#if 0 /*
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# util/distutils.py - Freevo distutils for installing plugins
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#  If you want to create a package with a plugin, you have to rebuild
#  the freevo directory structure. E.g. if you have a video plugin and
#  an image for it, you should have the following structure:
#
#  root
#    |--> setup.py
#    |
#    |--> share
#    | |--> images
#    | | |--> file.jpg
#    |
#    |--> src
#    | |--> video
#    | | |--> plugins
#    | | | |--> __init__.py (empty)
#    | | | |--> plugin.py
#
#
#  The setup.py file should look like this:
#
#  |   #!/usr/bin/env python
#  |   
#  |   """Setup script for my freevo plugin."""
#  |   
#  |   
#  |   __revision__ = "$Id$"
#  |   
#  |   from distutils.core import setup, Extension
#  |   import distutils.command.install
#  |   import freevo.util.distutils
#  |   
#  |   # now start the python magic
#  |   setup (name = "My first plugin",
#  |          version = 0.1,
#  |          description = "Yes, my first plugin",
#  |          author = "me",
#  |          author_email = "my@mail.address",
#  |          url = "http://i-also-have-web.address",
#  |   
#  |          package_dir = freevo.util.distutils.package_dir,
#  |          packages = freevo.util.distutils.packages,
#  |          data_files = freevo.util.distutils.data_files
#  |          )
#
#
#  If you need help, please join the freevo developer mailing list
#
#
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.1  2003/10/18 13:04:42  dischi
# add distutils
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

import os
import sys

try:
    import version
except:
    import freevo.version as version
    
def package_finder(result, dirname, names):
    for name in names:
        if os.path.splitext(name)[1] == '.py':
            import_name = dirname.replace('/','.').replace('..src', 'freevo')
            result[import_name] = dirname
            return result
    return result


def data_finder(result, dirname, names):
    files = []
    for name in names:
        if os.path.isfile(os.path.join(dirname, name)):
            if name != 'freevo.pot':
                files.append(os.path.join(dirname, name))
            
    if files and dirname.find('/CVS') == -1:
        result.append((dirname.replace('./share', 'share/freevo').
                       replace('./src/www', 'share/freevo').\
                       replace('./i18n', 'share/locale').\
                       replace('./contrib', 'share/freevo/contrib').\
                       replace('./Docs', 'share/doc/freevo-%s' % version.__version__).\
                       replace('./helpers', 'share/freevo/helpers'), files))
    return result


def check_libs(libs):
    # ok, this can't be done by setup it seems, so we have to do it
    # manually
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'install':
        # check for needed libs
        for module, url in libs:
            print 'checking for %-13s' % (module+'...'),
            try:
                exec('import %s' % module)
                print 'found'
            except:
                print 'not found'
                print 'please download it from %s and install it' % url
                sys.exit(1)
            

    
# create list of source files
package_dir = {}

os.path.walk('./src', package_finder, package_dir)
packages = []
for p in package_dir:
    packages.append(p)

# create list of data files (share)
data_files = []
os.path.walk('./share', data_finder, data_files)
os.path.walk('./contrib/fbcon', data_finder, data_files)
os.path.walk('./contrib/xmltv', data_finder, data_files)
os.path.walk('./src/www/htdocs', data_finder, data_files)
os.path.walk('./i18n', data_finder, data_files)
os.path.walk('./Docs/howto', data_finder, data_files)

