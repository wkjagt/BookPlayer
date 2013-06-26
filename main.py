import time
import sqlite3
import pdb
import mpd
import signal
import sys
import rfid
import RPi.GPIO as GPIO
from mpd import MPDClient
import RPi.GPIO as GPIO

class BookReader(object):

    """The main class that controls MPD, the GPIO pins and the RFID reader
    
    Attributes:
        db_file : the SQLite file used to store the progress
        serial : settings for the serial port that the RFID reader connects to
        mpd_conn : the connection details for the MPD client
        gpio_pins : the ids of the GPIO input pins and their callbacks
        status_light_pin : the pin used by the status light
        playing : keep track of playing status. rather use this instead of calling
                  status() all the time
        paused : same as playing, but for paused state"""

    playing = False
       
    paused = False

    db_file = 'state.db'
    
    serial = { "port_name" : "/dev/ttyAMA0", "baudrate" : 9600, "string_length" : 14 }
    
    mpd_conn = { "host" : "localhost", "port" : 6600 }

    gpio_pins = [
        { 'pin_id': 9, 'callback' : 'rewind' },
        { 'pin_id': 11, 'callback' : 'pause' },
        { 'pin_id': 22, 'callback' : 'volume_down' },
        { 'pin_id': 10, 'callback' : 'volume_up' }
    ]

    status_light_pin = 23

    def __init__(self):
        """Initialize all the things"""

        self.rfid_reader = rfid.Reader(**self.serial)
        
        # the object holding information about the progress of the current book
        self.current = CurrentBook()

        signal.signal(signal.SIGINT, self.signal_handler)
        
        self.setup_db()
        self.setup_mpd_client()
        self.setup_gpio()


    def setup_db(self):
        """Setup a connection to the SQLite db"""
        self.db_conn = sqlite3.connect(self.db_file)
        self.db_cursor = self.db_conn.cursor()


    def setup_mpd_client(self):
        """Setup a connection to MPD to be able to play audio.
        
        Also update the MPD database with any new MP3 files that may have been added
        and clear any existing playlists.
        """
        self.mpd_client = MPDClient()
        self.mpd_client.connect(**self.mpd_conn)

        self.mpd_client.update()
        self.mpd_client.clear()


    def setup_gpio(self):
        """Setup all GPIO pins"""

        GPIO.setmode(GPIO.BCM)
        
        # status light
        GPIO.setup(self.status_light_pin, GPIO.OUT)
        GPIO.output(self.status_light_pin, True)

        # input pins for buttons
        for pin in self.gpio_pins:
            GPIO.setup(pin['pin_id'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(pin['pin_id'], GPIO.FALLING, callback=getattr(self, pin['callback']), bouncetime=500)
 


    def pause(self, channel):
        """Toggle playback status between play and pause"""

        if not self.paused:
            self.paused = True
            self.mpd_client.pause()
        else:
            self.paused = False
            self.mpd_client.play()


    def rewind(self, channel):
        """Rewind current track by 20 seconds"""
        if self.playing:

            seek = max(int(self.current.position) - 20, 0)
            self.mpd_client.seek(int(self.current.volume) - 1, seek)


    def volume_up(self, channel):
        """Volume up by 10 percent"""
        try:
            volume = int(self.mpd_client.status()['volume'])
            self.set_volume(min(volume + 10, 100))
        except KeyError:
            pass

    
    def volume_down(self, channel):
        """Volume down by 10 percent"""

        try:
            volume = int(self.mpd_client.status()['volume'])
            self.set_volume(max(volume - 10, 0))
        except KeyError:
            pass


    def set_volume(self, volume):
        self.mpd_client.setvol(volume)
        print "volume set to %d" % volume
    
    def signal_handler(self, signal, frame):
        """When quiting, stop playback, and release GPIO pins"""

        self.stop()
        GPIO.cleanup()
        sys.exit(0)


    def stop(self):
        """On stopping, reset the current playback and stop and clear the playlist
        
        In contract to pausing, stopping is actually meant to completely stop playing
        the current book and start listening to another"""

        self.playing = False
        self.current.reset()
        self.mpd_client.stop()
        self.mpd_client.clear()


    def play(self):
        """Play the book as defined in self.current
        
        1. Get the volumes (parts) from the current book and add them to the playlsit
        2. Start playing the playlist
        3. Immediately set the position the last know position to resume playback where
           we last left off"""

        self.mpd_client.clear()

        volumes = self.mpd_client.search('filename', self.current.book_id)
    
        if not volumes:
            print "unknown book id: %d" % self.current.book_id
            return

        for volume in volumes:
            self.mpd_client.add(volume['file'])

        self.mpd_client.play()
        self.playing = True
        # resume at last known position
        self.mpd_client.seek(int(self.current.volume) - 1, int(self.current.position))

    def start_loop(self):
        """The main event loop. This is where we look for new RFID cards on the RFID reader. If one is
        present and different from the book that's currently playing, in which case:
        
        1. Stop playback of the current book if one is playing
        2. Get the progress for the new book from the DB and build self.current
        3. Start playing
        """

        while True:
            
            # any events while playing should be done in self.on_playing()
            if self.mpd_client.status()['state'] == 'play':
                self.on_playing()
            else:
                self.playing = False

            rfid_card = self.rfid_reader.read()

            if not rfid_card:
                continue
    
            book_id_from_rfid = rfid_card.get_id()

            if book_id_from_rfid and book_id_from_rfid != self.current.book_id: # a change in book id

                # stop the currently playing song
                if self.playing:
                    self.stop()
                
                progress = self.db_cursor.execute(
                        'SELECT * FROM progress WHERE book_id = "%s"' % book_id_from_rfid).fetchone()
                self.current.set_progress(book_id_from_rfid, progress)

                self.play()

    
    def on_playing(self):

        """Executed for each loop execution. Here we update self.current with the latest know position
        and save the prigress to db"""

        try:
            status = self.mpd_client.status()
            self.current.position = float(status['elapsed'])
            self.current.volume = int(status['song']) + 1
        except KeyError:
            print "status error"
            print status
            return
       

        print "%s second of volume %s" % (self.current.position,  self.current.volume)

        self.db_cursor.execute(
                'INSERT OR REPLACE INTO progress (book_id, volume, position) VALUES (%s, %d, %f)' %\
                (self.current.book_id, self.current.volume, self.current.position))

        self.db_conn.commit()




class CurrentBook(object):
    """The book that is currenty playing"""


    def __init__(self):
        """Initialize"""

        self.book_id = None
        self.volume = 1
        self.position = 0


    def reset(self):
        """Reset progress"""

        self.__init__()

    def set_progress(self, book_id, progress):
        """Set progess from db result"""
        self.reset()
        self.book_id = book_id

        if progress:
            self.volume = progress[1]
            self.position = progress[2]

    def is_playing(self):
        """returns if we have a current book"""
        return self.book_id is not None

if __name__ == '__main__':
    #try:
        reader = BookReader()
        reader.start_loop()
    #except Exception as e:
    #    pdb.set_trace()
    #    GPIO.cleanup()

