# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# view_favorites.py - A plugin to view your list of favorites.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2003 Krister Lagerstrom, et al.
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
# -----------------------------------------------------------------------


import os
import config, plugin, menu, rc
from tv.record_client import RecordClient

from item import Item
from tv.favoriteitem import FavoriteItem
from gui.AlertBox import AlertBox


class ViewFavoritesItem(Item):
    def __init__(self, parent):
        _debug_('ViewFavoritesItem.__init__(parent=%r)' % (parent,), 2)
        Item.__init__(self, parent, skin_type='tv')
        self.name = _('View Favorites')
        self.menuw = None
        self.recordclient = RecordClient()


    def actions(self):
        _debug_('actions()', 2)
        return [ ( self.view_favorites , _('View Favorites') ) ]


    def view_favorites(self, arg=None, menuw=None):
        _debug_('view_favorites(arg=%r, menuw=%r)' % (arg, menuw), 2)
        items = self.get_items()
        if not len(items):
            AlertBox(_('No favorites.')).show()
            return

        favorite_menu = menu.Menu(_( 'View Favorites'), items, reload_func=self.reload, item_types='tv favorite menu')
        self.menuw = menuw
        rc.app(None)
        menuw.pushmenu(favorite_menu)
        menuw.refresh()


    def reload(self):
        _debug_('reload()', 2)
        menuw = self.menuw

        menu = menuw.menustack[-1]

        new_choices = self.get_items()
        if not menu.selected in new_choices and len(new_choices):
            sel = menu.choices.index(menu.selected)
            if len(new_choices) <= sel:
                menu.selected = new_choices[-1]
            else:
                menu.selected = new_choices[sel]

        menu.choices = new_choices

        return menu


    def get_items(self):
        _debug_('get_items()', 2)
        items = []

        #(server_available, msg) = self.recordclient.connectionTest()
        #if not server_available:
        #    AlertBox(_('Recording server is unavailable.')+(': %s' % msg)).show()
        #    return []

        (result, favorites) = self.recordclient.getFavoritesNow()
        if result:
            f = lambda a, b: cmp(a.priority, b.priority)
            favorites = favorites.values()
            favorites.sort(f)
            for fav in favorites:
                items.append(FavoriteItem(self, fav))
        else:
            AlertBox(_('Get favorites failed')+(': %s' % favorites)).show()
            return []

        return items



class PluginInterface(plugin.MainMenuPlugin):
    """
    This plugin is used to display your list of favorites.

    | plugin.activate('tv.view_favorites')
    """

    def __init__(self):
        _debug_('PluginInterface.__init__()', 2)
        plugin.MainMenuPlugin.__init__(self)

    def items(self, parent):
        _debug_('items(parent=%r)' % (parent,), 2)
        return [ ViewFavoritesItem(parent) ]
