#if 0 /*
# -----------------------------------------------------------------------
# record_types.py - Some classes that are important to recording.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.11  2004/02/22 06:23:51  gsbarbieri
# Unicode support: name could be an unicode object and unicode doesn't provide
# translate() method.
#
# Revision 1.10  2004/01/09 19:43:56  outlyer
# Was that \x0 supposed to be there? If so, sorry. I didn't think it was
# supposed to be there and it was causing warnings in the recordserver
# and the OSD interface.
#
# Revision 1.9  2004/01/09 19:39:31  outlyer
# Oops, we don't use config here.
#
# Revision 1.8  2004/01/09 19:35:49  outlyer
# Inherit DEBUG parameter from config, move some prints into DEBUG
#
# Revision 1.7  2004/01/09 02:10:00  rshortt
# Patch from Matthieu Weber to revive add/edit favorites support from the
# TV interface.
#
# Revision 1.6  2003/10/20 01:41:55  rshortt
# Moving tv_util from src/tv/ to src/util/.
#
# Revision 1.5  2003/09/05 02:48:12  rshortt
# Removing src/tv and src/www from PYTHONPATH in the freevo script.  Therefore any module that was imported from src/tv/ or src/www that didn't have a leading 'tv.' or 'www.' needed it added.  Also moved tv/tv.py to tv/tvmenu.py to avoid namespace conflicts.
#
# Revision 1.4  2003/08/23 12:51:43  dischi
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
#endif

import sys, time, os, string
import util.tv_util as tv_util

# The file format version number. It must be updated when incompatible
# changes are made to the file format.
TYPES_VERSION = 2

# Set to 1 for debug output
DEBUG = 0

TRUE = 1
FALSE = 0


class ScheduledRecordings:
 

    def __init__(self):
        self.programList = {}
	self.favorites = {}
        self.TYPES_VERSION = TYPES_VERSION
        

    def addProgram(self, prog, key=None):
        if not key:
            # key = rec_interface.getKey(prog)
            pass

        if DEBUG: print 'addProgram: key is "%s"' % key
        if not self.programList.has_key(key):
            if DEBUG: print 'addProgram: actually adding "%s"' % prog
            self.programList[key] = prog
        else:
            if DEBUG: print 'We already know about this recording.'
        if DEBUG: print 'addProgram: len is "%s"' % len(self.programList)


    def removeProgram(self, prog, key=None):
        if not key:
            # key = rec_interface.getKey(prog)
            pass

        if self.programList.has_key(key):
            del self.programList[key]
            if DEBUG: print 'removed recording: %s' % prog
        else:
            if DEBUG: print 'We do not know about this recording.'


    def getProgramList(self):
        return self.programList


    def setProgramList(self, pl):
        self.programList = pl


    def addFavorite(self, fav):
        if not self.favorites.has_key(fav.name):
            if DEBUG: print 'addFavorites: actually adding "%s"' % fav.name
            self.favorites[fav.name] = fav
        else:
            if DEBUG: print 'We already have a favorite called "%s".' % fav.name


    def removeFavorite(self, name):
        if self.favorites.has_key(name):
            del self.favorites[name]
            if DEBUG: print 'removed favorite: %s' % name
        else:
            if DEBUG: print 'We do not have a favorite called "%s".' % name


    def getFavorites(self):
        return self.favorites


    def setFavorites(self, favs):
        self.favorites = favs


    def setFavoritesList(self, favs):
        newfavs = {}

        for fav in favs:
            if not newfavs.has_key(fav.name):
                newfavs[fav.name] = fav

        self.setFavorites(newfavs)


    def clearFavorites(self):
        self.favorites = {}


class Favorite:


    def __init__(self, name=None, prog=None, exactchan=FALSE, exactdow=FALSE, 
                 exacttod=FALSE, priority=0):
        self.TYPES_VERSION = TYPES_VERSION
        translation_table = \
                            '                ' \
                            + '                ' \
                            + ' !"#$%&' + "'" + '()*+,-./' \
                            + '0123456789:;<=>?' \
                            + '@ABCDEFGHIJKLMNO' \
                            + 'PQRSTUVWXYZ[\]^_' \
                            + '`abcdefghijklmno' \
                            + 'pqrstuvwxyz{|}~ ' \
                            + '                ' \
                            + '                ' \
                            + '                ' \
                            + '                ' \
                            + 'AAAAAAACEEEEIIII' \
                            + 'DNOOOOOxOUUUUYPS' \
                            + 'aaaaaaaceeeeiiii' \
                            + 'dnooooo/ouuuuypy'

        self.name = name
        if name:
            self.name = string.translate(name,translation_table)
        self.priority = priority

        if prog:
            self.title = prog.title

	    if exactchan:
                self.channel = tv_util.get_chan_displayname(prog.channel_id)
            else:
                self.channel = 'ANY'
          
	    if exactdow:
	        lt = time.localtime(prog.start)
                self.dow = lt[6]
            else:
                self.dow = 'ANY'
          
	    if exacttod:
	        lt = time.localtime(prog.start)
                self.mod = (lt[3]*60)+lt[4]
            else:
                self.mod = 'ANY'

        else:
            self.title = 'NONE'
            self.channel = 'NONE'
            self.dow = 'NONE'
            self.mod = 'NONE'


class ScheduledTvProgram:

    LOW_QUALTY  = 1
    MED_QUALTY  = 2
    HIGH_QUALTY = 3

    def __init__(self):
        self.tunerid      = None
        self.isRecording  = FALSE
        self.isFavorite   = FALSE
        self.favoriteName = None
        self.removed      = FALSE
        self.quality      = self.HIGH_QUALITY


