import time
import settings
import sqlite3
import player
import pdb



class BookReader(object):

    sleep_time = .5


    def __init__(self):

        self.mpd_client = player.MPDClient()
        player.mpdConnect(self.mpd_client, player.CON_ID)

        # clear any playlist items
        self.mpd_client.clear()

        # connect to database
        self.db_conn = sqlite3.connect('state.db')
        self.db_cursor = self.db_conn.cursor()

        self.current = CurrentBook()

        
    def get_book_id(self):

        """
        Get the id of the book from the RFID
        """
        # temporary to simulate RFID
        try:
            with file('mp3id') as f:
                book_id = f.read()
        except:
            return None

        return book_id.strip()


    def stop(self):
        self.current.reset()
        self.mpd_client.stop()
        self.mpd_client.clear()


    def play(self):
        filename = '%s.mp3' % (self.current.book_id)
        print "trying to load %s" % filename

        self.mpd_client.add(filename)
        self.mpd_client.play()

        # when resuming go 20 seconds back
        seek = max(int(self.current.position) - 20, 0)

        # index can always be 0 because we always only have a playlist of length 1
        self.mpd_client.seek(0, seek)


    def start_loop(self):
        """
        The main event loop
        """
        while True:

            time.sleep(self.sleep_time)

            book_id_from_rfid = self.get_book_id()
            player_state = self.mpd_client.status()['state']

            if  book_id_from_rfid is not None:
            
            
                if book_id_from_rfid != self.current.book_id:

                    # stop the currently playing song
                    if player_state == 'play':
                        self.stop()
                    
                    progress = self.db_cursor.execute(
                            'SELECT * FROM progress WHERE book_id = "%s"' % book_id_from_rfid).fetchone()

                    self.current.set_progress(book_id_from_rfid, progress)
                    self.play()

            elif player_state == 'play':
                self.stop()      

            if player_state == 'play':

                # things to do each time music is playing
                elapsed = self.mpd_client.status()['elapsed']
                self.current.position = float(elapsed)

                print elapsed

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

