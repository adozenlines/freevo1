#if 0 /*
# -----------------------------------------------------------------------
# audioitem - Item for mp3 and ogg files
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.48  2004/01/31 11:20:15  dischi
# cdda is not network play
#
# Revision 1.47  2004/01/27 17:24:43  outlyer
# Use the tag title if available and DIRECTORY_USE_MEDIAID_TAG_NAMES is set.
#
# Revision 1.46  2004/01/25 11:20:09  dischi
# make sure length is an int
#
# Revision 1.45  2003/12/31 16:42:40  dischi
# changes, related to item.py changes
#
# Revision 1.44  2003/12/30 15:34:42  dischi
# remove unneeded copy function
#
# Revision 1.43  2003/12/29 22:09:18  dischi
# move to new Item attributes
#
# Revision 1.42  2003/12/12 19:20:46  dischi
# use util functions to get the image
#
# Revision 1.41  2003/11/28 20:08:57  dischi
# renamed some config variables
#
# Revision 1.40  2003/11/23 17:03:43  dischi
# Removed fxd handling from AudioItem and created a new FXDHandler class
# in __init__.py to let the directory handle the fxd files. The format
# of audio fxd files changed a bit to match the video fxd format. See
# __init__.py for details.
#
# Revision 1.39  2003/11/22 20:36:34  dischi
# use new vfs
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


import os
import string
import time
import re
import traceback
import config
import util
import rc

from player import PlayerGUI
from item import Item


class AudioItem(Item):
    """
    This is the common class to get information about audiofiles.
    """
    
    def __init__(self, url, parent, name=None, scan=True):
        Item.__init__(self, parent, info=scan)

        self.type       = 'audio'
        self.set_url(url, info=scan)

        if name:
            self.name   = name

        if self.info['title'] and config.DIRECTORY_USE_MEDIAID_TAG_NAMES:
            self.name = self.info['title']

        self.start      = 0
        self.elapsed    = 0
        self.remain     = 0
        self.done       = 0.0
        self.pause      = 0
	self.valid	= 1

        self.mplayer_options = ''
            
        try:
            self.length = int(self.info['length'])
        except:
            self.length = 0
            
        # Let's try to find if there is any image in the current directory
        # that could be used as a cover
        if self.filename and not self.image and not \
           (self.parent and self.parent.type == 'dir'):
            images = ()
            covers = ()
            files =()
            def image_filter(x):
                return re.match('.*(jpg|png)$', x, re.IGNORECASE)
            def cover_filter(x):
                return re.search(config.AUDIO_COVER_REGEXP, x, re.IGNORECASE)

            # Pick an image if it is the only image in this dir, or it matches
            # the configurable regexp
            dirname = os.path.dirname(self.filename)
            try:
                files = os.listdir(dirname)
            except OSError:
                print "oops, os.listdir() error"
                traceback.print_exc()
            images = filter(image_filter, files)
            image = None
            if len(images) == 1:
                image = os.path.join(dirname, images[0])
            elif len(images) > 1:
                covers = filter(cover_filter, images)
                if covers:
                    image = os.path.join(dirname, covers[0])
            self.image = image


    def sort(self, mode=None):
        """
        Returns the string how to sort this item
        """
        if mode == 'date':
            if self.filename:
                return '%s%s' % (os.stat(self.filename).st_ctime, self.filename)
        return self.url


    def set_url(self, url, info=True):
        """
        Sets a new url to the item. Always use this function and not set 'url'
        directly because this functions also changes other attributes, like
        filename, mode and network_play
        """
        Item.set_url(self, url, info)
        if url.startswith('cdda://'):
            self.network_play = False
            self.mimetype = 'cdda'


    def __getitem__(self, key):
        """
        return the specific attribute as string or an empty string
        """
        if key  == 'length' and self.length:
            # maybe the length was wrong
            if self.length < self.elapsed:
                self.length = self.elapsed
            return '%d:%02d' % (int(self.length / 60), int(self.length % 60))

        if key  == 'elapsed':
            return '%d:%02d' % (int(self.elapsed / 60), int(self.elapsed % 60))
            
        return Item.__getitem__(self, key)

   
    # ----------------------------------------------------------------------------

    def actions(self):
        """
        return a list of possible actions on this item
        """
        return [ ( self.play, 'Play' ) ]


    def play(self, arg=None, menuw=None):
        """
        Start playing the item
        """
        print self.network_play
        self.parent.current_item = self
        self.elapsed = 0

        if not self.menuw:
            self.menuw = menuw

        self.player = PlayerGUI(self, menuw)
        error = self.player.play()

        if error and menuw:
            AlertBox(text=error).show()
            rc.post_event(rc.PLAY_END)


    def stop(self, arg=None, menuw=None):
        """
        Stop the current playing
        """
        self.player.stop()


    def format_track(self):
        """ Return a formatted string for use in music.py """
	# Since we can't specify the length of the integer in the
	# format string (Python doesn't seem to recognize it) we
	# strip it out first, when we see the only thing that can be
	# a number.


        # Before we begin, make sure track is an integer
    
        if self.track:
            try:
    	        mytrack = ('%0.2d' % int(self.track))
            except ValueError:
    	        mytrack = None
        else:
           mytrack = None
    
        song_info = {  'a'  : self.artist,
       	               'l'  : self.album,
    	               'n'  : mytrack,
    	               't'  : self.title,
    	               'y'  : self.year,
    	               'f'  : self.name }

        if self.parent and hasattr(self.parent, 'AUDIO_FORMAT_STRING'):
            return self.parent.DIRECTORY_AUDIO_FORMAT_STRING % song_info
        return config.DIRECTORY_AUDIO_FORMAT_STRING % song_info
        
