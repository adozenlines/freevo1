#if 0 /*
# -----------------------------------------------------------------------
# __init__.py - interface between mediamenu and video
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.21  2004/01/03 17:40:27  dischi
# remove update function
#
# Revision 1.20  2003/12/29 22:08:54  dischi
# move to new Item attributes
#
# Revision 1.19  2003/12/09 19:43:01  dischi
# patch from Matthieu Weber
#
# Revision 1.18  2003/12/06 13:44:11  dischi
# move more info to the Mimetype
#
# Revision 1.17  2003/11/30 14:41:10  dischi
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


import os
import copy
import re

import config
import util
import plugin

from videoitem import VideoItem

# variables for the hashing function
fxd_database         = {}
discset_informations = {}
tv_show_informations = {}


class PluginInterface(plugin.MimetypePlugin):
    """
    Plugin to handle all kinds of video items
    """
    def __init__(self):
        plugin.MimetypePlugin.__init__(self)
        self.display_type = [ 'video' ]
        if config.AUDIO_SHOW_VIDEOFILES:
            self.display_type = [ 'video', 'audio' ]

        # load the fxd part of video
        import fxdhandler

        plugin.register_callback('fxditem', ['video'], 'movie', fxdhandler.parse_movie)
        plugin.register_callback('fxditem', ['video'], 'disc-set', fxdhandler.parse_disc_set)

        # activate the mediamenu for video
        plugin.activate('mediamenu', level=plugin.is_active('video')[2], args='video')
        

    def suffix(self):
        """
        return the list of suffixes this class handles
        """
        return config.VIDEO_SUFFIX


    def get(self, parent, files):
        """
        return a list of items based on the files
        """
        items = []

        for file in util.find_matches(files, config.VIDEO_SUFFIX):
            x = VideoItem(file, parent)
            if parent.media:
                file_id = parent.media.id + \
                          file[len(os.path.join(parent.media.mountdir,"")):]
                try:
                    x.mplayer_options = discset_informations[file_id]
                except KeyError:
                    pass
            items += [ x ]
            files.remove(file)

        return items


    def dirinfo(self, diritem):
        """
        set informations for a diritem based on the content, etc.
        """
        global tv_show_informations
        if not diritem.image and config.VIDEO_SHOW_DATA_DIR:
            diritem.image = util.getimage(vfs.join(config.VIDEO_SHOW_DATA_DIR,
                                                   vfs.basename(diritem.dir).lower()))

        if tv_show_informations.has_key(vfs.basename(diritem.dir).lower()):
            tvinfo = tv_show_informations[vfs.basename(diritem.dir).lower()]
            diritem.info = tvinfo[1]
            if not diritem.image:
                diritem.image = tvinfo[0]
            if not diritem.fxd_file:
                diritem.fxd_file = tvinfo[3]


def hash_fxd_movie_database():
    """
    hash fxd movie files in some directories. This is used e.g. by the
    rom drive plugin, but also for a directory and a videoitem.
    """
    import fxditem
    
    global tv_show_informations
    global discset_informations
    global fxd_database

    fxd_database['id']    = {}
    fxd_database['label'] = []
    discset_informations  = {}
    tv_show_informations  = {}
    
    if vfs.exists("/tmp/freevo-rebuild-database"):
        try:
            os.remove('/tmp/freevo-rebuild-database')
        except OSError:
            print '*********************************************************'
            print
            print '*********************************************************'
            print 'ERROR: unable to remove /tmp/freevo-rebuild-database'
            print 'please fix permissions'
            print '*********************************************************'
            print
            return 0

    _debug_("Building the xml hash database...",1)

    files = []
    if not config.VIDEO_ONLY_SCAN_DATADIR:
        for name,dir in config.VIDEO_ITEMS:
            files += util.recursefolders(dir,1,'*.fxd',1)

    for subdir in ('disc', 'disc-set'):
        files += util.recursefolders(vfs.join(config.OVERLAY_DIR, subdir), 1, '*.fxd', 1)

    for info in fxditem.mimetype.parse(None, files, display_type='video'):
        if hasattr(info, '__fxd_rom_info__'):
            for i in info.__fxd_rom_id__:
                fxd_database['id'][i] = info
            for l in info.__fxd_rom_label__:
                fxd_database['label'].append((re.compile(l), info))
            for fo in info.__fxd_files_options__:
                discset_informations[fo['file-id']] = fo['mplayer-options']

    if config.VIDEO_SHOW_DATA_DIR:
        files = util.recursefolders(config.VIDEO_SHOW_DATA_DIR,1, '*.fxd',1)
        for info in fxditem.mimetype.parse(None, files, display_type='video'):
            k = vfs.splitext(vfs.basename(info.fxd_file))[0]
            tv_show_informations[k] = (info.image, info.info, info.mplayer_options,
                                       info.fxd_file)
            if hasattr(info, '__fxd_rom_info__'):
                for fo in info.__fxd_files_options__:
                    discset_informations[fo['file-id']] = fo['mplayer-options']
            
    _debug_('done',1)
    return 1
