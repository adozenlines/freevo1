#if 0 /*
# -----------------------------------------------------------------------
# mplayer.py - the Freevo MPlayer module for video
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.58  2004/01/13 15:03:45  dischi
# add version detection patch
#
# Revision 1.57  2004/01/11 23:21:58  outlyer
# Fix for this crash:
#
# Traceback (most recent call last):
#   File "/usr/lib/python2.3/site-packages/freevo/main.py", line 435, in ?
#     child.poll()
#   File "/usr/lib/python2.3/site-packages/freevo/childapp.py", line 610, in poll
#     rc.post_event(self.stop_event())
#   File "/usr/lib/python2.3/site-packages/freevo/video/plugins/mplayer.py", line 505, in stop_event
#     print _( 'ERROR' ) + ': ' + self.exit_type + \
# TypeError: cannot concatenate 'str' and 'NoneType' objects
#
# Revision 1.56  2004/01/02 11:17:35  dischi
# cleanup
#
# Revision 1.55  2004/01/01 19:37:31  dischi
# dvd and interlace fixes
#
# Revision 1.54  2003/12/29 22:29:09  dischi
# remove debug
#
# Revision 1.53  2003/12/29 22:08:54  dischi
# move to new Item attributes
#
# Revision 1.52  2003/12/22 13:27:34  dischi
# patch for better support of fxd files with more discs from Matthieu Weber
#
# Revision 1.51  2003/12/15 03:45:29  outlyer
# Added onscreen notification of bookmark being added via mplayer's
# osd_show_text... older versions of mplayer will ignore the command so
# it should be a non-issue to add this in without checking the version.
#
# Revision 1.50  2003/12/10 19:47:49  dischi
# make it possible to bypass version checking
#
# Revision 1.49  2003/12/10 19:06:06  dischi
# move to new ChildApp2 and remove the internal thread
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
#endif


import os, re
import threading
import popen2

import config     # Configuration handler. reads config file.
import util       # Various utilities
import childapp   # Handle child applications
import rc         # The RemoteControl class.
import plugin

from event import *


class PluginInterface(plugin.Plugin):
    """
    Mplayer plugin for the video player.

    With this plugin Freevo can play all video files defined in
    VIDEO_MPLAYER_SUFFIX. This is the default video player for Freevo.
    """
    def __init__(self):
        mplayer_version = 0

        # Detect version of mplayer. Possible values are
        # 0.9 (for 0.9.x series), 1.0 (for 1.0preX series) and 9999 for cvs
        if not hasattr(config, 'MPLAYER_VERSION'):
            child = popen2.Popen3( "%s -v" % config.MPLAYER_CMD, 1, 100)
            data  = True
            while data:
                data = child.fromchild.readline()
                if data:
                    data = re.search( "^MPlayer (?P<version>\S+)", data )
                    if data:                
                        break

            if data:                
                _debug_("MPlayer version is: %s" % data.group( "version" ))
                data = data.group( "version" )
                if data[ 0 ] == "1":
                    config.MPLAYER_VERSION = 1.0
                elif data[ 0 ] == "0":
                    config.MPLAYER_VERSION = 0.9
                elif data[ 0 : 7 ] == "dev-CVS":
                    config.MPLAYER_VERSION = 9999
            else:
                config.MPLAYER_VERSION = None
            _debug_("MPlayer version set to: %s" % config.MPLAYER_VERSION)
            child.wait()

        if not config.MPLAYER_VERSION:
            self.reason = 'failed to detect mplayer version'
            return
        
        # create plugin structure
        plugin.Plugin.__init__(self)

        # register mplayer as the object to play video
        plugin.register(MPlayer(config.MPLAYER_VERSION), plugin.VIDEO_PLAYER, True)





class MPlayer:
    """
    the main class to control mplayer
    """
    def __init__(self, version):
        """
        init the mplayer object
        """
        self.name       = 'mplayer'

        self.app_mode   = 'video'
        self.version    = version
        self.seek       = 0
        self.seek_timer = threading.Timer(0, self.reset_seek)
        self.app        = None


    def rate(self, item):
        """
        How good can this player play the file:
        2 = good
        1 = possible, but not good
        0 = unplayable
        """
        if item.url in ('dvd://', 'vcd://'):
            return 1
        if item.mode in ('dvd', 'vcd'):
            return 2
        if item.mimetype in config.VIDEO_MPLAYER_SUFFIX:
            return 2
        if item.network_play:
            return 1
        return 0
    
    
    def play(self, options, item):
        """
        play a videoitem with mplayer
        """
        self.options = options
        self.item    = item
        
        mode         = item.mode
        url          = item.url

        if mode == 'file':
            url = item.url[6:]

        if url == 'dvd://':
            url += '1'
            
        if url == 'vcd://':
            c_len = 0
            for i in range(len(item.info.tracks)):
                if item.info.tracks[i].length > c_len:
                    c_len = item.info.tracks[i].length
                    url = item.url + str(i+1)
            
        try:
            _debug_('MPlayer.play(): mode=%s, url=%s' % (mode, url))
        except UnicodeError:
            _debug_('MPlayer.play(): [non-ASCII data]')

        if mode == 'file' and not os.path.isfile(url):
            # This event allows the videoitem which contains subitems to
            # try to play the next subitem
            return '%s\nnot found' % os.path.basename(url)
       

        # Build the MPlayer command
        command = [ '--prio=%s' % config.MPLAYER_NICE, config.MPLAYER_CMD ] + \
                  config.MPLAYER_ARGS_DEF.split(' ') + \
                  [ '-slave', '-ao', config.MPLAYER_AO_DEV ]

        additional_args = []

        if mode == 'dvd':
            if config.DVD_LANG_PREF:
                # There are some bad mastered DVDs out there. E.g. the specials on
                # the German Babylon 5 Season 2 disc claim they have more than one
                # audio track, even more then on en. But only the second en works,
                # mplayer needs to be started without -alang to find the track
                if hasattr(item, 'mplayer_audio_broken') and item.mplayer_audio_broken:
                    print '*** dvd audio broken, try without alang ***'
                else:
                    additional_args += [ '-alang', config.DVD_LANG_PREF ]

            if config.DVD_SUBTITLE_PREF:
                # Only use if defined since it will always turn on subtitles
                # if defined
                additional_args += [ '-slang', config.DVD_SUBTITLE_PREF ]

            additional_args += [ '-dvd-device', item.media.devicename ]

        if item.media:
            additional_args += [ '-cdrom-device', item.media.devicename ]

        if item.selected_subtitle == -1:
            additional_args += [ '-noautosub' ]

        elif item.selected_subtitle and mode == 'file':
            additional_args += [ '-vobsubid', item.selected_subtitle ]

        elif item.selected_subtitle:
            additional_args += [ '-sid', item.selected_subtitle ]
            
        if item.selected_audio:
            additional_args += [ '-aid', item.selected_audio ]

        if self.version >= 1 and item.deinterlace:
            additional_args += [ '-vf',  'pp=de/fd' ]
        elif item.deinterlace:
            additional_args += [ '-vop', 'pp=fd' ]
        elif self.version >= 1:
            additional_args += [ '-vf',  'pp=de' ]
                
        mode = item.mimetype
        if not config.MPLAYER_ARGS.has_key(mode):
            mode = 'default'

        # Mplayer command and standard arguments
        command += [ '-v', '-vo', config.MPLAYER_VO_DEV +
                     config.MPLAYER_VO_DEV_OPTS ]

        # mode specific args
        command += config.MPLAYER_ARGS[mode].split(' ')

        # make the options a list
        command += additional_args

        if hasattr(item, 'is_playlist') and item.is_playlist:
            command.append('-playlist')

        # add the file to play
        command.append(url)

        if options:
            command += options

        # use software scaler?
        if '-nosws' in command:
            command.remove('-nosws')

        elif not '-framedrop' in command:
            command += config.MPLAYER_SOFTWARE_SCALER.split(' ')

        # correct avi delay based on mmpython settings
        if config.MPLAYER_SET_AUDIO_DELAY and item.info.has_key('delay') and \
               item.info['delay'] > 0:
            command += [ '-mc', str(int(item.info['delay'])+1), '-delay',
                         '-' + str(item.info['delay']) ]

        while '' in command:
            command.remove('')

        # autocrop
        if config.MPLAYER_AUTOCROP and str(' ').join(command).find('crop=') == -1:
            _debug_('starting autocrop')
            (x1, y1, x2, y2) = (1000, 1000, 0, 0)
            crop_cmd = command[1:] + ['-ao', 'null', '-vo', 'null', '-ss', '60',
                                      '-frames', '20', '-vop', 'cropdetect' ]
            child = popen2.Popen3(self.sort_filter(crop_cmd), 1, 100)
            exp = re.compile('^.*-vop crop=([0-9]*):([0-9]*):([0-9]*):([0-9]*).*')
            while(1):
                data = child.fromchild.readline()
                if not data:
                    break
                m = exp.match(data)
                if m:
                    x1 = min(x1, int(m.group(3)))
                    y1 = min(y1, int(m.group(4)))
                    x2 = max(x2, int(m.group(1)) + int(m.group(3)))
                    y2 = max(y2, int(m.group(2)) + int(m.group(4)))
        
            if x1 < 1000 and x2 < 1000:
                command = command + [ '-vop' , 'crop=%s:%s:%s:%s' % (x2-x1, y2-y1, x1, y1) ]
            
            child.wait()

        if item.subtitle_file:
            d, f = util.resolve_media_mountdir(item.subtitle_file)
            util.mount(d)
            command += ['-sub', f]

        if item.audio_file:
            d, f = util.resolve_media_mountdir(item.audio_file)
            util.mount(d)
            command += ['-audiofile', f]

        self.plugins = plugin.get('mplayer_video')

        for p in self.plugins:
            command = p.play(command, self)

        command=self.sort_filter(command)

        if plugin.getbyname('MIXER'):
            plugin.getbyname('MIXER').reset()

        rc.app(self)

        self.app = MPlayerApp(command, self)
        return None
    

    def stop(self):
        """
        Stop mplayer
        """
        if not self.app:
            return
        
        self.app.stop('quit\n')
        rc.app(None)
        self.app = None

        for p in self.plugins:
            command = p.stop()


    def eventhandler(self, event, menuw=None):
        """
        eventhandler for mplayer control. If an event is not bound in this
        function it will be passed over to the items eventhandler
        """
        if not self.app:
            return self.item.eventhandler(event)

        for p in self.plugins:
            if p.eventhandler(event):
                return True

        if event == VIDEO_MANUAL_SEEK:
            self.seek = 0
            rc.set_context('input')
            return True
        
        if event.context == 'input':
            if event in INPUT_ALL_NUMBERS:
                self.reset_seek_timeout()
                self.seek = self.seek * 10 + int(event);
                return True
            
            elif event == INPUT_ENTER:
                self.seek_timer.cancel()
                self.seek *= 60
                self.app.write('seek ' + str(self.seek) + ' 2\n')
                _debug_("seek "+str(self.seek)+" 2\n")
                self.seek = 0
                rc.set_context('video')
                return True

            elif event == INPUT_EXIT:
                _debug_('seek stopped')
                self.seek_timer.cancel()
                self.seek = 0
                rc.set_context('video')
                return True

        if event == STOP:
            self.stop()
            return self.item.eventhandler(event)

        if event == 'AUDIO_ERROR_START_AGAIN':
            self.stop()
            self.play(self.options, self.item)
            return True
        
        if event in ( PLAY_END, USER_END ):
            self.stop()
            return self.item.eventhandler(event)

        if event == VIDEO_SEND_MPLAYER_CMD:
            self.app.write('%s\n' % event.arg)
            return True

        if event == TOGGLE_OSD:
            self.app.write('osd\n')
            return True

        if event == PAUSE or event == PLAY:
            self.app.write('pause\n')
            return True

        if event == SEEK:
            self.app.write('seek %s\n' % event.arg)
            return True

        if event == OSD_MESSAGE:
            self.app.write('osd_show_text "%s"\n' % event.arg);
            return True

        # nothing found? Try the eventhandler of the object who called us
        return self.item.eventhandler(event)

    
    def reset_seek(self):
        _debug_('seek timeout')
        self.seek = 0
        rc.set_context('video')

        
    def reset_seek_timeout(self):
        self.seek_timer.cancel()
        self.seek_timer = threading.Timer(config.MPLAYER_SEEK_TIMEOUT, self.reset_seek)
        self.seek_timer.start()

        
    def sort_filter(self, command):
        """
        Change a mplayer command to support more than one -vop
        parameter. This function will grep all -vop parameter from
        the command and add it at the end as one vop argument
        """
        ret = []
        vop = ''
        next_is_vop = False
    
        for arg in command:
            if next_is_vop:
                vop += ',%s' % arg
                next_is_vop = False
            elif (arg == '-vop' or arg == '-vf'):
                next_is_vop=True
            else:
                ret += [ arg ]

        if vop:
            if self.version >= 1:
                return ret + [ '-vf', vop[1:] ]
            return ret + [ '-vop', vop[1:] ]
        return ret



# ======================================================================


class MPlayerApp(childapp.ChildApp2):
    """
    class controlling the in and output from the mplayer process
    """

    def __init__(self, app, mplayer):
        self.RE_TIME   = re.compile("^A: *([0-9]+)").match
        self.RE_START  = re.compile("^Starting playback\.\.\.").match
        self.RE_EXIT   = re.compile("^Exiting\.\.\. \((.*)\)$").match
        self.item      = mplayer.item
        self.mplayer   = mplayer
        self.exit_type = None
                       
        # DVD items also store mplayer_audio_broken to check if you can
        # start them with -alang or not
        if hasattr(self.item, 'mplayer_audio_broken') or self.item.mode != 'dvd':
            self.check_audio = 0
        else:
            self.check_audio = 1

        import osd     
        self.osd       = osd.get_singleton()
        self.osdfont   = self.osd.getfont(config.OSD_DEFAULT_FONTNAME,
                                          config.OSD_DEFAULT_FONTSIZE)

        # check for mplayer plugins
        self.stdout_plugins  = []
        self.elapsed_plugins = []
        for p in plugin.get('mplayer_video'):
            if hasattr(p, 'stdout'):
                self.stdout_plugins.append(p)
            if hasattr(p, 'elapsed'):
                self.elapsed_plugins.append(p)

        # init the child (== start the threads)
        childapp.ChildApp2.__init__(self, app)


                
    def stop_event(self):
        """
        return the stop event send through the eventhandler
        """
        if self.exit_type == "End of file":
            return PLAY_END
        elif self.exit_type == "Quit":
            return USER_END
        else:
            print _( 'ERROR' ) + ': ' + str(self.exit_type) + \
                  _( 'unknow error while playing file' )
            return PLAY_END
                        

    def stdout_cb(self, line):
        """
        parse the stdout of the mplayer process
        """
        # show connection status for network play
        if self.item.network_play:
            if line.find('Opening audio decoder') == 0:
                self.osd.clearscreen(self.osd.COL_BLACK)
                self.osd.update()
            elif (line.startswith('Resolving ') or \
                  line.startswith('Connecting to server') or \
                  line.startswith('Cache fill:')) and \
                  line.find('Resolving reference to') == -1:

                if line.startswith('Connecting to server'):
                    line = 'Connecting to server'
                self.osd.clearscreen(self.osd.COL_BLACK)
                self.osd.drawstringframed(line, config.OSD_OVERSCAN_X+10,
                                          config.OSD_OVERSCAN_Y+10,
                                          self.osd.width - 2 * (config.OSD_OVERSCAN_X+10),
                                          -1, self.osdfont, self.osd.COL_WHITE)
                self.osd.update()


        # current elapsed time
        if line.find("A:") == 0:
            m = self.RE_TIME(line)
            if hasattr(m,'group'):
                self.item.elapsed = int(m.group(1))+1
                for p in self.elapsed_plugins:
                    p.elapsed(self.item.elapsed)


        # exit status
        elif line.find("Exiting...") == 0:
            m = self.RE_EXIT(line)
            if m:
                self.exit_type = m.group(1)


        # this is the first start of the movie, parse infos
        elif not self.item.elapsed:
            for p in self.stdout_plugins:
                p.stdout(line)
                
            if self.check_audio:
                if line.find('MPEG: No audio stream found -> no sound') == 0:
                    # OK, audio is broken, restart without -alang
                    self.check_audio = 2
                    self.item.mplayer_audio_broken = True
                    rc.post_event(Event('AUDIO_ERROR_START_AGAIN'))
                
                if self.RE_START(line):
                    if self.check_audio == 1:
                        # audio seems to be ok
                        self.item.mplayer_audio_broken = False
                    self.check_audio = 0



    def stderr_cb(self, line):
        """
        parse the stderr of the mplayer process
        """
        for p in self.stdout_plugins:
            p.stdout(line)
