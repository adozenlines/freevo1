#if 0 /*
# -----------------------------------------------------------------------
# interface.py - interface between mediamenu and games
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.4  2003/01/12 13:51:51  dischi
# Added the feature to remove items for videos, too. For that the interface
# was modified (update instead of remove).
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

import config
import util

import mame_cache
from mameitem import MameItem
from snesitem import SnesItem


def cwd(parent, files):
    """
    return a list of items based on the files
    """
    items = []

    mame_files = util.find_matches(files, config.SUFFIX_MAME_FILES)

    # This will only add real mame roms to the cache.
    (rm_files, mame_list) = mame_cache.getMameItemInfoList(mame_files)

    for rm_file in rm_files:
        files.remove(rm_file)

    for ml in mame_list:   
        items += [ MameItem(ml[0], ml[1], ml[2], parent) ]

    for file in util.find_matches(files, config.SUFFIX_SNES_FILES):
        items += [ SnesItem(file, parent) ]
        files.remove(file)


    return items



def update(parent, new_files, del_files, new_items, del_items, current_items):
    """
    update a directory. Add items to del_items if they had to be removed based on
    del_files or add them to new_items based on new_files
    """

    # XXX the remove stuff is missing right now, can someone who knows the mame
    # XXX code please add it?
    
    new_items += cwd(parent, new_files)
