#if 0 /*
# -----------------------------------------------------------------------
# mameitem.py - Item for mame objects
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.18  2004/02/24 17:04:39  mikeruelle
# Add some info to the info area where we have it
#
# Revision 1.17  2004/01/19 21:33:02  mikeruelle
#  a patch from Sylvian to use the new set_url stuff
#
# Revision 1.16  2004/01/14 18:29:49  mikeruelle
# .
#
# Revision 1.15  2003/12/29 22:30:35  dischi
# move to new Item attributes
#
# Revision 1.14  2003/12/03 17:25:04  mikeruelle
# they seem to have lost a patch i put in.
#
# Revision 1.13  2003/09/05 20:48:35  mikeruelle
# new game system
#
# Revision 1.12  2003/08/23 12:51:42  dischi
# removed some old CVS log messages
#
# Revision 1.11  2003/06/20 01:31:14  rshortt
# Adding support for a seperate directory for screen/titleshots.  They show
# up in the MAME menu like album covers do in the audio menu.
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
import re

import config
import util
import game
import rc

# Set to 1 for debug output
DEBUG = config.DEBUG

TRUE  = 1
FALSE = 0

import menu
import event as em
import time
import copy
import mame_cache

from item import Item


class MameItem(Item):
    def __init__(self, title, file, image = None, cmd = None, args = None, imgpath = None, parent = None):
        Item.__init__(self, parent)
        self.type  = 'mame'            # fix value
        self.set_url(file, info=True)
        self.image = image
        self.name  = title
        self.parent = parent

        # find image for this file
        if image == None:
            shot = imgpath + '/' + \
                os.path.splitext(os.path.basename(file))[0] + ".png"
            if os.path.isfile(shot):
                self.image = shot
            elif os.path.isfile(os.path.splitext(file)[0] + ".png"):
                self.image = os.path.splitext(file)[0] + ".png"

        command = '--prio=%s %s %s' % (config.GAMES_NICE,
                                       cmd,
                                       args)

        # Some files needs special arguments to mame, they can be
        # put in a <file>.mame options file. The <file>
        # includes the suffix (.zip, etc)!
        # The arguments in the options file are added at the end of the
        # regular mame arguments.
        if os.path.isfile(file + '.mame'):
            command += (' ' + open(filename + '.mame').read().strip())
            if DEBUG: print 'Read options, command = "%s"' % command

        romname = os.path.basename(file)
        romdir = os.path.dirname(file)
        command = '%s %s' % (command, file)

        self.command = command
	print "Command for MAME : %s" % self.command

        self.game_player = game.get_singleton()
	rominfo = mame_cache.getMameItemInfo(file)
	if rominfo:
	    self.info = { 'description' : '%s - %s - %s' % (rominfo.description,rominfo.manufacturer,rominfo.year) }
	else:
	    self.info = { 'description' : 'No ROM information' }
        

    def sort(self, mode=None):
        """
        Returns the string how to sort this item
        """
        return self.name

    # ------------------------------------------------------------------------
    # actions:


    def actions(self):
        return [ ( self.play, 'Play' ) ]


    def play(self, arg=None, menuw=None):
        self.parent.current_item = self

        if not self.menuw:
            self.menuw = menuw

        if self.menuw.visible:
            self.menuw.hide()

        print "Playing:  %s" % self.filename

        self.game_player.play(self, menuw)


    def stop(self, menuw=None):
        self.game_player.stop()


    def eventhandler(self, event, menuw=None):

        if event == em.STOP:
            self.stop()
            rc.app(None)
            if not menuw == None:
                menuw.refresh(reload=1)

        # give the event to the next eventhandler in the list
        return Item.eventhandler(self, event, menuw)

