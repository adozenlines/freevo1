# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# idlebar/MultiMail - IdleBar plugins for checking email accounts
# -----------------------------------------------------------------------
# $Id$
#
# Author : Chris Griffiths (freevo@y-fronts.com)
# Date   : Nov 8th 2003
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
# -----------------------------------------------------------------------

import os
import config
import imaplib
import poplib
import mailbox
import threading
import time

from plugins.idlebar import IdleBarPlugin


class MultiMail(IdleBarPlugin):
    """
    Displays an icon in the idlebar representing the number of emails for a specified account. In the case of IMAP, it only lists unread messages

    Activate with:
    plugin.activate('idlebar.MultiMail.Imap',    level=10, args=('username', 'password', 'host', 'port', 'folder')) (port and folder are optional)
    plugin.activate('idlebar.MultiMail.Pop3',    level=10, args=('username', 'password', 'host', 'port')) (port is optional)
    plugin.activate('idlebar.MultiMail.Mbox',    level=10, args=('path to mailbox file')
    plugin.activate('idlebar.MultiMail.Maildir', level=10, args=('path to maildir')

    """
    def __init__(self):
        IdleBarPlugin.__init__(self)
        self.NO_MAILIMAGE = os.path.join(config.ICON_DIR, 'status/newmail_dimmed.png')
        self.MAILIMAGE = os.path.join(config.ICON_DIR, 'status/newmail_active_small.png')
        self.FREQUENCY = 20 # seconds between checks
        self.unread = 0
        self.bg_thread = threading.Thread(target=self._bg_function, name='MultiMail Thread')
        self.bg_thread.setDaemon(1)
        self.bg_thread.start() # Run self._bg_function() in a separate thread

    def _bg_function(self):
        while 1:
            self.unread = self.checkmail()
            time.sleep(self.FREQUENCY)

    def checkmail(self):
        return 0

    def draw(self, (type, object), x, osd):
        if self.unread > 0:
            image_width = osd.draw_image(self.MAILIMAGE, (x, osd.y + 2, -1, -1))[0]
            font  = osd.get_font(config.OSD_IDLEBAR_FONT)
            unread_str = '%3s' % self.unread
            text_width = font.stringsize(unread_str)
            osd.write_text(unread_str, font, None, x, osd.y + 55 - font.h, text_width, font.h, 'left', 'top')
            display_width = max(image_width, text_width)
        else:
            display_width = osd.draw_image(self.NO_MAILIMAGE, (x, osd.y + 10, -1, -1))[0]
        return display_width

class Imap(MultiMail):
    def __init__(self, username, password, host, port=143, folder="INBOX"):
        self.USERNAME = username
        self.PASSWORD = password
        self.HOST = host
        self.PORT = port
        self.FOLDER = folder
        MultiMail.__init__(self)

    def checkmail(self):
        try:
            imap = imaplib.IMAP4(self.HOST)
            imap.login(self.USERNAME,self.PASSWORD)
            imap.select(self.FOLDER)
            unread = len(imap.search(None,"(UNSEEN)")[1][0].split())
            imap.logout
            return unread
        except:
            _debug_('IMAP exception')
            return 0

class Pop3(MultiMail):
    def __init__(self, username, password, host, port=110):
        self.USERNAME = username
        self.PASSWORD = password
        self.HOST = host
        self.PORT = port
        MultiMail.__init__(self)

    def checkmail(self):
        try:
            pop = poplib.POP3(self.HOST, self.PORT)
            pop.user(self.USERNAME)
            pop.pass_(self.PASSWORD)
            unread = len(pop.list()[1])
            pop.quit
            return unread
        except:
            _debug_('Error loading POP account')
            return 0

class Mbox(MultiMail):
    def __init__(self, mailbox):
        self.MAILBOX = mailbox
        MultiMail.__init__(self)

    def checkmail(self):
        if os.path.isfile(self.MAILBOX):
            mb = mailbox.UnixMailbox (file(self.MAILBOX,'r'))
            msg = mb.next()
            count = 0
            while msg is not None:
                count = count + 1
                msg = mb.next()
            return count
        else:
            return 0


class Maildir(MultiMail):
    def __init__(self, mailbox):
        self.MAILBOX = mailbox
        MultiMail.__init__(self)

    def checkmail(self):
        if os.path.isdir(self.MAILBOX):
            md = mailbox.Maildir(self.MAILBOX)
            msg = md.next()
            #count the new emails
            count = 0
            while msg is not None:
                #new emails don't have any tags to them, and filename ends in ,
                if msg.fp.name[-1] == ',':
                    count = count + 1
                msg = md.next()
            return count
        else:
            _debug_('Could not open maildir: %s, check settings.' % self.MAILBOX)
            return 0
