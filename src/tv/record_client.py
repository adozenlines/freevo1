# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# record_client.py - A client interface to the Freevo recording server.
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


import sys
import time
import config

import kaa.rpc
import kaa.notifier
import time, sys, socket, traceback, string
import xmlrpclib
import epg_types

from util.marmalade import jellyToXML, unjellyFromXML

TRUE  = 1
FALSE = 0

xml_rpc_server = 'http://%s:%s/' % (config.RECORDSERVER_IP, config.RECORDSERVER_PORT)
server = xmlrpclib.Server(xml_rpc_server, allow_none=1)

class RecordClient:
    """
    recordserver access class using kaa.rpc
    """
    def __init__(self):
        self.socket = (config.RECORDSERVER_IP, config.RECORDSERVER_PORT2)
        self.secret = config.RECORDSERVER_SECRET
        try:
            self.server = kaa.rpc.Client(self.socket, self.secret)
        except kaa.rpc.ConnectError, e:
            print e
            raise

    #@kaa.notifier.execute_in_mainloop()
    def recordserver_rpc(self, cmd, *args, **kwargs):
        print 'RecordClient.recordserver_rpc(cmd=%r, args=%r, kwargs=%r)' % (cmd, args, kwargs)
        return self.server.rpc(cmd, *args, **kwargs)

    def getScheduledRecordings(self):
        """ get the scheduled recordings, returning an in process object """
        print 'RecordClient.getScheduledRecordings()'
        inprogress = self.recordserver_rpc('getScheduledRecordings')
        print 'RecordClient.getScheduledRecordings.inprogress = %r' % (inprogress)
        return inprogress

    # this redefined getScheduledRecordings
    def getScheduledRecordings(self, callback):
        """ get the scheduled recordings, using a callback function """
        print 'RecordClient.getScheduledRecordings(callback=%r)' % (callback)
        res = self.server.rpc('getScheduledRecordings').connect(callback)
        print 'RecordClient.getScheduledRecordings().res = %r' % (res)
        return res


    def findNextProgram(self, callback):
        """ find the next program using a callback function """
        print 'RecordClient.findNextProgram(callback=%r)' % (callback)
        self.server.rpc('findNextProgram').connect(callback)


    def isPlayerRunning(self, callback):
        """ is a player running, using a callback function """
        print 'RecordClient.isPlayerRunning(callback=%r)' % (callback)
        self.server.rpc('isPlayerRunning').connect(callback)
        


def returnFromJelly(status, response):
    if status:
        return (status, unjellyFromXML(response))
    return (status, response)


def getScheduledRecordings():
    try:
        (status, message) = server.getScheduledRecordings()
    except Exception, e:
        _debug_('%s' % e)
        return (FALSE, 'record_client: '+_('connection error'))
    return returnFromJelly(status, message)


def saveScheduledRecordings(scheduledRecordings):
    try:
        (status, message) = server.saveScheduledRecordings(scheduledRecordings)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def connectionTest(teststr='testing'):
    try:
        (status, message) = server.echotest(teststr)
    except Exception, e:
        _debug_('%s' % e)
        traceback.print_exc()
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def scheduleRecording(prog=None):
    if not prog:
        return (FALSE, _('no program'))

    if prog.stop < time.time():
        return (FALSE, _('ERROR')+': '+_('cannot record it if it is over'))

    try:
        (status, message) = server.scheduleRecording(jellyToXML(prog))
    except:
        traceback.print_exc()
        return (FALSE, 'record_client: '+_('connection error'))

    return (status, message)


def removeScheduledRecording(prog=None):
    if not prog:
        return (FLASE, _('no program'))

    try:
        (status, message) = server.removeScheduledRecording(jellyToXML(prog))
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def cleanScheduledRecordings():
    try:
        (status, message) = server.cleanScheduledRecordings()
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def isProgScheduled(prog, schedule=None):
    if schedule or schedule == {}:
        if schedule == {}:
            return (FALSE, _('program not scheduled'))

        for me in schedule.values():
            if me.start == prog.start and me.channel_id == prog.channel_id:
                return (TRUE, _('program is scheduled'))

        return (FALSE, _('program not scheduled'))
    else:
        try:
            (status, message) = server.isProgScheduled(jellyToXML(prog), schedule)
        except:
            return (FALSE, 'record_client: '+_('connection error'))

        return (status, message)


def findProg(chan, start):
    try:
        (status, response) = server.findProg(chan, start)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return returnFromJelly(status, response)


def findMatches(find='', movies_only=0):
    try:
        (status, response) = server.findMatches(find, movies_only)
    except Exception, e:
        _debug_('Search error for \'%s\' %s' % (find, e), DWARNING)
        return (FALSE, 'record_client: '+_('connection error'))
    return returnFromJelly(status, response)


def addFavorite(name, prog, exactchan, exactdow, exacttod):
    try:
        (status, message) = server.addFavorite(name, prog, exactchan, exactdow, exacttod)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def addEditedFavorite(name, title, chan, dow, mod, priority, allowDuplicates, onlyNew):
    try:
        (status, message) = \
            server.addEditedFavorite(jellyToXML(name), \
            jellyToXML(title), chan, dow, mod, priority, allowDuplicates, onlyNew)
    except Exception, e:
        _debug_('%s' % e, DERROR)
        traceback.print_exc()
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def removeFavorite(name):
    try:
        (status, message) = server.removeFavorite(name)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def clearFavorites():
    try:
        (status, message) = server.clearFavorites()
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def getFavorites():
    try:
        (status, response) = server.getFavorites()
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return returnFromJelly(status, response)


def getFavorite(name):
    try:
        (status, response) = server.getFavorite(name)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return returnFromJelly(status, response)


def getFavoriteObject(prog, favs=None):
    try:
        (status, response) = server.getFavoriteObject(jellyToXML(prog), jellyToXML(favs))
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return returnFromJelly(status, response)


def adjustPriority(favname, mod):
    try:
        (status, message) = server.adjustPriority(favname, mod)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def isProgAFavorite(prog, favs=None):
    try:
        (status, message) = server.isProgAFavorite(jellyToXML(prog), jellyToXML(favs))
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def removeFavoriteFromSchedule(fav):
    try:
        (status, message) = server.removeFavoriteFromSchedule(fav)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def addFavoriteToSchedule(fav):
    try:
        (status, message) = server.addFavoriteToSchedule(fav)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def updateFavoritesSchedule():
    try:
        (status, message) = server.updateFavoritesSchedule()
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


if __name__ == '__main__':

    def handler(result):
        print 'result = %r' % (result)
        raise SystemExit

    rc = RecordClient()
    rc.getScheduledRecordings(handler)
    kaa.main()

    if len(sys.argv) >= 2:
        function = sys.argv[1]
    else:
        function = 'none'

    print 'xml_rpc_server at %r' % (xml_rpc_server)

    if function == "updateFavoritesSchedule":
        (result, response) = updateFavoritesSchedule()
        print '%r' % response


    if function == "test":
        (result, response) = connectionTest('connection test')
        print 'result: %s, response: %s ' % (result, response)


    if function == "moviesearch":
        if len(sys.argv) >= 3:
            find = Unicode(sys.argv[2])

            (result, response) = findMatches(find, 0)
            if result:
                for prog in response:
                    _debug_('Prog: %s' % prog.title)
            else:
                _debug_('result: %s, response: %s ' % (result, response))
        else:
            print 'no data'


    if function == "addfavorite":
        if len(sys.argv) >= 3:
            name=Unicode(string.join(sys.argv[2:]))
            title=name
            channel="ANY"
            dow="ANY"
            mod="ANY"
            priority=0
            allowDuplicates=FALSE
            onlyNew=TRUE

            (result, msg) = addEditedFavorite(name,title,channel,dow,mod,priority,allowDuplicates,onlyNew)
            if not result:
                # it is important to show the user this error,
                # because that means the favorite is removed,
                # and must be created again
                _debug_('Save Failed, favorite was lost: %s' % (msg), DWARNING)
            else:
                _debug_('Ok!')
                (result, response) = updateFavoritesSchedule()
                _debug_('%r' % response)
        else:
            print 'no data'
