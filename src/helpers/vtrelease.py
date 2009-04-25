#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Release the ttys after pygame crash
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# Todo:
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
import sys
from fcntl import ioctl
from optparse import IndentedHelpFormatter, OptionParser

def parse_options():
    """
    Parse command line options
    """
    import version
    formatter = IndentedHelpFormatter(indent_increment=2, max_help_position=32, width=100, short_first=0)
    parser = OptionParser(conflict_handler='resolve', formatter=formatter, usage="freevo %prog [options]",
        version='%prog ' + str(version._version))
    parser.prog = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    parser.description = "release the vt in case freevo crashed and still locks the framebuffer"

    opts, args = parser.parse_args()
    return opts, args


opts, args = parse_options()

for i in range(1,7):
    try:
        tty_device = '/dev/tty%s' % i
        fd = os.open(tty_device, os.O_RDONLY | os.O_NONBLOCK)
        # set ioctl (tty, KDSETMODE, KD_TEXT)
        ioctl(fd, 0x4B3A, 0)
        os.close(fd)
    except:
        pass
