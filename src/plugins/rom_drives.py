#if 0 /*
# -----------------------------------------------------------------------
# rom_drives.py - the Freevo identifymedia/automount plugin
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.54  2004/02/05 20:47:33  dischi
# fix audio disc info
#
# Revision 1.53  2004/01/31 16:38:23  dischi
# changes because of mediainfo changes
#
# Revision 1.52  2004/01/18 16:51:05  dischi
# (re)move unneeded variables
#
# Revision 1.51  2004/01/17 20:30:18  dischi
# use new metainfo
#
# Revision 1.50  2004/01/10 16:52:19  dischi
# shut down identify thread before exit to prevent a strange error sometimes
#
# Revision 1.49  2004/01/03 17:43:15  dischi
# OVERLAY_DIR is always used
#
# Revision 1.48  2003/12/30 15:30:56  dischi
# IDENTIFY_MEDIA now sends the media as arg
#
# Revision 1.47  2003/12/29 22:09:38  dischi
# move to new Item attributes
#
# Revision 1.46  2003/12/14 17:15:19  dischi
# check if CDROM.py is complete
#
# Revision 1.45  2003/11/30 14:41:10  dischi
# use new Mimetype plugin interface
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

import time, os
from fcntl import ioctl
import re
import threading
import thread
import string
import copy
import traceback
import util.mediainfo
from struct import *
import array
import rc


try:
    from CDROM import *
    # test if CDROM_DRIVE_STATUS is there
    # (for some strange reason, this is missing sometimes)
    CDROM_DRIVE_STATUS
except:
    if os.uname()[0] == 'FreeBSD':
        # FreeBSD ioctls - there is no CDROM.py...
        CDIOCEJECT = 0x20006318
        CDIOCCLOSE = 0x2000631c
        CDIOREADTOCENTRYS = 0xc0086305
        CD_LBA_FORMAT = 1
        CD_MSF_FORMAT = 2
        CDS_NO_DISC = 1
        CDS_DISC_OK = 4
    else:
        # strange ioctrls missing
        CDROMEJECT = 0x5309
        CDROMCLOSETRAY = 0x5319
        CDROM_DRIVE_STATUS = 0x5326
        CDROM_SELECT_SPEED = 0x5322
        CDS_NO_DISC = 1
        CDS_DISC_OK = 4
        

import config
import util
import rc
import plugin
import video

from event import *
from directory import DirItem
from gui import PopupBox
from item import Item
from audio import AudioDiskItem
from video import VideoItem

LABEL_REGEXP = re.compile("^(.*[^ ]) *$").match


# Identify_Thread
im_thread = None


def init():
    """
    create a list of media objects and start the Identify_Thread
    """
    # Add the drives to the config.removable_media list. There doesn't have
    # to be any drives defined.
    if config.ROM_DRIVES != None: 
        for i in range(len(config.ROM_DRIVES)):
            (dir, device, name) = config.ROM_DRIVES[i]
            media = RemovableMedia(mountdir=dir, devicename=device,
                                   drivename=name)
            # close the tray without popup message
            media.move_tray(dir='close', notify=0)
            config.REMOVABLE_MEDIA.append(media)

    # Remove the ROM_DRIVES member to make sure it is not used by
    # legacy code!
    del config.ROM_DRIVES
    
    # Start identifymedia thread
    global im_thread
    im_thread = Identify_Thread()
    im_thread.setDaemon(1)
    im_thread.start()


def shutdown():
    """
    shut down the Identify_Thread
    """
    global im_thread
    if im_thread.isAlive():
        _debug_('stopping Identify_Thread', 2)
        im_thread.stop = True
        while im_thread.isAlive():
            time.sleep(0.1)
        

class autostart(plugin.DaemonPlugin):
    """
    Plugin to autostart if a new medium is inserted while Freevo shows
    the main menu
    """
    def __init__(self):
        """
        load the plugin and start the thread
        """
        plugin.DaemonPlugin.__init__(self)
        global im_thread
        if not im_thread:
            init()

            
    def eventhandler(self, event = None, menuw=None, arg=None):
        """
        eventhandler to handle the IDENTIFY_MEDIA plugin event and the
        EJECT event
        """
        global im_thread

        # if we are at the main menu and there is an IDENTIFY_MEDIA event,
        # try to autorun the media
        if plugin.isevent(event) == 'IDENTIFY_MEDIA' and menuw and \
               len(menuw.menustack) == 1 and not event.arg[1]:
            media = event.arg[0]
            if media.item:
                media.item.parent = menuw.menustack[0].selected
            if media.item and media.item.actions():
                media.item.actions()[0][0](menuw=menuw)
            else:
                menuw.refresh()
            return True

        # Handle the EJECT key for the main menu
        elif event == EJECT and len(menuw.menustack) == 1:

            # Are there any drives defined?
            if config.REMOVABLE_MEDIA:
                # The default is the first drive in the list
                media = config.REMOVABLE_MEDIA[0]  
                media.move_tray(dir='toggle')
                return True
            
    def shutdown(self):
        shutdown()


class rom_items(plugin.MainMenuPlugin):
    """
    Plugin to add the rom drives to a main menu. This can be the global main menu
    or most likely the video/audio/image/games main menu
    """
    def __init__(self):
        """
        load the plugin and start the thread
        """
        plugin.MainMenuPlugin.__init__(self)
        global im_thread
        if not im_thread:
            init()
        
    def items(self, parent):
        """
        return the list of rom drives
        """
        items = []
        for media in config.REMOVABLE_MEDIA:
            if media.item:
                if parent.display_type == 'video' and media.videoitem:
                    m = media.videoitem
                    
                else:
                    if media.item.type == 'dir':
                        media.item.display_type = parent.display_type
                    m = media.item

            else:
                m = Item(parent)
                m.name = _('Drive %s (no disc)') % media.drivename
                m.type = media.type
                m.media = media
                media.item = m

            m.parent = parent
            m.eventhandler_plugins.append(self.items_eventhandler)
            items.append(m)
            
        return items


    def items_eventhandler(self, event, item, menuw):
        """
        handle EJECT for the rom drives
        """
        if event == EJECT and item.media and menuw and \
           menuw.menustack[1] == menuw.menustack[-1]:
            item.media.move_tray(dir='toggle')
            return True
        return False
    

class RemovableMedia:
    """
    Object about one drive
    """
    def __init__(self, mountdir='', devicename='', drivename=''):
        # This is read-only stuff for the drive itself
        self.mountdir = mountdir
        self.devicename = devicename
        self.drivename = drivename

        # Dynamic stuff
        self.tray_open = 0
        self.drive_status = None  # return code from ioctl for DRIVE_STATUS

        self.id        = ''
        self.label     = ''
        self.item      = None
        self.videoitem = None
        self.type      = 'empty_cdrom'
        self.cached   = False


    def is_tray_open(self):
        """
        return tray status
        """
        return self.tray_open


    def move_tray(self, dir='toggle', notify=1):
        """
        Move the tray. dir can be toggle/open/close
        """
        if dir == 'toggle':
            if self.is_tray_open():
                dir = 'close'
            else:
                dir = 'open'

        if dir == 'open':
            _debug_('Ejecting disc in drive %s' % self.drivename,2)

            if notify:
                pop = PopupBox(text=_('Ejecting disc in drive %s') % self.drivename) 
                pop.show()

            try:
                fd = os.open(self.devicename, os.O_RDONLY | os.O_NONBLOCK)
                if os.uname()[0] == 'FreeBSD':
                    s = ioctl(fd, CDIOCEJECT, 0)
                else:
                    s = ioctl(fd, CDROMEJECT)
                os.close(fd)
            except:
                try:
                    traceback.print_exc()
                except IOError:
                    # believe it or not, this sometimes causes an IOError if
                    # you've got a music track playing in the background (detached)
                    pass
                # maybe we need to close the fd if ioctl fails, maybe
                # open fails and there is no fd
                try:
                    os.close(fd)
                except:
                    pass

            self.tray_open = 1
            if notify:
                pop.destroy()

        
        elif dir == 'close':
            _debug_('Inserting %s' % self.drivename,2)

            if notify:
                pop = PopupBox(text=_('Reading disc in drive %s') % self.drivename)
                pop.show()

            # close the tray, identifymedia does the rest,
            # including refresh screen
            try:
                fd = os.open(self.devicename, os.O_RDONLY | os.O_NONBLOCK)
                if os.uname()[0] == 'FreeBSD':            
                    s = ioctl(fd, CDIOCCLOSE, 0)
                else:
                    s = ioctl(fd, CDROMCLOSETRAY)
                os.close(fd)
            except:
                traceback.print_exc()
                # maybe we need to close the fd if ioctl fails, maybe
                # open fails and there is no fd
                try:
                    os.close(fd)
                except:
                    pass

            self.tray_open = 0
            global im_thread
            if im_thread:
                im_thread.check_all()
            if notify:
                pop.destroy()

    
    def mount(self):
        """
        Mount the media
        """
        _debug_('Mounting disc in drive %s' % self.drivename,2)
        util.mount(self.mountdir, force=True)
        return

    
    def umount(self):
        """
        Mount the media
        """
        _debug_('Unmounting disc in drive %s' % self.drivename,2)
        util.umount(self.mountdir)
        return
    
    def shutdown(self):
        shutdown()


class Identify_Thread(threading.Thread):
    """
    Thread to watch the rom drives for changes
    """
    def identify(self, media):
        """
        magic!
        Try to find out as much as possible about the disc in the
        rom drive: title, image, play options, ...
        """
        # Check drive status (tray pos, disc ready)
        try:
            CDSL_CURRENT = ( (int ) ( ~ 0 >> 1 ) )
            fd = os.open(media.devicename, os.O_RDONLY | os.O_NONBLOCK)
            if os.uname()[0] == 'FreeBSD':
                try:
                    data = array.array('c', '\000'*4096)
                    (address, length) = data.buffer_info()
                    buf = pack('BBHP', CD_MSF_FORMAT, 0, length, address)
                    s = ioctl(fd, CDIOREADTOCENTRYS, buf)
                    s = CDS_DISC_OK
                except:
                    s = CDS_NO_DISC
            else:
                s = ioctl(fd, CDROM_DRIVE_STATUS, CDSL_CURRENT)
        except:
            # maybe we need to close the fd if ioctl fails, maybe
            # open fails and there is no fd
            try:
                os.close(fd)
            except:
                pass
            media.drive_status = None
            return

        # Same as last time? If so we're done
        if s == media.drive_status:
            os.close(fd)
            return

        media.drive_status = s

        media.id        = ''
        media.label     = ''
        media.type      = 'empty_cdrom'
        media.item      = None
        media.videoitem = None
        media.cached    = False

        # Is there a disc present?
        if s != CDS_DISC_OK:
            os.close(fd)
            return

        # if there is a disc, the tray can't be open
        media.tray_open = False
        disc_info = util.mediainfo.disc_info(media)
        data = disc_info.mmdata
        
        # try to set the speed
        if config.ROM_SPEED and data and not data['mime'] == 'video/dvd':
            try:
                ioctl(fd, CDROM_SELECT_SPEED, config.ROM_SPEED)
            except:
                pass

        if data and data['mime'] == 'audio/cd':
            os.close(fd)
            disc_id = data['id']
            media.item = AudioDiskItem(disc_id, parent=None,
                                       devicename=media.devicename,
                                       display_type='audio')
            media.type = media.item.type
            media.item.media = media
            if data['title']:
                media.item.name = data['title']
            media.item.info = disc_info
            return

        os.close(fd)
        image = title = movie_info = more_info = fxd_file = None

        media.id    = data['id']
        media.label = data['label']
        media.type  = 'cdrom'

        label = data['label']

        # is the id in the database?
        if media.id in video.fxd_database['id']:
            movie_info = video.fxd_database['id'][media.id]
            if movie_info:
                title = movie_info.name
            
        # no? Maybe we can find a label regexp match
        else:
            for (re_label, movie_info_t) in video.fxd_database['label']:
                if re_label.match(media.label):
                    movie_info = movie_info_t
                    if movie_info_t.name:
                        title = movie_info.name
                        m = re_label.match(media.label).groups()
                        re_count = 1

                        # found, now change the title with the regexp. E.g.:
                        # label is "bla_2", the label regexp "bla_[0-9]" and the title
                        # is "Something \1", the \1 will be replaced with the first item
                        # in the regexp group, here 2. The title is now "Something 2"
                        for g in m:
                            title=string.replace(title, '\\%s' % re_count, g)
                            re_count += 1
                        break
                
        if movie_info:
            image = movie_info.image
                        

        # DVD/VCD/SVCD:
        # There is data from mmpython for these three types
        if data['mime'] in ('video/vcd', 'video/dvd'):
            if not title:
                title = '%s [%s]' % (data['mime'][6:].upper(), media.label)

            if movie_info:
                media.item = copy.copy(movie_info)
            else:
                media.item = VideoItem('', None)
                media.item.image = util.getimage(os.path.join(config.OVERLAY_DIR,
                                                              'disc-set', media.id))
            variables = media.item.info.variables
            media.item.info = disc_info
            media.item.info.set_variables(variables)

            media.item.name  = title
            media.item.set_url(data['mime'][6:] + '://')
            media.item.media = media

            media.type  = data['mime'][6:]

            media.item.info.mmdata = data

            # copy configure options from track[0] to main item
            # for playback
            for k in ('audio', 'subtitles', 'chapters' ):
                if data['tracks'][0].has_key(k):
                    if not data.has_key(k):
                        data[k] = data['tracks'][0][k]

            media.item.num_titles = len(data['tracks'])
            return

        # Disc is data of some sort. Mount it to get the file info
        util.mount(media.mountdir, force=True)
        
        # Check for movies/audio/images on the disc
        mplayer_files = util.match_files(media.mountdir, config.VIDEO_SUFFIX)
        mp3_files = util.match_files(media.mountdir, config.AUDIO_SUFFIX)
        image_files = util.match_files(media.mountdir, config.IMAGE_SUFFIX)
        
        _debug_('identifymedia: mplayer = "%s"' % mplayer_files, level = 2)
        _debug_('identifymedia: mp3="%s"' % mp3_files, level = 2)
        _debug_('identifymedia: image="%s"' % image_files, level = 2)
            
        media.item = DirItem(media.mountdir, None)
        media.item.info = disc_info
        util.umount(media.mountdir)
        
        # Is this a movie disc?
        if mplayer_files and not mp3_files:
            media.type = 'video'

            # try to find out if it is a series cd
            if not title:
                show_name = ""
                the_same  = 1
                volumes   = ''
                start_ep  = 0
                end_ep    = 0

                mplayer_files.sort(lambda l, o: cmp(l.upper(), o.upper()))

                for movie in mplayer_files:
                    if config.VIDEO_SHOW_REGEXP_MATCH(movie):
                        show = config.VIDEO_SHOW_REGEXP_SPLIT(os.path.basename(movie))

                        if show_name and show_name != show[0]:
                            the_same = 0
                        if not show_name:
                            show_name = show[0]
                        if volumes:
                            volumes += ', '
                        current_ep = int(show[1]) * 100 + int(show[2])
                        if end_ep and current_ep == end_ep + 1:
                            end_ep = current_ep
                        elif not end_ep:
                            end_ep = current_ep
                        else:
                            end_ep = -1
                        if not start_ep:
                            start_ep = end_ep
                        volumes += show[1] + "x" + show[2]

                if show_name and the_same and config.VIDEO_SHOW_DATA_DIR:
                    if end_ep > 0:
                        volumes = '%dx%02d - %dx%02d' % (start_ep / 100, start_ep % 100,
                                                         end_ep / 100, end_ep % 100)
                    k = config.VIDEO_SHOW_DATA_DIR + show_name
                    if os.path.isfile((k + ".png").lower()):
                        image = (k + ".png").lower()
                    elif os.path.isfile((k + ".jpg").lower()):
                        image = (k + ".jpg").lower()
                    title = show_name + ' ('+ volumes + ')'
                    if video.tv_show_informations.has_key(show_name.lower()):
                        tvinfo = video.tv_show_informations[show_name.lower()]
                        more_info = tvinfo[1]
                        if not image:
                            image = tvinfo[0]
                        if not fxd_file:
                            fxd_file = tvinfo[3]
                        
                elif (not show_name) and len(mplayer_files) == 1:
                    movie = mplayer_files[0]
                    title = os.path.splitext(os.path.basename(movie))[0]

            # nothing found, give up: return the label
            if not title:
                title = label


        # XXX add more intelligence to cds with audio files
        elif (not mplayer_files) and mp3_files:
            media.type = 'audio'
            title = '%s [%s]' % (media.drivename, label)

        # XXX add more intelligence to cds with image files
        elif (not mplayer_files) and (not mp3_files) and image_files:
            media.type = 'image'
            title = '%s [%s]' % (media.drivename, label)

        # Mixed media?
        elif mplayer_files or image_files or mp3_files:
            media.type = None
            title = '%s [%s]' % (media.drivename, label)
        
        # Strange, no useable files
        else:
            media.type = None
            title = '%s [%s]' % (media.drivename, label)


        if title:
            media.item.name = title
        if image:
            media.item.image = image
        if more_info:
            media.item.info.set_variables(more_info)
        if fxd_file and not media.item.fxd_file:
            media.item.set_fxd_file(fxd_file)
            
        if len(mplayer_files) == 1:
            util.mount(media.mountdir)
            if movie_info:
                media.videoitem = copy.deepcopy(movie_info)
            else:
                media.videoitem = VideoItem(mplayer_files[0], None)
            util.umount(media.mountdir)
            media.videoitem.media    = media
            media.videoitem.media_id = media.id
            
            if title:
                media.videoitem.name = title
            if image:
                media.videoitem.image = image
            if more_info:
                media.videoitem.set_variables(more_info)
            if fxd_file:
                media.videoitem.fxd_file = fxd_file
                
        media.item.media = media
        return


    def check_all(self):
        """
        check all drives
        """
        if rc.app():
            # Some app is running, do not scan, it's not necessary
            return
        
        self.lock.acquire()
        for media in config.REMOVABLE_MEDIA:
            last_status = media.drive_status
            self.identify(media)

            if last_status != media.drive_status:
                _debug_('MEDIA: Status=%s' % media.drive_status,2)
                _debug_('Posting IDENTIFY_MEDIA event',2)
                if last_status == None:
                    rc.post_event(plugin.event('IDENTIFY_MEDIA', arg=(media, True)))
                else:
                    rc.post_event(plugin.event('IDENTIFY_MEDIA', arg=(media, False)))
        self.lock.release()

                
    def __init__(self):
        """
        init the thread
        """
        threading.Thread.__init__(self)
        self.lock = thread.allocate_lock()

        
    def run(self):
        """
        thread main function
        """
        rebuild_file = '/tmp/freevo-rebuild-database'
        # Make sure the movie database is rebuilt at startup
        util.touch(rebuild_file)
        while 1:
            # Check if we need to update the database
            # This is a simple way for external apps to signal changes
            if os.path.exists(rebuild_file):
                if video.hash_fxd_movie_database() == 0:
                    # something is wrong, deactivate this feature
                    rebuild_file = '/this/file/should/not/exist'
                    
                for media in config.REMOVABLE_MEDIA:
                    media.drive_status = None

            if not rc.app():
                # check only in the menu
                self.check_all()

            for i in range(4):
                # wait some time
                time.sleep(0.5)

                # check if we need to stop
                if hasattr(self, 'stop'):
                    return

