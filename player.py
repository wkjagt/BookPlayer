from mpd import MPDClient
from threading import Lock
from book import Book

import re

class LockableMPDClient(MPDClient):
    def __init__(self, use_unicode=False):
        super(LockableMPDClient, self).__init__()
        self.use_unicode = use_unicode
        self._lock = Lock()
    def acquire(self):
        self._lock.acquire()
    def release(self):
        self._lock.release()
    def __enter__(self):
        self.acquire()
    def __exit__(self, type, value, traceback):
        self.release() 


class Player(object):

    """The class responsible for playing the audio books"""

    def __init__(self, conn_details):
        """Setup a connection to MPD to be able to play audio.
        
        Also update the MPD database with any new MP3 files that may have been added
        and clear any existing playlists.
        """
        self.book = Book()

        self.mpd_client = LockableMPDClient()
        with self.mpd_client:
            self.mpd_client.connect(**conn_details)

            self.mpd_client.update()
            self.mpd_client.clear()
            self.mpd_client.setvol(100)


    def toggle_pause(self, channel):
        """Toggle playback status between play and pause"""
        
        with self.mpd_client:
            state = self.mpd_client.status()['state']
            if state == 'play':
                self.mpd_client.pause()
            elif state == 'pause':
                self.mpd_client.play()

    def rewind(self, channel):
        if self.is_playing():
            with self.mpd_client:
                seek = max(int(self.book.elapsed) - 20, 0)
                self.mpd_client.seek(int(self.book.part) - 1, seek)


    def volume_up(self, channel):

        volume = int(self.get_status()['volume'])
        self.set_volume(min(volume + 10, 100))


    def volume_down(self, channel):

        volume = int(self.get_status()['volume'])
        self.set_volume(max(volume - 10, 0))


    def set_volume(self, volume):
        """Set the volume on the MPD client"""

        with self.mpd_client:
            self.mpd_client.setvol(volume)
            print "volume set to %d" % volume


    def stop(self):
        """On stopping, reset the current playback and stop and clear the playlist
        
        In contract to pausing, stopping is actually meant to completely stop playing
        the current book and start listening to another"""

        self.playing = False
        self.book.reset()
        
        with self.mpd_client:
            self.mpd_client.stop()
            self.mpd_client.clear()


    def play(self, book_id, progress=None):
        """Play the book as defined in self.book
        
        1. Get the parts from the current book and add them to the playlsit
        2. Start playing the playlist
        3. Immediately set the position the last know position to resume playback where
           we last left off"""

        def sorting(file1, file2):

            """sorting algorithm for files in playlist"""
            pattern = '(\d+)(-(\d+))?\.mp3'
            
            try:
                file1_index = re.search(pattern, file1).groups()[2] or 0
                file2_index = re.search(pattern, file2).groups()[2] or 0

                return -1 if int(file1_index) < int(file2_index) else 1
            except:
                return 0


        with self.mpd_client:

            parts = self.mpd_client.search('filename', book_id)
    
            if not parts:
                print "Unused book id: %d" % book_id
                self.book.book_id = None
                return

            self.mpd_client.clear()
            
            for part in parts.sorted(cmp=sorting):
                self.mpd_client.add(part['file'])

            self.book.book_id = book_id

            if progress:
                # resume at last known position
                self.book.set_progress(progress)
                self.mpd_client.seek(int(self.book.part) - 1, int(self.book.elapsed))
            else:
                self.mpd_client.play()


    def is_playing(self):
        return self.get_status()['state'] == 'play'


    def get_status(self):
        with self.mpd_client:
            return self.mpd_client.status()


    def close(self):
        self.stop()
        self.mpd_client.close()
        self.mpd_client.disconnect()
