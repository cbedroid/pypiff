import os
import re
import sys 
from time import time
from subprocess import PIPE,Popen
from ..filehandler import Path
from ..config import Threader
from .baseplayer import BasePlayer

try:
    # try to import eyed3 for easy metadata
    import eyed3
except:
    class eyed3():
        pass

class AndroidError(Exception):
    pass


class Android(BasePlayer):
    # Because of android's permission not allowing non-root users to 
    # to access write permissions on low-level filesystem,
    # we will move the tempfile (see backend.filehandler)
    # to the device storage system ('/sdcard' or '/storage/')
    DROID_TMP = '/sdcard/.pydatpiff_tmp.mp3'
    __Id3 = eyed3

    def __init__(self,*args,**kwargs):
        """ Initialize BasePlayer from Android class"""
        super(Android,self).__init__(*args,**kwargs)
    
    def __len__(self):
        return len(self.__content)

    def __resetState(self,**kwargs):
        self._state = dict(playing=False,pause=False,
            load=False,stop=False)
        self._state.update(**kwargs)

    def _is_playing(self,boolean=False):
        """ Return whether a song is being played or paused.
            
            variable state - belongs to BasePlayer
            sets the playing state = boolean
            sets the pause state = not boolean
        """
        self.state.update(dict(playing=bool(boolean),pause=not bool(boolean)))



    @property
    def elapse(self):
        """ 
        Elapse is the last time since a track has been loaded (self.__load).
        Elaspe capture when player is playing track
        It records the time from the latest state in seconds
        """
        return self._elapse

    @elapse.setter
    def elapse(self,val=0):
        #state_time was here
        self._elapse = (time() - self._load_time )


    @Threader
    def startClock(self):
        print('\nClock started')
        start = time()
        while True:
            if self._state['playing'] and not self._state['pause']:
                #state_time was here
                self._elapse = time() - self._load_time
            #else: #catch the current postion  paused,rewinf, and fast-forward 
            #    # its self.elapse because sef.elapse has the pause position
            #    self.current_position = 0
            if time() - start > 3:
                #print('TIME:',self.current_position)
                start = time()

            if hasattr(self,'__content'):
                if self.current_position > (len(self)/self.bytes_per_sec)\
                        and self._state['playing']:
                    print('\nTrack finish')
                    self.__resetState()

    @property
    def __am_start_Intent(self):
        """ Prepares android java 'am start' intent to play song""" 
        path = re.sub('\B\/','',self.DROID_TMP) #remove start '/'
        intent = 'am start --user 0 -a android.intent.action.VIEW -d '
        return intent + 'file:///{} -t audio/*'.format(path)
    
        
    @property
    def duration(self):
        return self.__Id3.info.time_secs 
   
        
    @property
    def songpath(self):
        """ Returns media song path from media class"""
        if hasattr(self,'_media_song_path'):
            return self._media_song_path
        else:
             raise AndroidError('Media song path not found')
    
    @songpath.setter
    def songpath(self,path):
        if Path.isFile(path):
            # keep a copy of the original path to extract the meta data
            self.__meta_data_path = path
            self._media_song_path = path
        else: 
            error = 'internal Error: android media path %s not found'%path
            raise AndroidError(error)


    
    def _format_time(self,pos=None):
        """Format current song time to clock format """
        pos = self.duration  if not pos else pos
        mins = int(pos/60)
        secs = int(pos%60)
        return  mins,secs


    def preloadTrack(self):
        """Open file path  and return its content"""

        #if not self._state.get('load'):
        #    self._load_time = time()
        self.__Id3 = eyed3.load(self.__meta_data_path)
        self.__tag = self.__Id3.tag
        
        with open(self.songpath,'rb') as f:
            self.__content = f.read()

        self._state['load'] = True
        print('loadingMedia:',self._state)


    @property
    def bytes_per_sec(self):
        """song bytes per seconds"""
        return len(self)/self.duration

    @property
    def pause_position(self):
        """ Return the position when the pause is pause"""
        if not hasattr(self,'_pause_pos'):
            self._pause_pos = self._current_position
            return 0
        return self._pause_pos

    @pause_position.setter
    def pause_position(self,pos):
        self._pause_pos = pos


    @property
    def current_position(self):
        pos = time() - self._start_time
        return pos if pos > 0 else 0 

    @current_position.setter
    def current_position(self,pos):
        self._start_time -= pos
    ''' 
    if self._state['pause']:
            position = self.pause_position + position
            print('RELEASING PAUSE AT POSITION:', position)
    '''
    def __load(self,position):
        """
        Write media content to file
        
        :param: position  - postion to start song (second(s)) 
        """
        #spot in seconds
        with open(self.DROID_TMP,'wb') as mp3:

            print('\nPOS',position)
            if self.state['pause']:
                print("OLD POSITION P<>:",int(self.pause_position))
                difference = self.current_position - (
                                self.pause_position + position)
                print('THE DIFFERENCE: ',difference)
                self.current_position = -difference
            else:
                print("OLD POSITION:",int(self.current_position))
                self.current_position = position

            spot = int(self.current_position+position) 
            topos = spot*self.bytes_per_sec if spot > 0 else 1*self.bytes_per_sec
            topos = int(topos)

            oldpos = self.current_position #testing
            print('NEW POSITION:',self.current_position)
            #testing
            if self.state['pause']: # testing
                print('UNPAUSE POSITION:',self.pause_position)
            newpos = self.current_position # testing
            print('DIFFERENCE IN POSITION:',oldpos-newpos)
            self._load_time = time()
            print('loaded to:',topos)
            self.topos = topos # can delect this : testing only
            mp3.write(self.__content[topos:])

            """
            if not self._state['playing'] and not self._state['load']:
                print('fresh start playing from beginning')
                #state_time was here
                self._load_time = time() + self.elapse
            else:
                #state_time was here
                self._load_time = (time() - #state_time was here
                self._load_time) + (self.elapse + spot) 
            """
     


    def setTrack(self,name,path):
        """ 
        Prepares the media tracks and set its attributes and current state

        :params: name - name of the of the media track
        :param: path - path location of the media track
        """
        #TMP = '/sdcard/2chainz.mp3'
        #mp3file = '/sdcard/testmp3.mp3'
        self.current_time = 0
        self.__resetState()

        if Path.isFile(path):
            self._name = name
            self.songpath = path
            print('Setting Track',name,path)
        else:
            raise AndroidError('Internal Error: Media song invalid path')

        self._load_time = time()
        self.elapse = 0

    @property
    def play(self):
        #state_time was here
        #self._load_time = time()
        self.startClock()
        self._start_time = time()
        self._play()

    def _play(self,position=0):
        """
        Play media songs
        :param:pos   - play a song at the given postion (seconds)
        """ 
        print('\n')
        self.preloadTrack()

        if not self._state['load']:
            #state_time was here
            #self._load_time = time()
            self.__startClock()
            self._state['load'] = True
        print('MID STATE:',self.state)
        self.__load(position)
        self._player = Popen(self.__am_start_Intent ,shell=True,
                    stdin=PIPE,stdout=PIPE,stderr=PIPE)
        self._state['pause'] = False
        self._is_playing(True)
        print('NEW STATE:',self.state)

    def volume(self,vol=None):
        """
        Android volume controls
        @params:: vol - set the media volume range 0 - 100 
        """
        os.system('termux-volume music %s'% vol)

   
    @property
    def pause(self):
        """Pause song"""
        print('PAUSE STATE:',self.state['pause'])
        # capture the position the media player was pause
        if not self._state['pause']:
            self.stop
            print("Paused")
            self._is_playing(False)
            #Capture time when state is pause 
            self.pause_position = self.current_position
            print('Paused_Position:',self.pause_position)

        else: # unpause
            print("Unpause")
            self._play()
            #self._is_playing(True)
            # Not here play() will handle self._is_playing(True) 

        print('NEW PAUSE STATE: %s\n '%self.state)

    def _seeker(self,pos=5, rew=True):
        """Control fast forward and rewind function"""
        spot = pos
        if self._state['pause']:
            self._state['pause'] = False

        #self.current_position = spot
        self._play(position=pos)


    def rewind(self,pos=5):
        self._seeker(-(pos),True)
        

    def ffwd(self,pos=5):
        self._seeker(pos,False)

    @property
    def stop(self):
        service = "am stopservice "
        cmd = service + "org.videolan.vlc/org.videolan.vlc.PlaybackService"
        results = Popen(cmd,shell=True,stdout=PIPE,stderr=PIPE)
        
