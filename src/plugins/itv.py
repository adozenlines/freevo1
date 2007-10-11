# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# itv.py - a simple plugin to view rss Video
# -----------------------------------------------------------------------
#
# Notes:
# Todo:
# activate:
# plugin.activate('itv', level=45)
# TV_LOCATIONS = [
#       ('JT LCI 18h', 'http://tf1.lci.fr/xml/rss/0,,14,00.xml'),
#       ('JT i>Tele', 'http://podcast12.streamakaci.com/iTELE/iTELElejournal.xml'),
#       ('Flash Equipe', 'http://www.lequipe.fr/Podcast/flashETV_rss.xml'),
#       ('M�t�o LCI', 'http://tf1.fr/xml/rss/0,,23,00.xml'),
#       ('M�t�o France 2', 'file:///home/henri2/.freevo/meteo.xml')]
#
# for a full list of tested sites see Docs/plugins/iTV.txt
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


#python modules
import os, time, stat, re, copy

# rdf modules
from xml.dom.ext.reader import Sax2
import urllib

#freevo modules
import config, menu, rc, plugin, skin, osd, util
from gui.PopupBox import PopupBox
from item import Item
from skin.widgets import ScrollableTextScreen
from video import VideoItem
from event import Event

#get the singletons so we get skin info and access the osd
skin_object = skin.get_singleton()
osd  = osd.get_singleton()

skin_object.register('itv', ('screen', 'title', 'scrollabletext', 'plugin'))

#check every 30 minutes
MAX_HEADLINE_AGE = 1800


class PluginInterface(plugin.MainMenuPlugin):
    """
    A plugin to list Video from an XML (RSS) feed.

    To activate, put the following lines in local_conf.py:

    plugin.activate('itv', level=45)
    ITV_PLAYER = 'mplayer'
    ITV_ARGS = '-nolirc -nojoystick -autoq 100 -screenw 800 -screenh 600 -fs '
    ITV_LOCATIONS = [
        ('JT LCI 18h', 'http://tf1.lci.fr/xml/rss/0,,14,00.xml'),
        ('JT i>Tele', 'http://podcast12.streamakaci.com/iTELE/iTELElejournal.xml'),
        ('Flash Equipe', 'http://www.lequipe.fr/Podcast/flashETV_rss.xml'),
        ('M�t�o LCI', 'http://tf1.fr/xml/rss/0,,23,00.xml'),
        ('M�t�o France 2', 'file:///home/henri2/.freevo/meteo.xml')]

    For a full list of tested sites, see 'Docs/plugins/iTV.txt'.
    """
    # make an init func that creates the cache dir if it don't exist
    def __init__(self):
        if not hasattr(config, 'ITV_LOCATIONS'):
            self.reason = 'ITV_LOCATIONS not defined'
            return
        plugin.MainMenuPlugin.__init__(self)

    def config(self):
        return [
            ('ITV_PLAYER', 'mplayer', 'player for the iTV feed, must support http://'),
            ('ITV_ARGS', '-nolirc -nojoystick -autoq 100 -screenw 800 -screenh 600 -fs ', 'player options'),
            ('ITV_LOCATIONS', [
                ('JT LCI 18h', 'http://tf1.lci.fr/xml/rss/0,,14,00.xml'),
                ('JT i>Tele', 'http://podcast12.streamakaci.com/iTELE/iTELElejournal.xml'),
                ('Flash Equipe', 'http://www.lequipe.fr/Podcast/flashETV_rss.xml'),
                ('M�t�o LCI', 'http://tf1.fr/xml/rss/0,,23,00.xml'),
                ('M�t�o France 2', 'file:///home/henri2/.freevo/meteo.xml')],
            'where to get the news')]

    def items(self, parent):
        return [ HeadlinesMainMenuItem(parent) ]


class HeadlinesSiteItem(Item):
    """
    Item for the menu for one rss feed
    """
    def __init__(self, parent):
        Item.__init__(self, parent)
        self.url = ''
        self.cachedir = '%s/itv' % config.FREEVO_CACHEDIR
        if not os.path.isdir(self.cachedir):
            os.mkdir(self.cachedir,
                     stat.S_IMODE(os.stat(config.FREEVO_CACHEDIR)[stat.ST_MODE]))
        self.location_index = None
        self.player        = ChaineItem(self, "http","file://")

    def eventhandler(self, event, menuw=None):
        """
        eventhandler
        """
        if event in ('USER_END','PLAY_END','STOP'):
            self.player.stop()
            menuw.show()
            return True

        return False

    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ ( self.getheadlines , _('Show Sites Headlines') ) ]
        return items


    def getsiteheadlines(self):
        headlines = []
        pfile = os.path.join(self.cachedir, 'itv-%i' % self.location_index)
        if (os.path.isfile(pfile) == 0 or \
            (abs(time.time() - os.path.getmtime(pfile)) > MAX_HEADLINE_AGE)):
            #print 'Fresh Headlines'
            headlines = self.fetchheadlinesfromurl()
        else:
            #print 'Cache Headlines'
            headlines = util.read_pickle(pfile)
        return headlines


    def fetchheadlinesfromurl(self):
        headlines = []
        # create Reader object
        reader = Sax2.Reader()

        popup = PopupBox(text=_('Fetching headlines...'))
        popup.show()

        # parse the document
        try:
            myfile=urllib.urlopen(self.url)
            doc = reader.fromStream(myfile)
            items = doc.getElementsByTagName('item')
            for item in items:
                title = ''
                link  = ''
                description = ''

                if item.hasChildNodes():
                    for c in item.childNodes:
                        if c.localName == 'title':
                            title = c.firstChild.data
                        if c.localName == 'description':
                            description = c.firstChild.data
                        #################################
                        # Ajout pour identifier le lien de la video
                        if c.localName == 'enclosure':
                            attrs = c.attributes
                            for attrName in attrs.keys():
                                attrNode = attrs.get(attrName)
                                attrValue = attrNode.nodeValue
                                if 'url' in attrName:
                                    link = attrValue

                if title:
                    headlines.append((title, link, description))

        except:
            #unreachable or url error
            _debug_('could not open %s' % self.url, config.DERROR)
            pass

        #write the file
        if len(headlines) > 0:
            pfile = os.path.join(self.cachedir, 'itv-%i' % self.location_index)
            util.save_pickle(headlines, pfile)

        popup.destroy()
        return headlines


    def show_details(self, arg=None, menuw=None):
        self.player.mode = 'http'
        self.player.url = arg.link
        lien = arg.link
        self.player.play(lien, menuw)


    def getheadlines(self, arg=None, menuw=None):
        headlines = []
        rawheadlines = []
        rawheadlines = self.getsiteheadlines()
        for title, link, description in rawheadlines:
            mi = menu.MenuItem('%s' % title, self.show_details, 0)
            mi.arg = mi
            mi.link = link

            description = description.replace('\n\n', '&#xxx;').replace('\n', ' ').\
                          replace('&#xxx;', '\n')
            description = description.replace('<p>', '\n').replace('<br>', '\n')
            description = description.replace('<p>', '\n').replace('<br/>', '\n')
            description = description + '\n \n \nLink: ' + link
            description = util.htmlenties2txt(description)

            mi.description = re.sub('<.*?>', '', description)

            headlines.append(mi)


        if (len(headlines) == 0):
            headlines += [menu.MenuItem(_('No Headlines found'), menuw.goto_prev_page, 0)]

        headlines_menu = menu.Menu(_('Headlines'), headlines)
        rc.app(None)
        menuw.pushmenu(headlines_menu)
        menuw.refresh()


class HeadlinesMainMenuItem(Item):
    """
    this is the item for the main menu and creates the list
    of Headlines Sites in a submenu.
    """
    def __init__(self, parent):
        Item.__init__(self, parent, skin_type='itv')
        self.name = _('Internet TV')

    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ ( self.create_locations_menu , _('Headlines Sites' )) ]
        return items

    def create_locations_menu(self, arg=None, menuw=None):
        headlines_sites = []
        for location in config.ITV_LOCATIONS:
            headlines_site_item = HeadlinesSiteItem(self)
            headlines_site_item.name = location[0]
            headlines_site_item.url = location[1]
            headlines_site_item.location_index = config.ITV_LOCATIONS.index(location)
            headlines_sites += [ headlines_site_item ]
        if (len(headlines_sites) == 0):
            headlines_sites += [menu.MenuItem(_('No Headlines Sites found'),
                                              menuw.goto_prev_page, 0)]
        headlines_site_menu = menu.Menu(_('Headlines Sites'), headlines_sites)
        menuw.pushmenu(headlines_site_menu)
        menuw.refresh()

class ChaineItem(VideoItem):
    """
    Item for the menu for one rss feed
    """
    def __init__(self, parent, flux_name,flux_location):
        VideoItem.__init__(self, flux_location, parent)
        self.network_play = True
        self.parent       = parent
        self.location     = flux_location
        self.name         = '' #parent.name
        self.type = 'video'
        self.force_player = 'mplayer'
