# if 0 /*
# -----------------------------------------------------------------------
# cdbackup.py - CD Backup plugin for ripping/backing up CDs to 
# your hard drive
# -----------------------------------------------------------------------
# $Id$
# 
# Notes: This is the cdbackup module which can be accessed from the audio menu 
# by hitting 'e' or enter (not return) whilst a CD is selected.
# 
# It allows you to backup CDs as .wav files or as .mp3s.
# 
# To Activate Plugin, add the following to local_conf.py: 
# plugin.activate('audio.cdbackup') 
# 
# Todo:      
#
# Add a status bar showing progress Parse the output of cdparanoia and
# lame to determine status of rip, mp3 conversion For encoding
# parameters, make choices dynamic/selectable from menu instead of
# only local_conf.py
# maybe just use local_conf.py parameters as defaults.  Be able to
# stop ripping once it's started.  Be able to select individual songs
# for ripping.  There is slight delay before menu opens up after being
# selected from main menu, add a hourglass or some other notification
# that its loading.  Albums with more than one Artist aren't handled
# very well.
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.31  2004/01/18 16:51:48  dischi
# (re)move unneeded variables
#
# Revision 1.30  2004/01/17 20:29:12  dischi
# renamed media.info to media.item
#
# Revision 1.29  2004/01/02 14:20:10  dischi
# send OSD_MESSAGE when ripping is complete
#
# Revision 1.28  2003/11/28 19:26:36  dischi
# renamed some config variables
#
# Revision 1.27  2003/11/09 12:10:14  dischi
# do not rip last track for mixed cds
#
# Revision 1.26  2003/11/02 13:48:19  outlyer
# My first post 1.4rc2 commit... allows you to make sure your ripped mp3's had
# properly case'd tags.
#
# Revision 1.1  2003/10/29 19:00:50  outlyer
# Presumably this will have to wait until after the freeze. It's a minor
# change but it includes a preference to allow the user to make sure all
# CD track information is in normalized title case so you can deal with the
# annoying ways people submit CDDB data.
#
# It's self contained, so it can go in before 1.4, but not before 1.4rc2.
#
# Revision 1.24  2003/10/22 18:37:41  mikeruelle
# if we have the coverart might as well copy it over
#
# Revision 1.23  2003/10/21 21:17:41  gsbarbieri
# Some more i18n improvements.
#
# Revision 1.22  2003/10/20 18:26:01  outlyer
# No CDDB data is a warning at best; sometimes a CD is just not listed there.
# Convert the rest of the 'print' into _debug_ with errors getting 0
#
# Revision 1.21  2003/10/08 02:57:41  outlyer
# Get rid of the global variables; keep the thread inside the class.
#
# I still don't know why ripping CDs breaks audio playback, but I'm hoping
# these changes will help.
#
# Revision 1.20  2003/10/08 02:06:18  outlyer
# Just some cleanup of commented out or disabled code.
#
# Revision 1.19  2003/09/20 09:42:32  dischi
# cleanup
#
# Revision 1.18  2003/09/14 20:47:48  outlyer
# * TRUE/FALSE wasn't working in Python 2.3...
# * Wrapped the tagging function in a try: except because it failed on a data
#    track and Freevo needed to be restarted to rip another CD.
#
# Revision 1.17  2003/09/13 10:08:22  dischi
# i18n support
#
# Revision 1.16  2003/09/10 18:15:11  dischi
# o use plugin config() function to set defaults to freevo_config.py
# o show current ripping status in itemmenu while ripping
# o some cleanup and restructuring
#
# Revision 1.15  2003/09/09 18:54:59  dischi
# Add some doc
#
# Revision 1.14  2003/08/26 18:47:29  outlyer
# Initial FLAC support (for encoding) Xine is required for playback.
#
# Revision 1.13  2003/08/23 12:51:42  dischi
# removed some old CVS log messages
#
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2002 Krister Lagerstrom, et al.
# Please see the file freevo/Docs/CREDITS for a complete list of authors.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
# 
# ----------------------------------------------------------------------- */
# endif

import os
import time
import string
import sys
import threading
import re
import shutil

import config
import menu
import util
import plugin
import rc

from gui.AlertBox import AlertBox
from event import *

# Included to be able to access the info for Audio CDs
import mmpython

class PluginInterface(plugin.ItemPlugin):
    """
    Backup audio CDs in .mp3, .ogg, or .wav format.
    
    The following variables are needed by this plugin. Please set them in
    your local_conf.py:
    
    Directory that you want to backup your audio CD to.
    AUDIO_BACKUP_DIR = '/music/MP3'
    
    You can use any combination of the 4 variables below to create subdirectories,
    and filename of songs.
    The four variables are: genre, artist,album, and song.
    Whatever follows the last slash indicates how to create the filename.
    Everything before the last slash indicates the directory structure you would
    like to use -which will be appended to AUDIO_BACKUP_DIR.
    CD_RIP_PN_PREF= '%(genre)s/%(artist)s/%(album)s/%(song)s'
    
    This would give you something like:
    /music/MP3/metal/Metallica/And Justice For All/Blackened.mp3
    (or Blackened.wav, Blackened.ogg)
    
    Here is another example which includes the artist and album in the filename:
    CD_RIP_PN_PREF = '%(artist)s/%(artist)s - %(album)s - %(song)s'
    /music/MP3/Metallica/Metallica - And Justice For All - Blackened.mp3
    
    cdparanoia is used to rip the CD to your hard drive. The actual command that
    will be executed is stored in CDPAR_CMD.
    CDPAR_CMD = 'cdparanoia'
    
    Lame .mp3 encoding parameters:
    Lame is used for .mp3 encoding. The actual command that will be executed is
    stored in LAME_CMD
    LAME_CMD = 'lame'
    
    For ripping to .mp3 you can provide your own Lame encoder parameters for
    bitrate, algorithm, and various other lame options. Add your custom parameters
    in CD_RIP_LAME_OPTS.
    CD_RIP_LAME_OPTS = '--vbr-new'
    
    Ogg Encoding:
    Likewise for Ogg format, the command is as below, and you can add your own
    custom ogg encoding options.
    OGGENC_CMD ='oggenc'
    CD_RIP_OGG_OPTS = ' '
    
    To activate this plugin, add the following to local_conf.py:
    plugin.activate('audio.cdbackup')
    
    Finally, to actually backup an audio CD within Freeevo, when you are in the
    Music menu, highlight/choose a CD, then hit 'e' on keyboard or 'ENTER' on
    your remote control and you will be able to access the rip/backup menu.
    
    Here is a list of all the above mentioned parameters for simple cutting and
    pasting:
    
    #The following are for adding and configuring the CD Audio backup plugin: 
    AUDIO_BACKUP_DIR =  '/music/MP3' 
     
    CD_RIP_PN_PREF= '%(genre)s/%(artist)s/%(album)s/%(song)s' 
    CDPAR_CMD = 'cdparanoia' 
     
    LAME_CMD = 'lame' 
    CD_RIP_LAME_OPTS  = '--vbr-new' 
     
    #You can leave this out if you never use ogg and it won't show up in the
    #backup menu 
    OGGENC_CMD ='oggenc' 
    CD_RIP_OGG_OPTS = ' ' 
     
    #To activate the cdbackup plugin: 
    plugin.activate('audio.cdbackup') 
    """

    def __init__(self):
        plugin.ItemPlugin.__init__(self)
        self.artist = ''
        self.album = ''
        self.song_names = []
        self.device = ''
        self.rip_thread = None

        
    def config(self):
        """
        list of config variables this plugin needs
        """
        return (('AUDIO_BACKUP_DIR', config.AUDIO_ITEMS[ 0 ][ 1 ],
                 'directory where to put the encoded files'),
                ('LAME_CMD', config.CONF.lame , '' ),
                ('CDPAR_CMD', config.CONF.cdparanoia, ''),
                ('OGGENC_CMD', config.CONF.oggenc, ''),
                ('FLAC_CMD', config.CONF.flac, ''),
                ('CD_RIP_PN_PREF', '%(artist)s/%(album)s/%(song)s', ''),
                ('CD_RIP_LAME_OPTS', '--preset standard', ''),
                ('CD_RIP_OGG_OPTS', '-m 128', ''),
                ('FLAC_OPTS', '-8', '8==Best, but slowest compression'),
                ('RIP_TITLE_CASE','0',
                 'Autoconvert all track/album/artist names to title case'))

    def actions(self, item):
        self.item = item
        
        try:
            if (self.item.type == 'audiocd'):
                if self.rip_thread and self.rip_thread.current_track != -1:
                    return [ ( self.show_status, _( 'Show CD ripping status' ) ) ]
                else:
                    self.device = self.item.devicename
                    _debug_('devicename = %s' %self.device)
                    return [ ( self.create_backup_menu,
                               _('Rip the CD to the hard drive'),
                               _('Get CDs available for ripping')) ]
        except:
            _debug_( _( 'ERROR' ) + ': ' + _( 'Item is not an Audio CD' ) )
        return []


    def show_status(self, arg=None, menuw=None):
        t = self.rip_thread
        if t.current_track != -1:
            pop = AlertBox(text=_( 'Ripping in progress\nTrack %d of %d' ) % \
                           (t.current_track, t.max_track))
            pop.show()
            
            
    def create_backup_menu(self, arg=None, menuw=None):
        mm_menu = self.create_backup_items(self.device, menuw=None)
        menuw.pushmenu(mm_menu)
        menuw.refresh()


    def create_backup_items(self, arg, menuw):   
        items = []

        if config.LAME_CMD:
            items.append(menu.MenuItem(_('Backup CD to hard drive in mp3 format'),
                                       self.cd_backup, arg=(arg, 'mp3')))
        if config.OGGENC_CMD:
            items.append(menu.MenuItem(_('Backup CD to hard drive in Ogg format'),
                                       self.cd_backup, arg=(arg, 'ogg')))
        if config.FLAC_CMD:
            items.append(menu.MenuItem(_('Backup CD to hard drive in FLAC format'),
                                       self.cd_backup, arg=(arg, 'flac')))
        items.append(menu.MenuItem(_('Backup CD to hard drive in wav format'),
                                   self.cd_backup, arg=(arg, 'wav')))

        backupmenu = menu.Menu(_('CD Backup'), items, reload_func=self.create_backup_menu)
        return backupmenu
        

    def cd_backup(self, arg,  menuw=None):            
        device, type = arg
        self.rip_thread = main_backup_thread(device=device, rip_format=type)        
        self.rip_thread.start()
        AlertBox(text=_( 'Ripping started' ) ).show()
        menuw.delete_menu()
        menuw.back_one_menu()




class main_backup_thread(threading.Thread):
    device = None
    rip_format = ''
    def __init__(self, rip_format, device=None):
        threading.Thread.__init__(self)
        self.device           = device
        self.rip_format       = rip_format
        self.current_track    = 0
        self.max_track        = 0
        self.output_directory = ''

    def run(self, rip_format='mp3'):        
        if self.rip_format == 'mp3' :
            self.cd_backup_threaded(self.device, rip_format='mp3')
        elif self.rip_format == 'ogg' :
            self.cd_backup_threaded(self.device, rip_format='ogg')                      
        elif self.rip_format == 'wav' :
            self.cd_backup_threaded(self.device, rip_format='wav')        
        elif self.rip_format == 'flac' :
            self.cd_backup_threaded(self.device, rip_format='flac')
          
    
    def cd_backup_threaded(self, device, rip_format='mp3'):  
        rip_format = rip_format
        album = 'default_album'
        artist = 'default_artist'
        genre = 'default_genre'
        dir_audio_default = "dir_audio_default"        
        path_head = ''
        for media in config.REMOVABLE_MEDIA:
            if media.devicename == device:
                media.type = 'cdrip'
        
        # Get the artist, album and song_names	
        (discid, artist, album, genre, song_names) = self.get_formatted_cd_info(device)
               
        dir_audio = config.AUDIO_BACKUP_DIR
        
        user_rip_path_prefs = {  'artist': artist,
       	                         'album': album,
                                 'genre': genre }
        
        path_list = re.split("\\/", config.CD_RIP_PN_PREF)
        
        # Get everything up to the last "/"
        if len(path_list) != 0:
            for i in range (0, len(path_list)-1 ):
                path_head +=  '/' + path_list[i]
        path_tail_temp = '/' + path_list[len(path_list)-1]
        
        # If no directory structure preferences were given use default dir structure
        if len(path_list) == 0:
             pathname = dir_audio + "/" + artists + "/" + album + "/"
        # Else use the preferences given by user
        else:
            path_temp  =  dir_audio + path_head
            pathname = path_temp % user_rip_path_prefs
             
        try: 
            os.makedirs(pathname, 0777)
        except:
            _debug_(_( 'Directory %s already exists' ) % pathname)

        try:
	    mycoverart = '%s/mmpython/disc/%s.jpg' % (config.FREEVO_CACHEDIR, discid)
	    if os.path.isfile(mycoverart):
	        shutil.copy(mycoverart, os.path.join(pathname,'cover.jpg'))
	except:
            _debug_('can not copy over cover art')

        self.output_directory = pathname
        cdparanoia_command = []
        length=len(song_names)

        self.max_track = len(song_names)
        for i in range (0, len(song_names)):
            # Keep track of track# 
            track = i +1        
            self.current_track = track

            # CD_RIP_PATH = '%(artist)s/%(album)/%(song)s'

            # Add the song and track key back into user_rip_path_prefs to be used
            # in the song name as specified in CD_RIP_PN_PREF.  The song name was
            # previously not set so had to wait until here to add it in.

            track = '%0.2d' % int(track)
            user_rip_path_prefs = {  'artist': artist,
                                                 'album': album,
                                                 'genre': genre,
                                                 'track': track,
                                                 'song': song_names[i] }
                                                                                             
            path_tail = path_tail_temp % user_rip_path_prefs 
            
            # If rip_format is mp3 or ogg, then copy the file to
            # /tmp/track_being_ripped.wav
            if (string.upper(rip_format) == 'MP3') or \
                   (string.upper(rip_format) == 'OGG') or \
                   (string.upper(rip_format) == 'FLAC'):
                pathname_cdparanoia = '/tmp'
                path_tail_cdparanoia   = '/track_being_ripped'
           
            # Otherwise if it's going to be a .wav  just use the the users preferred
            # directory and filename. i.e. don't bother putting into /tmp directory,
            # just use directory and filename of final destination.    

            else: 
                pathname_cdparanoia  = pathname
                path_tail_cdparanoia = path_tail
                            
            # Build the cdparanoia command to be run
            cdparanoia_command = '%s -s %s "%s%s.wav" >/dev/null 2>&1' % \
                                 (config.CDPAR_CMD, str(i+1), 
                                  pathname_cdparanoia, path_tail_cdparanoia)

            _debug_('cdparanoia:  %s' % cdparanoia_command)
    
            # Have the OS execute the CD Paranoia rip command            
            os.system(cdparanoia_command)
             
            # Build the lame command to be run if mp3 format is selected
            if string.upper(rip_format) == 'MP3':
                lame_command = '%s --nohist -h %s "%s%s.wav" "%s%s.mp3" >/dev/null 2>&1' % \
                               (config.LAME_CMD, config.CD_RIP_LAME_OPTS,
                                pathname_cdparanoia, path_tail_cdparanoia,
                                pathname, path_tail)

                _debug_('lame: %s' %lame_command)
                os.system(lame_command)
                try: 
                    util.tagmp3(pathname+path_tail+'.mp3', title=song_names[i],
                            artist=artist, album=album, track=track, 
                            tracktotal=len(song_names))
                except IOError:
                    # This sometimes fails if the CD has a data track
                    # This is not a 100% fix, but temporary until I figure out why
                    # it's trying to tag a data track
                    pass
                    
                # Remove the .wav file.
                rm_command = '%s%s.wav' % (pathname_cdparanoia, path_tail_cdparanoia)
                if os.path.exists (rm_command): os.unlink(rm_command)


            # Build the oggenc command to be run if ogg format is selected                
            elif string.upper(rip_format) == 'OGG':
                oggenc_command = '%s %s -a "%s" -G "%s" -N "%s" -t "%s" -l "%s" ' \
                                 '"%s%s.wav" -o "%s%s.ogg"' % \
                                 (config.OGGENC_CMD, config.CD_RIP_OGG_OPTS, 
                                  artist, genre, track, song_names[i], album,
                                  pathname_cdparanoia, path_tail_cdparanoia, pathname,
                                  path_tail)

                _debug_('oggenc_command: %s' %oggenc_command)
                os.system(oggenc_command)
                    
                # Remove the .wav file.
                rm_command = '%s%s.wav' % (pathname_cdparanoia, path_tail_cdparanoia)
                if os.path.exists (rm_command): os.unlink(rm_command)                

            # Build the flacenc command
            elif string.upper(rip_format) == 'FLAC':
                flac_command = '%s %s "%s%s.wav" -o "%s%s.flac"' % \
                               ( config.FLAC_CMD, config.FLAC_OPTS, pathname_cdparanoia,
                                 path_tail_cdparanoia, pathname, path_tail)
                metaflac_command = \
                    'metaflac --set-vc-field=ARTIST="%s" --set-vc-field=ALBUM="%s" '\
                    '--set-vc-field=TITLE="%s" --set-vc-field=TRACKNUMBER="%s/%s" '\
                    '"%s%s.flac"' % (artist, album, song_names[i], track,
                                     len(song_names), pathname, path_tail)
                _debug_('flac_command: %s' % (flac_command))
                _debug_('metaflac    : %s' % (metaflac_command))
                os.system(flac_command)
                os.system(metaflac_command)
                rm_command = '%s%s.wav' % (pathname_cdparanoia, path_tail_cdparanoia)
                if os.path.exists (rm_command): os.unlink(rm_command)
        
        for media in config.REMOVABLE_MEDIA:
            if media.devicename == device:
                media.type = 'audio'

        # done
        rc.post_event(Event(OSD_MESSAGE, arg=_('Ripping complete')))
        self.current_track = -1


        
    def get_formatted_cd_info(self, device):
        cd_info = mmpython.parse(device)
        
        # Check if getting CDDB data failed -is there a better way to do this?
        # Give some defaults with a timestamp to uniqueify artist and album names.
        # So that subsequent CDs with no CDDB data found don't overwrite each other.
        if ((cd_info.title == None) and (cd_info.artist == None)):

            _debug_( _( 'WARNING' ) + ': ' + _( 'No CDDB data available to mmpython' ) ,2)
            current_time = time.strftime('%d-%b-%y-%I:%M%P')
            
            artist = _( 'Unknown Artist' ) + ' ' + current_time + ' - ' + _( 'RENAME' )
            album = _( 'Unknown CD Album' ) + ' ' + current_time +  ' - ' + _( 'RENAME' )
            genre = _( 'Other' )
           
           # Flash a popup window indicating copying is done
            popup_string=_( "CD info not found!\nMust manually rename files\nwhen finished ripping" )

            pop = AlertBox(text=popup_string)
            time.sleep(7)

        # If  valid data was returned from mmpython/CDDB
        else:
            album   = self.fix_case(self.replace_special_char(cd_info.title, '-'))
            artist     = self.fix_case(self.replace_special_char(cd_info.artist, '-'))
            genre    = self.replace_special_char(cd_info.tracks[0].genre, '-')

        song_names = []                        
        for track in cd_info.tracks:
            song_names.append(self.fix_case(self.replace_special_char(track.title, '-')))

        if hasattr(cd_info, 'mixed') and cd_info.mixed:
            # remove last tracks if it's a mixed cd
            song_names = song_names[:-1]

        return [cd_info.id, artist, album, genre, song_names]                
    

    # This function gets rid of the slash, '/', in a string, and replaces it
    # with join_string    
    def slash_split(self, string, join_string = '-'):
        split_string= re.split(" \\/ ", string)
        rejoined_string = ''
        # Were there any splits on '/'?
        if len(split_string) > 1:
            for  i in range (0, len(split_string)):
                # Are we at the last slash
                if (i == (len(split_string) - 1)):
                    rejoined_string += split_string[i]
                # if not at the last slash, keep adding to string the join_string 
                else :
                    rejoined_string += split_string[i] + join_string
        # If there are no slashes , then the list is only 1 element long and there
        # is nothing to do.
        else:
            rejoined_string = string
        
        return rejoined_string               

    # Function to get rid of funky characters that exist in a string
    # so that when for example writing a file to disk, the filename 
    # doesn't contain any special reserved characters.
    # This list of special_chars probably contains some characters that are okay.            
    def replace_special_char(self, string, repl='-'):
        # Regular Expression Special Chars =  . ^ $ * + ? { [ ] \ | ( )
        special_chars = [ '\"',  '\`', '\\\\', '/','~' ]
        new_string = string
        num = 0
       
        for j in special_chars:
            pattern = j
            try: 
                # A few of the special characters get automatically converted to a
                # different char, rather than what is passed in as repl
                if (pattern == "\'"):
                    (new_string, num) = re.subn(pattern, "\\\'", new_string, count=0)
                elif (pattern == '/'):
                    (new_string, num) = re.subn(pattern, '\\\\', new_string, count=0) 
                else:
                    (new_string, num) = re.subn(pattern, repl, new_string, count=0)
            except:
                _debug_( _( 'ERROR' ) + ': ' + _( 'Problem trying to call:' ) + ' re.subn' )
        return new_string

    def fix_case(self, string):
        if config.RIP_TITLE_CASE:
            return util.title_case(string)
        else:
            return string
