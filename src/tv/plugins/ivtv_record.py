
#if 0 /*
# -----------------------------------------------------------------------
# ivtv_record.py - A plugin to record tv using an ivtv based card.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.18  2004/01/09 19:25:21  outlyer
# Since the recordserver has been stable for some time, we can remove some
# of the original DEBUG messages...
#
# Revision 1.17  2003/12/31 16:09:32  rshortt
# Use the VideoGroup for this channel to change to the correct input on the
# v4l device.
#
# Revision 1.16  2003/11/28 19:26:37  dischi
# renamed some config variables
#
# Revision 1.15  2003/11/23 19:55:27  rshortt
# Changes to use src/tv/channels.py and VIDEO_GROUPS.
#
# Revision 1.14  2003/10/15 12:49:53  rshortt
# Patch from Eirik Meland that stops recording when you remove a recording
# program from the recording schedule.  There exists a race condition where
# removing a recording right before it starts recording the entry in the
# schedule will go away but recording will start anyways.  We should figure
# out a good way to eliminate this.
#
# A similar method should be created for the generic_record.py plugin.
#
# Revision 1.13  2003/09/14 03:22:47  outlyer
# Move some output into 'DEBUG:'
#
# Revision 1.12  2003/09/06 15:12:04  rshortt
# recordserver's name changed.
#
# Revision 1.11  2003/09/05 02:48:13  rshortt
# Removing src/tv and src/www from PYTHONPATH in the freevo script.  Therefore any module that was imported from src/tv/ or src/www that didn't have a leading 'tv.' or 'www.' needed it added.  Also moved tv/tv.py to tv/tvmenu.py to avoid namespace conflicts.
#
# Revision 1.10  2003/08/23 12:51:43  dischi
# removed some old CVS log messages
#
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
# ----------------------------------------------------------------------- */
#endif

import sys, string
import random
import time, os
import threading
import signal

import config
import tv.ivtv
import childapp 
import plugin 

from tv.channels import FreevoChannels

DEBUG = config.DEBUG

TRUE = 1
FALSE = 0

CHUNKSIZE = 65536


class PluginInterface(plugin.Plugin):
    def __init__(self):
        plugin.Plugin.__init__(self)

        plugin.register(Recorder(), 'RECORD')


class Recorder:

    def __init__(self):
        # Disable this plugin if not loaded by record_server.
        if string.find(sys.argv[0], 'recordserver') == -1:
            return

        if DEBUG: print 'ACTIVATING IVTV RECORD PLUGIN'

        self.thread = Record_Thread()
        self.thread.setDaemon(1)
        self.thread.mode = 'idle'
        self.thread.start()
        

    def Record(self, rec_prog):

        self.thread.mode = 'record'
        self.thread.prog = rec_prog
        self.thread.mode_flag.set()
        
        if DEBUG: print('Recorder::Record: %s' % rec_prog)
        
        
    def Stop(self):
        self.thread.mode = 'stop'
        self.thread.mode_flag.set()



class Record_Thread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        
        self.mode = 'idle'
        self.mode_flag = threading.Event()
        self.prog  = ''
        self.app = None

    def run(self):
        while 1:
            if DEBUG: print('Record_Thread::run: mode=%s' % self.mode)
            if self.mode == 'idle':
                self.mode_flag.wait()
                self.mode_flag.clear()
                
            elif self.mode == 'record':
                if DEBUG: print 'Record_Thread::run: started recording'

                fc = FreevoChannels()
                if DEBUG: print 'CHAN: %s' % fc.getChannel()

                tv_lock_file = config.FREEVO_CACHEDIR + '/record'
                open(tv_lock_file, 'w').close()

                video_save_file = '%s/%s.mpeg' % (config.TV_RECORD_DIR, 
                                             string.replace(self.prog.filename,
                                                            ' ', '_'))
                
                (v_norm, v_input, v_clist, v_dev) = config.TV_SETTINGS.split()

                v = tv.ivtv.IVTV(v_dev)

                v.init_settings()
                vg = fc.getVideoGroup(self.prog.tunerid)

                if DEBUG: print 'Setting Input to %s' % vg.input_num
                v.setinput(vg.input_num)

                if DEBUG: print 'Setting Channel to %s' % self.prog.tunerid
                fc.chanSet(str(self.prog.tunerid))

                if DEBUG: v.print_settings()

                now = time.time()
                stop = now + self.prog.rec_duration

                time.sleep(2)

                v_in  = open(v_dev, 'r')
                v_out = open(video_save_file, 'w')

                while time.time() < stop:
                    buf = v_in.read(CHUNKSIZE)
                    v_out.write(buf)
                    if self.mode == 'stop':
                        break

                v_in.close()
                v_out.close()
                v.close()
                v = None

                os.remove(tv_lock_file)

                if DEBUG: print('Record_Thread::run: finished recording')

                self.mode = 'idle'
                
            else:
                self.mode = 'idle'
            time.sleep(0.5)


    

