import time
import sqlite3
import pdb
import signal
import sys
import rfid
import RPi.GPIO as GPIO
from player import Player

class BookReader(object):

    """The main class that controls the player, the GPIO pins and the RFID reader
    
    Attributes:

    db_file : the SQLite file used to store the progress
    serial : settings for the serial port that the RFID reader connects to
    mpd_conn : the connection details for the MPD client
    gpio_pins : the ids of the GPIO input pins and their callbacks
    status_light_pin : the pin used by the status light
    playing : keep track of playing status. rather use this instead of calling
              status() all the time"""


    db_file = 'state.db'
    serial = { "port_name" : "/dev/ttyAMA0", "baudrate" : 9600, "string_length" : 14 }
    mpd_conn = { "host" : "localhost", "port" : 6600 }
    gpio_pins = [
        { 'pin_id': 9, 'callback' : 'rewind' },
        { 'pin_id': 11, 'callback' : 'toggle_pause' },
        { 'pin_id': 22, 'callback' : 'volume_down' },
        { 'pin_id': 10, 'callback' : 'volume_up' }
    ]
    status_light_pin = 23


    def __init__(self):
        """Initialize all the things"""

        self.rfid_reader = rfid.Reader(**self.serial)
        
        signal.signal(signal.SIGINT, self.signal_handler)
        
        self.setup_db()
        self.player = Player(self.mpd_conn)
        self.setup_gpio()


    def setup_db(self):
        """Setup a connection to the SQLite db"""

        self.db_conn = sqlite3.connect(self.db_file)
        self.db_cursor = self.db_conn.cursor()

    def setup_gpio(self):
        """Setup all GPIO pins"""

        GPIO.setmode(GPIO.BCM)
        
        # status light
        GPIO.setup(self.status_light_pin, GPIO.OUT)
        GPIO.output(self.status_light_pin, True)

        # input pins for buttons
        for pin in self.gpio_pins:
            GPIO.setup(pin['pin_id'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(pin['pin_id'], GPIO.FALLING, callback=getattr(self.player, pin['callback']), bouncetime=200)


    def signal_handler(self, signal, frame):
        """When quiting, stop playback, close the player and release GPIO pins"""

        self.player.close()
        GPIO.cleanup()
        sys.exit(0)

    def loop(self):
        """The main event loop. This is where we look for new RFID cards on the RFID reader. If one is
        present and different from the book that's currently playing, in which case:
        
        1. Stop playback of the current book if one is playing
        2. Start playing
        """

        while True:

            if self.player.is_playing():
                self.on_playing()

            rfid_card = self.rfid_reader.read()

            if not rfid_card:
                continue
    
            book_id = rfid_card.get_id()

            if book_id and book_id != self.player.book.book_id: # a change in book id

                progress = self.db_cursor.execute(
                        'SELECT * FROM progress WHERE book_id = "%s"' % book_id).fetchone()

                self.player.play(book_id, progress)

    
    def on_playing(self):

        """Executed for each loop execution. Here we update self.player.book with the latest known position
        and save the prigress to db"""

        status = self.player.get_status()

        self.player.book.elapsed = float(status['elapsed'])
        self.player.book.part = int(status['song']) + 1

        print "%s second of part %s" % (self.player.book.elapsed,  self.player.book.part)

        self.db_cursor.execute(
                'INSERT OR REPLACE INTO progress (book_id, part, elapsed) VALUES (%s, %d, %f)' %\
                (self.player.book.book_id, self.player.book.part, self.player.book.elapsed))

        self.db_conn.commit()


if __name__ == '__main__':
    reader = BookReader()
    reader.loop()
