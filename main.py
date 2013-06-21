import time
import settings
import sqlite3
import player
import pdb
import mpd
import signal
import sys
import rfid

class BookReader(object):

    def __init__(self):

        self.rfid_reader = rfid.Reader("/dev/ttyAMA0", 9600, 14)

        self.mpd_client = player.MPDClient()
        player.mpdConnect(self.mpd_client, player.CON_ID)

        # update mpd database with mp3 files
        self.mpd_client.update()
        # clear any playlist items
        self.mpd_client.clear()

        # connect to database
        self.db_conn = sqlite3.connect('state.db')
        self.db_cursor = self.db_conn.cursor()

        self.current = CurrentBook()

        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, signal, frame):

        print 'You pressed Ctrl+C!'
        self.stop()
        sys.exit(0)


    def stop(self):
        self.current.reset()
        self.mpd_client.stop()
        self.mpd_client.clear()


    def play(self):
        self.mpd_client.clear()

        volumes = self.mpd_client.search('filename', self.current.book_id)
    
        if not volumes:
            print "unknown book id: %d" % self.current.book_id
            return


        for volume in volumes:
            self.mpd_client.add(volume['file'])

        self.mpd_client.play()

        # when resuming go 20 seconds back
        seek = max(int(self.current.position) - 20, 0)
        self.mpd_client.seek(int(self.current.volume) - 1, seek)

    def start_loop(self):
        """
        The main event loop
        """
        while True:
            
            if self.mpd_client.status()['state'] == 'play':
                self.on_playing()

            rfid_card = self.rfid_reader.read()

            if not rfid_card:
                continue
    
            book_id_from_rfid = rfid_card.get_id()


            if book_id_from_rfid and book_id_from_rfid != self.current.book_id: # a change in book id

                # stop the currently playing song
                if self.mpd_client.status()['state'] == 'play':
                    self.stop()
                
                # get progress from db and start from saved position if it exists
                progress = self.db_cursor.execute(
                        'SELECT * FROM progress WHERE book_id = "%s"' % book_id_from_rfid).fetchone()
                self.current.set_progress(book_id_from_rfid, progress)

                self.play()

    def on_playing(self):
        # things to do each time music is playing
        status = self.mpd_client.status()
        self.current.position = float(status['elapsed'])
        self.current.volume = int(status['song']) + 1
       

        print "%s second of volume %s" % (self.current.position,  self.current.volume)

        self.db_cursor.execute(
                'INSERT OR REPLACE INTO progress (book_id, volume, position) VALUES (%s, %d, %f)' %\
                (self.current.book_id, self.current.volume, self.current.position))

        self.db_conn.commit()




class CurrentBook(object):

    def __init__(self):
        self.book_id = None
        self.volume = 1
        self.position = 0

    def reset(self):
        self.__init__()

    def set_progress(self, book_id, progress):
        self.reset()
        self.book_id = book_id

        if progress:
            self.volume = progress[1]
            self.position = progress[2]

    def is_playing(self):
        return self.book_id is not None

if __name__ == '__main__':

    reader = BookReader()
    reader.start_loop()

