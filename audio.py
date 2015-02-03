import mutagen, time
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.easyid3 import EasyID3

''' TEST
from audio import Audio
a = Audio('id3test/song.mp3')
a.albumart('id3test/no_cover.jpg')
'''
class Audio:
    
    "store audio metadata"
    def __init__(self, filepath=None):
        self.filepath = filepath
    
    def flush(self):
        
        try:
            id3 = ID3(self.filepath)
            id3.delete()
        except mutagen.id3.error:
            pass
        
        mp3file = MP3(self.filepath, ID3=EasyID3)

        try:
            mp3file.add_tags(ID3=EasyID3)
        except mutagen.id3.error:
            print("has tags")
        
        mp3file.save()
    
    def title(self, title=None):
        mp3 = MP3(self.filepath, ID3=EasyID3)
        if title is not None:
            mp3["title"] = title
            mp3.save()
        return mp3["title"]
    
    def artist(self, artist=None):
        mp3 = MP3(self.filepath, ID3=EasyID3)
        if artist is not None:
            mp3["artist"] = artist
            mp3.save()
        return mp3["artist"]
        
    def tracknumber(self, tracknumber=None):
        mp3 = MP3(self.filepath, ID3=EasyID3)
        if tracknumber is not None:
            mp3["tracknumber"] = tracknumber
            mp3.save()
        return mp3["tracknumber"]
    
    def album(self, album=None):
        mp3 = MP3(self.filepath, ID3=EasyID3)
        if album is not None:
            mp3["album"] = album
            mp3.save()
        return mp3["album"]
    
    def runtime(self):
        mp3 = MP3(self.filepath, ID3=EasyID3)
        return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(mp3.info.length))
    
    def albumart(self, albumart_path):
        mp3 = MP3(self.filepath, ID3=ID3)
        mime = 'image/png' if '.png' in albumart_path.lower() else 'image/jpg'
        mp3.tags.add(
            APIC(
                encoding=3,
                mime=mime,
                type=3, 
                desc=u'Cover',
                data=open(albumart_path).read()
            )
        )
        mp3.save()
    