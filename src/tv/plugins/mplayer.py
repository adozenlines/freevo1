# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# mplayer.py - implementation of a TV function using MPlayer
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
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


# Configuration file. Determines where to look for AVI/MP3 files, etc
import config

import time, os

import util    # Various utilities
import osd     # The OSD class, used to communicate with the OSD daemon
import rc      # The RemoteControl class.
import event as em
import childapp # Handle child applications
import tv.epg_xmltv as epg # The Electronic Program Guide
from tv.channels import FreevoChannels
import tv.ivtv as ivtv
import plugin

DEBUG = config.DEBUG

TRUE = 1
FALSE = 0


# Create the OSD object
osd = osd.get_singleton()

class PluginInterface(plugin.Plugin):
    """
    Plugin to watch tv with mplayer.
    """
    def __init__(self):
        plugin.Plugin.__init__(self)

        # create the mplayer object and register it
        plugin.register(MPlayer(), plugin.TV)


class MPlayer:

    __muted    = 0
    __igainvol = 0

    def __init__(self):
        self.tuner_chidx = 0    # Current channel, index into config.TV_CHANNELS
        self.app_mode = 'tv'
        self.fc = FreevoChannels()
        self.current_vg = None


    def Play(self, mode, tuner_channel=None):

        if not tuner_channel:
            tuner_channel = self.fc.getChannel()

        vg = self.current_vg = self.fc.getVideoGroup(tuner_channel, True)

        # Convert to MPlayer TV setting strings
        norm = 'norm=%s' % vg.tuner_norm
        input = 'input=%s' % vg.input_num
        device= 'device=%s' % vg.vdev

        w, h = config.TV_VIEW_SIZE
        outfmt = 'outfmt=%s' % config.TV_VIEW_OUTFMT

        # Build the MPlayer command
        args = (config.MPLAYER_NICE, config.MPLAYER_CMD, config.MPLAYER_VO_DEV,
                config.MPLAYER_VO_DEV_OPTS, config.MPLAYER_AO_DEV, config.MPLAYER_ARGS_DEF)

        if mode == 'tv':
            if vg.group_type == 'ivtv':
                ivtv_dev = ivtv.IVTV(vg.vdev)
                ivtv_dev.init_settings()
                ivtv_dev.setinput(vg.input_num)
                cur_std = ivtv_dev.getstd()
                import tv.v4l2
                try:
                    new_std = tv.v4l2.NORMS.get(vg.tuner_norm)
                    if cur_std != new_std:
                        ivtv_dev.setstd(new_std)
                except:
                    print "Error! Videogroup norm value '%s' not from NORMS: %s" \
                        % (vg.tuner_norm,tv.v4l2.NORMS.keys())
                #ivtv_dev.print_settings()
                ivtv_dev.close()
                self.fc.chanSet(tuner_channel, True)

                tvcmd = vg.vdev

                if config.MPLAYER_ARGS.has_key('ivtv'):
                    args += (config.MPLAYER_ARGS['ivtv'],)

            elif vg.group_type == 'webcam':
                self.fc.chanSet(tuner_channel, True, app='mplayer')
                tvcmd = ''

                if config.MPLAYER_ARGS.has_key('webcam'):
                    args += (config.MPLAYER_ARGS['webcam'],)

            elif vg.group_type == 'dvb':
                self.fc.chanSet(tuner_channel, True, app='mplayer')
                tvcmd = ''
                args += ('"dvb://%s" %s' % (tuner_channel, config.MPLAYER_ARGS['dvb']),)

            elif vg.group_type == 'tvalsa':
                freq_khz = self.fc.chanSet(tuner_channel, True, app='mplayer')
                tuner_freq = '%1.3f' % (freq_khz / 1000.0)

                tvcmd = ('tv:// -tv driver=%s:%s:freq=%s:%s:%s:'
                         '%s:width=%s:height=%s:%s %s' %
                         (config.TV_DRIVER, vg.adev, tuner_freq, device, input, norm,
                          w, h, outfmt, config.TV_OPTS))

                if config.MPLAYER_ARGS.has_key('tv'):
                    args += (config.MPLAYER_ARGS['tv'],)

            else: # group_type == 'normal'
                freq_khz = self.fc.chanSet(tuner_channel, True, app='mplayer')
                tuner_freq = '%1.3f' % (freq_khz / 1000.0)

                tvcmd = ('tv:// -tv driver=%s:freq=%s:%s:%s:'
                         '%s:width=%s:height=%s:%s %s' %
                         (config.TV_DRIVER, tuner_freq, device, input, norm,
                          w, h, outfmt, config.TV_OPTS))

                if config.MPLAYER_ARGS.has_key('tv'):
                    args += (config.MPLAYER_ARGS['tv'],)

        elif mode == 'vcr':
            tvcmd = ('tv:// -tv driver=%s:%s:%s:'
                     '%s:width=%s:height=%s:%s %s' %
                     (config.TV_DRIVER, device, input, norm,
                      w, h, outfmt, config.TV_OPTS))

            if config.MPLAYER_ARGS.has_key('tv'):
                args += (config.MPLAYER_ARGS['tv'],)

        else:
            print 'Mode "%s" is not implemented' % mode  # XXX ui.message()
            return

        args += (tvcmd,)

        mpl = '--prio=%s %s -vo %s %s -ao %s %s -slave %s %s' % args

        command = mpl
        _debug_('command=\"%s\"', ' '.join(command))
        self.mode = mode


        # XXX Mixer manipulation code.
        # TV is on line in
        # VCR is mic in
        # btaudio (different dsp device) will be added later
        mixer = plugin.getbyname('MIXER')

        if mixer and config.MAJOR_AUDIO_CTRL == 'VOL':
            mixer_vol = mixer.getMainVolume()
            mixer.setMainVolume(0)
        elif mixer and config.MAJOR_AUDIO_CTRL == 'PCM':
            mixer_vol = mixer.getPcmVolume()
            mixer.setPcmVolume(0)

        # Start up the TV task
        self.app = childapp.ChildApp2(command)

        self.prev_app = rc.app()
        rc.app(self)

        if osd.focused_app():
            osd.focused_app().hide()

        # Suppress annoying audio clicks
        time.sleep(0.4)
        # XXX Hm.. This is hardcoded and very unflexible.
        if mixer and mode == 'vcr':
            mixer.setMicVolume(config.VCR_IN_VOLUME)
        elif mixer:
            mixer.setLineinVolume(config.TV_IN_VOLUME)
            mixer.setIgainVolume(config.TV_IN_VOLUME)

        if mixer and config.MAJOR_AUDIO_CTRL == 'VOL':
            mixer.setMainVolume(mixer_vol)
        elif mixer and config.MAJOR_AUDIO_CTRL == 'PCM':
            mixer.setPcmVolume(mixer_vol)

        if DEBUG: print '%s: started %s app' % (time.time(), self.mode)



    def Stop(self, channel_change=0):
        mixer = plugin.getbyname('MIXER')
        if mixer and not channel_change:
            mixer.setLineinVolume(0)
            mixer.setMicVolume(0)
            mixer.setIgainVolume(0) # Input on emu10k cards.

        self.app.stop('quit\n')

        rc.app(self.prev_app)
        if osd.focused_app() and not channel_change:
            osd.focused_app().show()

        if os.path.exists('/tmp/freevo.wid'): os.unlink('/tmp/freevo.wid')

        if config.MPLAYER_OLDTVCHANNELCHANGE:
            lastchanfile = os.path.join(config.FREEVO_CACHEDIR, 'lastchan')
            lcfp = open(lastchanfile, "w")
            lastchan = self.fc.getChannel()
            lastchannum = self.fc.getChannelNum()
            lcfp.write(str(lastchan))
            lcfp.write('\n')
            lcfp.write(str(lastchannum))
            lcfp.write('\n')
            lcfp.close()

    def eventhandler(self, event, menuw=None):
        s_event = '%s' % event

        if event == em.STOP or event == em.PLAY_END:
            self.Stop()
            rc.post_event(em.PLAY_END)
            return TRUE

        elif event == em.PAUSE or event == em.PLAY:
            self.app.write('pause\n')
            if DEBUG: print '%s: sending pause to mplayer' % (time.time())
            return TRUE

        elif event in [ em.TV_CHANNEL_UP, em.TV_CHANNEL_DOWN, em.TV_CHANNEL_LAST ] or s_event.startswith('INPUT_'):
            chan = None
            if event == em.TV_CHANNEL_UP:
                nextchan = self.fc.getNextChannel()
                nextchannum = self.fc.getNextChannelNum()
            elif event == em.TV_CHANNEL_DOWN:
                nextchan = self.fc.getPrevChannel()
                nextchannum = self.fc.getPrevChannelNum()
            elif event == em.TV_CHANNEL_LAST:
                if config.MPLAYER_OLDTVCHANNELCHANGE:
                    if os.path.isfile(os.path.join(config.FREEVO_CACHEDIR, 'lastchan')):
                        lastchanfile = os.path.join(config.FREEVO_CACHEDIR, 'lastchan')
                        lcfp = open(lastchanfile, "r")
                        nextchan = lcfp.readline()
                        nextchan = nextchan.strip()
                        nextchannum = lcfp.readline()
                        nextchannum = nextchannum.strip()
                        nextchannum = int(nextchannum)
                        lcfp.close()
                    else:
                        nextchan = self.fc.getChannel()
                        nextchannum = self.fc.getChannelNum()
                else:
                    return TRUE
            else:
                chan = int( s_event[6] )
                nextchan = self.fc.getManChannel(chan)
                nextchannum = self.fc.getManChannelNum(chan)

            nextvg = self.fc.getVideoGroup(nextchan, True)
            _debug_('chan=%s, nextchannum=%s, nextchan=%s nextvg=%s' % (chan, nextchannum, nextchan, nextvg))

            if self.current_vg != nextvg:
                self.Stop(channel_change=1)
                self.Play('tv', nextchan)
                return TRUE

            if self.mode == 'vcr':
                return

            elif self.current_vg.group_type == 'dvb':
                if not config.MPLAYER_OLDTVCHANNELCHANGE:
                    card = 0 # May be this should come from video groups or TV_CHANNELS
                    if em.TV_CHANNEL_UP:
                        self.app.write('dvb_set_channel %s %s\n' % (nextchannum, card))
                    elif em.TV_CHANNEL_DOWN:
                        self.app.write('dvb_set_channel %s %s\n' % (nextchannum, card))
                else:
                    self.Stop(channel_change=1)
                    self.Play('tv', nextchan)
                return TRUE

            elif self.current_vg.group_type == 'ivtv':
                self.fc.chanSet(nextchan, True)
                self.app.write('seek 999999 0\n')

            else:
                freq_khz = self.fc.chanSet(nextchan, True, app=self.app)
                new_freq = '%1.3f' % (freq_khz / 1000.0)
                self.app.write('tv_set_freq %s\n' % new_freq)

            self.current_vg = self.fc.getVideoGroup(self.fc.getChannel(), True)

            # Display a channel changed message
            tuner_id, chan_name, prog_info = self.fc.getChannelInfo()
            now = time.strftime(config.TV_TIMEFORMAT)
            msg = '%s %s (%s): %s' % (now, chan_name, tuner_id, prog_info)
            cmd = 'osd_show_text "%s"\n' % msg
            self.app.write(cmd)
            return TRUE

        elif event == em.TOGGLE_OSD:
            # Display the channel info message
            tuner_id, chan_name, prog_info = self.fc.getChannelInfo()
            now = time.strftime(config.TV_TIMEFORMAT)
            msg = '%s %s (%s): %s' % (now, chan_name, tuner_id, prog_info)
            cmd = 'osd_show_text "%s"\n' % msg
            self.app.write(cmd)
            return FALSE

        return FALSE
