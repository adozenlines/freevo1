#if 0 /*
# -----------------------------------------------------------------------
# snesitem.py - Item for snes objects
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.8  2003/05/27 17:53:34  dischi
# Added new event handler module
#
# Revision 1.7  2003/04/24 19:56:13  dischi
# comment cleanup for 1.3.2-pre4
#
# Revision 1.6  2003/04/20 12:43:33  dischi
# make the rc events global in rc.py to avoid get_singleton. There is now
# a function app() to get/set the app. Also the events should be passed to
# the daemon plugins when there is no handler for them before. Please test
# it, especialy the mixer functions.
#
# Revision 1.2  2002/12/22 12:59:34  dischi
# Added function sort() to (audio|video|games|image) item to set the sort
# mode. Default is alphabetical based on the name. For mp3s and images
# it's based on the filename. Sort by date is in the code but deactivated
# (see mediamenu.py how to enable it)
#
# Revision 1.1  2002/12/09 14:23:53  dischi
# Added games patch from Rob Shortt to use the interface.py and snes support
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

import config
import game

# Set to 1 for debug output
DEBUG = config.DEBUG

TRUE  = 1
FALSE = 0

import rc
import time
import copy

from item import Item
import event as em


class SnesItem(Item):
    def __init__(self, file, parent = None):
        Item.__init__(self)
        self.type  = 'snes'            # fix value
        self.mode  = 'file'            # file, dvd or vcd
        self.filename = file

        self.name = os.path.splitext(os.path.basename(file))[0]
        self.xml_file = None
        self.parent = parent
        
        # find image for this file
        if os.path.isfile(os.path.splitext(file)[0] + ".png"):
            self.image = os.path.splitext(file)[0] + ".png"
        elif os.path.isfile(os.path.splitext(file)[0] + ".jpg"):
            self.image = os.path.splitext(file)[0] + ".jpg"

        command = '--prio=%s %s %s' % (config.GAMES_NICE,
                                       config.SNES_CMD,
                                       config.SNES_ARGS_DEF)

        romname = os.path.basename(file)
        romdir = os.path.dirname(file)
        command = '%s "%s"' % (command, file)

        self.command = command

        self.game_player = game.get_singleton()
        

    def sort(self, mode=None):
        """
        Returns the string how to sort this item
        """
        return self.name


    # ------------------------------------------------------------------------
    # actions:


    def actions(self):
        return [ ( self.play, 'Play' ) ]
    

    def play(self, menuw=None):
        self.parent.current_item = self

        if not self.menuw:
            self.menuw = menuw

        if self.menuw.visible:
            self.menuw.hide()

        print "Playing:  %s" % self.filename

        self.game_player.play(self)


    def stop(self, menuw=None):
        self.game_player.stop()


    def eventhandler(self, event, menuw=None, mythread=None):

        if not mythread == None:
            if event == em.STOP:
                self.stop()
                rc.app(None)
                if not menuw == None:
                    menuw.refresh(reload=1)

            elif event == em.MENU:
                mythread.app.write('M')

            elif event == em.GAMES_CONFIG:
                mythread.cmd( 'config' )

            elif event == em.PAUSE or event == em.PLAY:
                mythread.cmd('pause')

            elif event == em.GAMES_RESET:
                mythread.cmd('reset')

            elif event == em.GAMES_SNAPSHOT:
                mythread.cmd('snapshot')

        # give the event to the next eventhandler in the list
        return Item.eventhandler(self, event, menuw)

