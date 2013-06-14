import time
import settings
import sqlite3
import player
import pdb



class BookReader(object):

    currently_playing = None
    sleep_time = .5


    def __init__(self):

        self.mpd_client = player.MPDClient()
        player.mpdConnect(self.mpd_client, player.CON_ID)

        # clear any playlist items
        self.mpd_client.clear()

        # connect to database
        self.db_connt = sqlite3.connect('state.db')

        


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
        self.currently_playing = None
        self.mpd_client.stop()
        self.mpd_client.clear()

    def play(self, book_id):
        filename = '%s.mp3' % (book_id)
        print "trying to load %s" % filename


        self.mpd_client.add(filename)
        self.mpd_client.play()
        self.currently_playing = book_id


        time.sleep(2)
        pdb.set_trace()

    def set_position(self, seconds):
        # index can always be 0 because we always only have a playlist of length 1
        self.mpd_client.seek(0, seconds)



    def start_loop(self):

        """
        The main event loop
        """


        while True:

            time.sleep(self.sleep_time)

            book_id_from_rfid = self.get_book_id()
            player_state = self.mpd_client.status()['state']

            if  book_id_from_rfid is not None:
            
            
                if book_id_from_rfid != self.currently_playing:

                    # stop the currently playing song
                    if player_state != 'stop':
                        self.stop()
                    
                    self.play(book_id_from_rfid)


            elif player_state != 'stop':
                self.stop()      
                


            if self.currently_playing is not None:
                # things to do each time music is playing
                print self.mpd_client.status()['elapsed']






if __name__ == '__main__':

    reader = BookReader()
    reader.start_loop()

