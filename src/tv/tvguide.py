#if 0 /*
# -----------------------------------------------------------------------
# tvguide.py - This is the Freevo TV Guide module. 
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.28  2004/03/08 19:15:14  dischi
# fix popup input focus
#
# Revision 1.27  2004/02/25 17:44:30  dischi
# add special event mapping for tvmenu
#
# Revision 1.26  2004/02/23 21:51:15  dischi
# fix unicode problem
#
# Revision 1.25  2004/02/23 03:54:25  rshortt
# Use ProgramItem and display_program rather than clunky popup-gui.  Because
# of this the tvguide does no longer need to extend GUIObject.  For now it
# needs to extend Item unless we make each program block into a distinctive
# ProgramItem which may unnesseccarily increase overhead.
#
# Revision 1.24  2004/02/16 18:10:54  outlyer
# Patch from James A. Laska to make the TV Guide behave intuitively when
# clicking on a future program. As you would expect, it now pops up the record
# dialog.
#
# Revision 1.23  2004/02/06 20:55:28  dischi
# move debug to 2
#
# Revision 1.22  2004/01/09 02:10:00  rshortt
# Patch from Matthieu Weber to revive add/edit favorites support from the
# TV interface.
#
# Revision 1.21  2003/12/04 21:48:11  dischi
# also add the plugin area
#
# Revision 1.20  2003/12/03 21:51:31  dischi
# register to the skin and rename some skin function calls
#
# Revision 1.19  2003/11/16 17:38:48  dischi
# i18n patch from David Sagnol
#
# Revision 1.18  2003/10/21 15:16:17  outlyer
# A workaround for the problem wherein Twisted Python cannot serialize
# boolean types.
#
# Revision 1.17  2003/10/18 09:34:37  dischi
# show the current recodings in the guide, RECORD toggles record and remove
#
# Revision 1.16  2003/09/13 10:08:23  dischi
# i18n support
#
# Revision 1.15  2003/09/07 15:44:29  dischi
# add em.MENU_CHANGE_STYLE to toggle styles
#
# Revision 1.14  2003/09/05 02:59:09  rshortt
# Merging in the changes from the new_record branch.  The tvguide now uses
# record_client.py to talk to record_server and no longer uses freevo_record.lst
# and record_daemon.py.  I will attic unused files at a later date.
#
# Revision 1.8.2.4  2003/09/05 02:04:26  rshortt
# Some fixes from the head and add the tv namespace.
#
# Revision 1.8.2.3  2003/08/11 19:45:00  rshortt
# Adding changes form the main branch, perparing to merge.
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
import time

import gui.GUIObject
import rc

from gui.PopupBox import PopupBox
from gui.AlertBox import AlertBox

import config, skin
import event as em

# The Electronic Program Guide
import epg_xmltv, epg_types

from item import Item
from program_display import ProgramItem
import record_client as ri

skin = skin.get_singleton()
skin.register('tv', ('screen', 'title', 'subtitle', 'view', 'tvlisting', 'info', 'plugin'))

CHAN_NO_DATA = _('This channel has no data loaded')

class TVGuide(Item):
    def __init__(self, start_time, player, menuw):
        Item.__init__(self)

        self.n_items, hours_per_page = skin.items_per_page(('tv', self))
        stop_time = start_time + hours_per_page * 60 * 60

        guide = epg_xmltv.get_guide(PopupBox(text=_('Preparing the program guide')))
        channels = guide.GetPrograms(start=start_time+1, stop=stop_time-1)
        if not channels:
            AlertBox(text=_('TV Guide is corrupt!')).show()
            return

        selected = None
        for chan in channels:
            if chan.programs:
                selected = chan.programs[0]
                break

        self.col_time = 30 # each col represents 30 minutes 
        self.n_cols  = (stop_time - start_time) / 60 / self.col_time
        self.player = player

        self.type = 'tv'
        self.menuw = menuw
        self.visible = True

        self.update_schedules(force=True)
        
        self.rebuild(start_time, stop_time, guide.chan_list[0].id, selected)
        menuw.pushmenu(self)


    def update_schedules(self, force=False):
        if not force and self.last_update + 60 > time.time():
            return

        _debug_('update schedule')
        self.last_update = time.time()
        self.scheduled_programs = []
        (got_schedule, schedule) = ri.getScheduledRecordings()
        if got_schedule:
            l = schedule.getProgramList()
            for k in l:
                self.scheduled_programs.append(l[k].encode())

        
    def eventhandler(self, event):
        _debug_('TVGUIDE EVENT is %s' % event, 2)

        if event == em.MENU_CHANGE_STYLE:
            if skin.toggle_display_style('tv'):
                start_time    = self.start_time
                stop_time     = self.stop_time
                start_channel = self.start_channel
                selected      = self.selected

                self.n_items, hours_per_page = skin.items_per_page(('tv', self))

                before = -1
                after  = -1
                for c in self.guide.chan_list:
                    if before >= 0 and after == -1:
                        before += 1
                    if after >= 0:
                        after += 1
                    if c.id == start_channel:
                        before = 0
                    if c.id == selected.channel_id:
                        after = 0
                    
                if self.n_items <= before:
                    start_channel = selected.channel_id

                if after < self.n_items:
                    up = min(self.n_items -after, len(self.guide.chan_list)) - 1
                    for i in range(len(self.guide.chan_list) - up):
                        if self.guide.chan_list[i+up].id == start_channel:
                            start_channel = self.guide.chan_list[i].id
                            break
                    
                stop_time = start_time + hours_per_page * 60 * 60

                self.n_cols  = (stop_time - start_time) / 60 / self.col_time
                self.rebuild(start_time, stop_time, start_channel, selected)
                self.menuw.refresh()
            
        if event == em.MENU_UP:
            self.event_UP()
            self.menuw.refresh()

        elif event == em.MENU_DOWN:
            self.event_DOWN()
            self.menuw.refresh()

        elif event == em.MENU_LEFT:
            self.event_LEFT()
            self.menuw.refresh()

        elif event == em.MENU_RIGHT:
            self.event_RIGHT()
            self.menuw.refresh()

        elif event == em.MENU_PAGEUP:
            self.event_PageUp()
            self.menuw.refresh()

        elif event == em.MENU_PAGEDOWN:
            self.event_PageDown()
            self.menuw.refresh()

        elif event == em.MENU_SUBMENU:
            
            pass

        elif event == em.TV_START_RECORDING:
            self.event_RECORD()
            self.menuw.refresh()
 
        elif event == em.MENU_SELECT or event == em.PLAY:
            tvlockfile = config.FREEVO_CACHEDIR + '/record'

            # jlaska -- START
            # Check if the selected program is >7 min in the future
            # if so, bring up the record dialog
            now = time.time() + (7*60)
            if self.selected.start > now:
                self.event_RECORD()
            # jlaska -- END
            elif os.path.exists(tvlockfile):
                # XXX: In the future add the options to watch what we are
                #      recording or cencel it and watch TV.
                AlertBox(text=_('Sorry, you cannot watch TV while recording. ')+ \
                              _('If this is not true then remove ') + \
                              tvlockfile + '.', height=200).show()
                return TRUE
            else:
                self.hide()
                self.player('tv', self.selected.channel_id)
        
        elif event == em.PLAY_END:
            self.show()

        else:
            return FALSE

        return TRUE


    def show(self):
        if not self.visible:
            self.visible = 1
            self.refresh()

            
    def hide(self):
        if self.visible:
            self.visible = 0
            skin.clear()
        

    def refresh(self):
        self.update_schedules(force=True)
        if not self.menuw.children:
            rc.set_context('tvmenu')
            self.menuw.refresh()


    def rebuild(self, start_time, stop_time, start_channel, selected):

        self.guide = epg_xmltv.get_guide()
        channels = self.guide.GetPrograms(start=start_time+1, stop=stop_time-1)

        table = [ ]
        self.update_schedules()

        self.start_time    = start_time
        self.stop_time     = stop_time
        self.start_channel = start_channel
        self.selected      = selected

        self.display_up_arrow   = FALSE
        self.display_down_arrow = FALSE

        # table header
        table += [ ['Chan'] ]
        for i in range(int(self.n_cols)):
            table[0] += [ start_time + self.col_time * i* 60 ]

        table += [ self.selected ] # the selected program

        found_1stchannel = 0
        if stop_time == None:
            found_1stchannel = 1
            
        flag_selected = 0

        n = 0
        for chan in channels:
            if n >= self.n_items:
                self.display_down_arrow = TRUE
                break
            
            if start_channel != None and chan.id == start_channel:
                found_1stchannel = 1            

            if not found_1stchannel:
                self.display_up_arrow = TRUE
                
            if found_1stchannel:
                if not chan.programs:
                    prg = epg_types.TvProgram()
                    prg.channel_id = chan.id
                    prg.start = 0
                    prg.stop = 2147483647   # Year 2038
                    prg.title = CHAN_NO_DATA
                    prg.desc = ''
                    chan.programs = [ prg ]

                    
                for i in range(len(chan.programs)):
                    if selected:
                        if chan.programs[i] == selected:
                            flag_selected = 1
                                
                table += [  chan  ]
                n += 1

        if flag_selected == 0:
            for i in range(2, len(table)):
                if flag_selected == 1:
                    break
                else:
                    if table[i].programs:
                        for j in range(len(table[i].programs)):
                            if table[i].programs[j].stop > start_time:
                                self.selected = table[i].programs[j]
                                table[1] = table[i].programs[j]
                                flag_selected = 1
                                break

        self.table = table
        for t in table:
            try:
                for p in t.programs:
                    if p in self.scheduled_programs:
                        p.scheduled = TRUE # DO NOT change this to 'True' Twisted
                                           # does not support boolean objects and 
                                           # it will break under Python 2.3
                    else:
                        p.scheduled = FALSE # Same as above; leave as 'FALSE' until
                                            # Twisted includes Boolean
            except:
                pass


    def event_RECORD(self):
        if self.selected.scheduled:
            pi = ProgramItem(self, prog=self.selected, context='schedule')
        else:
            pi = ProgramItem(self, prog=self.selected, context='guide')
        pi.display_program(menuw=self.menuw)


    def event_RIGHT(self):
        start_time    = self.start_time
        stop_time     = self.stop_time
        start_channel = self.start_channel
        last_prg      = self.selected

        if last_prg.stop >= stop_time:
            start_time += (self.col_time * 60)
            stop_time += (self.col_time * 60)
            
        channel = self.guide.chan_dict[last_prg.channel_id]
        all_programs = self.guide.GetPrograms(start_time+1, stop_time-1, [ channel.id ])

        # Current channel programs
        programs = all_programs[0].programs
        if programs:
            for i in range(len(programs)):
                if programs[i].title == last_prg.title and \
                   programs[i].start == last_prg.start and \
                   programs[i].stop == last_prg.stop and \
                   programs[i].channel_id == last_prg.channel_id:
                    break

            prg = None
            if i < len(programs) - 1:
                prg = programs[i+1]
            else:
                prg = programs[i]
            if prg.sub_title:
                procdesc = '"' + prg.sub_title + '"\n' + prg.desc
            else:
                procdesc = prg.desc
            to_info = (prg.title, procdesc)
        else:
            prg = epg_types.TvProgram()
            prg.channel_id = channel.id            
            prg.start = 0
            prg.stop = 2147483647   # Year 2038
            prg.title = CHAN_NO_DATA
            prg.desc = ''
            to_info = CHAN_NO_DATA

        self.rebuild(start_time, stop_time, start_channel, prg)


    def event_LEFT(self):
        start_time    = self.start_time
        stop_time     = self.stop_time
        start_channel = self.start_channel
        last_prg      = self.selected

        if last_prg.start <= start_time:
            start_time -= (self.col_time * 60)
            stop_time -= (self.col_time * 60)
            
        channel = self.guide.chan_dict[last_prg.channel_id]
        programs = self.guide.GetPrograms(start_time+1, stop_time-1, [ channel.id ])
        programs = programs[0].programs        
        if programs:
            for i in range(len(programs)):
                if programs[i].title == last_prg.title and \
                   programs[i].start == last_prg.start and \
                   programs[i].stop == last_prg.stop and \
                   programs[i].channel_id == last_prg.channel_id:
                    break

            prg = None
            if i > 0:
                prg = programs[i-1]
            else:
                prg = programs[i]
            if prg.sub_title:
                procdesc = '"' + prg.sub_title + '"\n' + prg.desc
            else:
                procdesc = prg.desc
            to_info = (prg.title, procdesc)
        else:
            prg = epg_types.TvProgram()
            prg.channel_id = channel.id            
            prg.start = 0
            prg.stop = 2147483647   # Year 2038
            prg.title = CHAN_NO_DATA
            prg.desc = ''
            to_info = CHAN_NO_DATA
            
        self.rebuild(start_time, stop_time, start_channel, prg)

        
    def event_DOWN(self):
        start_time    = self.start_time
        stop_time     = self.stop_time
        start_channel = self.start_channel
        last_prg      = self.selected

        n = 1
        flag_start_channel = 0
        for i in range(len(self.guide.chan_list)):
            if self.guide.chan_list[i].id == start_channel:
                flag_start_channel = 1                                        
            if self.guide.chan_list[i].id == last_prg.channel_id:
                break
            if flag_start_channel == 1:
                n += 1

        if n >= self.n_items and (i-self.n_items+2) < len(self.guide.chan_list):
            start_channel = self.guide.chan_list[i-self.n_items+2].id
        else:
            channel = self.guide.chan_list[i]

        channel = None
        if i < len(self.guide.chan_list) - 1:
            channel = self.guide.chan_list[i+1]
        else:
            channel = self.guide.chan_list[i]


        programs = self.guide.GetPrograms(start_time+1, stop_time-1, [ channel.id ])
        programs = programs[0].programs


        prg = None
        if programs and len(programs) > 0:
            for i in range(len(programs)):
                if programs[i].stop > last_prg.start and programs[i].stop > start_time:
                    break

                
            prg = programs[i]
            if prg.sub_title:
                procdesc = '"' + prg.sub_title + '"\n' + prg.desc
            else:
                procdesc = prg.desc
            
            to_info = (prg.title, procdesc)
        else:
            prg = epg_types.TvProgram()
            prg.channel_id = channel.id            
            prg.start = 0
            prg.stop = 2147483647   # Year 2038
            prg.title = CHAN_NO_DATA
            prg.desc = ''
            to_info = CHAN_NO_DATA

        self.rebuild(start_time, stop_time, start_channel, prg)





    def event_UP(self):
        start_time    = self.start_time
        stop_time     = self.stop_time
        start_channel = self.start_channel
        last_prg      = self.selected

        if last_prg == None:
            last_prg = epg_types.TvProgram()

        n = 0
        flag_start_channel = 0
        for i in range(len(self.guide.chan_list)):
            if self.guide.chan_list[i].id == start_channel:
                flag_start_channel = 1
            if self.guide.chan_list[i].id == last_prg.channel_id:
                break
            if flag_start_channel == 1:
                n += 1


        channel = None
        if i > 0:
            channel = self.guide.chan_list[i-1]
            if n == 0:
                start_channel = self.guide.chan_list[i-1].id
                
        else:
            channel = self.guide.chan_list[i]


        programs = self.guide.GetPrograms(start_time+1, stop_time-1, [ channel.id ])
        programs = programs[0].programs

        if programs and len(programs) > 0:
            for i in range(len(programs)):
                if programs[i].stop > last_prg.start and programs[i].stop > start_time:
                    break

            prg = programs[i]
            if prg.sub_title:
                procdesc = '"' + prg.sub_title + '"\n' + prg.desc
            else:
                procdesc = prg.desc
            
            to_info = (prg.title, procdesc)
        else:
            prg = epg_types.TvProgram()
            prg.channel_id = channel.id            
            prg.start = 0
            prg.stop = 2147483647   # Year 2038
            prg.title = _('This channel has no data loaded')
            prg.desc = ''
            to_info = _('This channel has no data loaded')

            
        self.rebuild(start_time, stop_time, start_channel, prg)


    def event_PageUp(self):
        start_time    = self.start_time
        stop_time     = self.stop_time
        start_channel = self.start_channel
        last_prg      = self.selected

        for i in range(len(self.guide.chan_list)):
            if self.guide.chan_list[i].id == last_prg.channel_id:
                break


        channel = None
        if i-self.n_items > 0:
            channel = self.guide.chan_list[i-self.n_items]
            start_channel = self.guide.chan_list[i-self.n_items].id
        else:
            channel = self.guide.chan_list[0]
            start_channel = self.guide.chan_list[0].id


        programs = self.guide.GetPrograms(start_time+1, stop_time-1, [ channel.id ])
        programs = programs[0].programs


        prg = None
        if programs and len(programs) > 0:
            for i in range(len(programs)):
                if programs[i].stop > last_prg.start and programs[i].stop > start_time:
                    break

                
            prg = programs[i]
            if prg.sub_title:
                procdesc = '"' + prg.sub_title + '"\n' + prg.desc
            else:
                procdesc = prg.desc
            
            to_info = (prg.title, procdesc)
        else:
            prg = epg_types.TvProgram()
            prg.channel_id = channel.id            
            prg.start = 0
            prg.stop = 2147483647   # Year 2038
            prg.title = CHAN_NO_DATA
            prg.desc = ''
            to_info = CHAN_NO_DATA

        self.rebuild(start_time, stop_time, start_channel, prg)





    def event_PageDown(self):
        start_time    = self.start_time
        stop_time     = self.stop_time
        start_channel = self.start_channel
        last_prg      = self.selected

        n = 1
        flag_start_channel = 0
        for i in range(len(self.guide.chan_list)):
            if self.guide.chan_list[i].id == start_channel:
                flag_start_channel = 1                                        
            if self.guide.chan_list[i].id == last_prg.channel_id:
                break
            if flag_start_channel == 1:
                n += 1

        channel = None
        if i+self.n_items < len(self.guide.chan_list):
            channel = self.guide.chan_list[i+self.n_items]
            start_channel = self.guide.chan_list[i+self.n_items].id
        else:
            channel = self.guide.chan_list[i]
            start_channel = self.guide.chan_list[i].id


        programs = self.guide.GetPrograms(start_time+1, stop_time-1, [ channel.id ])
        programs = programs[0].programs

        prg = None
        if programs and len(programs) > 0:
            for i in range(len(programs)):
                if programs[i].stop > last_prg.start and programs[i].stop > start_time:
                    break

            prg = programs[i]
            if prg.sub_title:
                procdesc = '"' + prg.sub_title + '"\n' + prg.desc
            else:
                procdesc = prg.desc
            
            to_info = (prg.title, procdesc)

        else:
            prg = epg_types.TvProgram()
            prg.channel_id = channel.id            
            prg.start = 0
            prg.stop = 2147483647   # Year 2038
            prg.title = CHAN_NO_DATA
            prg.desc = ''
            to_info = CHAN_NO_DATA

        self.rebuild(start_time, stop_time, start_channel, prg)
