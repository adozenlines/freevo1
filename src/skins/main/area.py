#if 0
# -----------------------------------------------------------------------
# area.py - An area for the Freevo skin
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
#
# This is the main class for all area.
#
# If you want to create a new Skin_Area, please keep my problems in mind:
#
#
# 1. Not all areas are visible at the same time, some areas may change
#    the settings and others don't
# 2. The listing and the view area can overlap, at the next item the image
#    may be gone
# 3. alpha layers are slow to blit on a non alpha surface.
# 4. the blue_round1 draws two alpha masks, one for the listing, one
#    for the view area. They overlap, but the overlapping area
#    shouldn't be an addition of the transparent value
# 5. If you drop an alpha layer on the screen, you can't get the original
#    background back by making a reverse alpha layer.
#
# For more informations contact me (dmeyer@tzi.de)
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.24  2004/01/01 16:03:53  dischi
# use vfs.open because it creates the needed dirs
#
# Revision 1.23  2004/01/01 12:25:48  dischi
# use pickle to cache the large background images
#
# Revision 1.22  2003/12/14 17:39:52  dischi
# Change TRUE and FALSE to True and False; vfs fixes
#
# Revision 1.21  2003/12/14 17:04:40  dischi
# move SkinObjects to screen.py
#
# Revision 1.20  2003/12/06 13:43:02  dischi
# more cleanup
#
# Revision 1.19  2003/12/05 18:07:55  dischi
# renaming of XML_xxx variables to Xxx
#
# Revision 1.18  2003/12/05 17:30:17  dischi
# some cleanup
#
# Revision 1.17  2003/12/04 21:49:18  dischi
# o remove BlankScreen and the Splashscreen
# o make it possible to register objects as areas
#
# Revision 1.16  2003/12/03 21:50:44  dischi
# rework of the loading/selecting
# o all objects that need a skin need to register what they areas they need
# o remove all 'player' and 'tv' stuff to make it more generic
# o renamed some skin function names
#
# Revision 1.15  2003/11/29 11:27:41  dischi
# move objectcache to util
#
# Revision 1.14  2003/11/28 20:08:58  dischi
# renamed some config variables
#
# Revision 1.13  2003/11/22 12:02:12  dischi
# make the skin blankscreen a real plugin area
#
# Revision 1.12  2003/10/28 17:54:12  dischi
# take icons from theme if available
#
# Revision 1.11  2003/10/17 18:51:33  dischi
# check for default with description area
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
#endif


import copy
import os
import pygame
import stat

import osd
import config
import util

import xml_skin
import screen

SkinObjects = screen.SkinObjects


# Create the OSD object
osd = osd.get_singleton()


class Geometry:
    """
    Simple object with x, y, with, height values
    """
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width  = width
        self.height = height



class Skin_Area:
    """
    the base call for all areas. Each child needs two functions:

    def update_content_needed
    def update_content
    """
    def __init__(self, name, imagecachesize=5):
        self.area_name = name
        self.area_val  = None
        self.redraw    = True
        self.layout    = None
        self.name      = name
        self.screen    = screen.get_singleton()
        self.objects   = SkinObjects()
        
        self.imagecache = util.objectcache.ObjectCache(imagecachesize,
                                                       desc='%s_image' % self.name)


    def update_content_needed(self):
        """
        this area needs a content update
        """
        return True


    def update_content(self):
        """
        there is no content in this area
        """
        pass
    

    def draw(self, settings, obj, menu, display_style=0, widget_type='menu',
             force_redraw=False):
        """
        this is the main draw function. This function draws the background,
        checks if redraws are needed and calls the two update functions
        for the different types of areas
        """

        self.display_style = display_style
        self.xml_settings  = settings
        self.widget_type   = widget_type

        self.menuw = obj
        if menu:
            self.menu = menu
            if self.menu.force_skin_layout != -1:
                self.display_style = self.menu.force_skin_layout
            
            if self.menu.viewitem:
                self.viewitem = self.menu.viewitem
            else:
                self.viewitem  = self.menu.selected
            if self.menu.infoitem:
                self.infoitem = self.menu.infoitem
            else:
                self.infoitem  = self.menu.selected
            item_type  = self.menu.item_types
            self.scan_for_text_view(self.menu)

        else:
            self.menu = obj
            item_type = None
            try:
                self.viewitem = obj.selected
                self.infoitem = obj.selected
            except AttributeError:
                self.viewitem = obj
                self.infoitem = obj

        self.redraw = force_redraw
        
        area = self.area_val
        if area:
            visible = area.visible
        else:
            visible = False

        self.redraw = self.init_vars(settings, item_type, widget_type)
            
        if area and area != self.area_val:
            old_area = area
        else:
            old_area = None
            
        area = self.area_val

        # maybe we are NOW invisible
        if visible and not area.visible and old_area:
            self.screen.update('background', (old_area.x, old_area.y,
                                              old_area.x + old_area.width,
                                              old_area.y + old_area.height))
            self.objects = SkinObjects()

        if not self.area_name == 'plugin':
            if not area.visible or not self.layout:
                self.objects = SkinObjects()
                return

            self.tmp_objects = SkinObjects()
            self.__draw_background__()
        else:
            self.tmp_objects = SkinObjects()
            
        # dependencies haven't changed, if no update needed: return
        if not self.redraw and not self.update_content_needed():
            self.screen.draw(self.objects)
            return

        self.update_content()


        # check which parts need an update
        bg_rect = ( osd.width, osd.height, 0, 0 )
        a_rect  = ( osd.width, osd.height, 0, 0 )
        c_rect  = ( osd.width, osd.height, 0, 0 )

        for b in self.tmp_objects.bgimages:
            try:
                self.objects.bgimages.remove(b)
            except ValueError:
                bg_rect = ( min(bg_rect[0], b[0]), min(bg_rect[1], b[1]),
                            max(bg_rect[2], b[2]), max(bg_rect[3], b[3]) )

        for b in self.objects.bgimages:
            bg_rect = ( min(bg_rect[0], b[0]), min(bg_rect[1], b[1]),
                        max(bg_rect[2], b[2]), max(bg_rect[3], b[3]) )



        for b in self.tmp_objects.rectangles:
            try:
                self.objects.rectangles.remove(b)
            except ValueError:
                a_rect = ( min(a_rect[0], b[0]), min(a_rect[1], b[1]),
                           max(a_rect[2], b[2]), max(a_rect[3], b[3]) )

        for b in self.objects.rectangles:
            a_rect = ( min(a_rect[0], b[0]), min(a_rect[1], b[1]),
                       max(a_rect[2], b[2]), max(a_rect[3], b[3]) )



        for b in self.tmp_objects.images:
            try:
                self.objects.images.remove(b)
            except ValueError:
                c_rect = ( min(c_rect[0], b[0]), min(c_rect[1], b[1]),
                           max(c_rect[2], b[2]), max(c_rect[3], b[3]) )

        for b in self.objects.images:
            c_rect = ( min(c_rect[0], b[0]), min(c_rect[1], b[1]),
                       max(c_rect[2], b[2]), max(c_rect[3], b[3]) )



        for b in self.tmp_objects.text:
            try:
                self.objects.text.remove(b)
            except ValueError:
                c_rect = ( min(c_rect[0], b[0]), min(c_rect[1], b[1]),
                           max(c_rect[2], b[2]), max(c_rect[3], b[3]) )

        for b in self.objects.text:
            c_rect = ( min(c_rect[0], b[0]), min(c_rect[1], b[1]),
                       max(c_rect[2], b[2]), max(c_rect[3], b[3]) )



        # send the update information to the screen object
        if bg_rect[0] < bg_rect[2]:
            self.screen.update('background', bg_rect)

        if a_rect[0] < a_rect[2]:
            self.screen.update('alpha', a_rect)
            if c_rect[0] < c_rect[2] and \
               not (c_rect[0] >= a_rect[0] and c_rect[1] >= a_rect[1] and \
                    c_rect[2] <= a_rect[2] and c_rect[3] <= a_rect[3]):
                self.screen.update('content', c_rect)

        elif c_rect[0] < c_rect[2]:
            self.screen.update('content', c_rect)

        # save and exit
        self.objects = self.tmp_objects
        self.screen.draw(self.objects)


    def scan_for_text_view(self, menu):
        """
        scan if we have to fall back to text view. This will be done if some
        items have images and all images are the same. And the number of items
        must be greater 5. With that the skin will fall back to text view for
        e.g. mp3s inside a folder with cover file
        """
        try:
            self.use_text_view = menu.skin_force_text_view
            try:
                self.use_images      = menu.skin_default_no_images
                self.use_description = menu.skin_default_has_description
            except:
                self.use_images      = False
                self.use_description = False
            return
        except:
            pass

        image  = None
        folder = 0

        menu.skin_default_no_images       = False
        menu.skin_default_has_description = False

        for i in menu.choices:
            if i.image:
                menu.skin_default_no_images = True
            if i.description:
                menu.skin_default_has_description = True
            try:
                if i.info['description']:
                    menu.skin_default_has_description = True
            except KeyError:
                pass
            
            if menu.skin_default_no_images and menu.skin_default_has_description:
                break
            
        self.use_images = menu.skin_default_no_images
        self.use_description = menu.skin_default_has_description

        if len(menu.choices) < 6:
            try:
                if menu.choices[0].info_type == 'track':
                    menu.skin_force_text_view = True
                    self.use_text_view = True
                    return
            except:
                pass

            for i in menu.choices:
                if config.SKIN_FORCE_TEXTVIEW_STYLE == 1 and \
                       i.type == 'dir' and not i.media:
                    # directory with few items and folder:
                    self.use_text_view = False
                    return
                    
                if image and i.image != image:
                    menu.skin_force_text_view = False
                    self.use_text_view = False
                    return
                image = i.image

            menu.skin_force_text_view = True
            self.use_text_view = True
            return

        for i in menu.choices:
            if i.type == 'dir':
                folder += 1
                # directory with mostly folder:
                if config.SKIN_FORCE_TEXTVIEW_STYLE == 1 and folder > 3 and not i.media:
                    self.use_text_view = False
                    return
                    
            if image and i.image != image:
                menu.skin_force_text_view = False
                self.use_text_view = False
                return
            image = i.image
        menu.skin_force_text_view = True
        self.use_text_view = True

    
    def calc_geometry(self, object, copy_object=0):
        """
        calculate the real values of the object (e.g. content) based
        on the geometry of the area
        """
        if copy_object:
            object = copy.copy(object)

        font_h=0

        MAX=self.area_val.width
        if isinstance(object.width, str):
            object.width = int(eval(object.width))

        MAX=self.area_val.height
        if isinstance(object.height, str):
            object.height = int(eval(object.height))

        object.x += self.area_val.x
        object.y += self.area_val.y
        
        if not object.width:
            object.width = self.area_val.width

        if not object.height:
            object.height = self.area_val.height

        if object.width + object.x > self.area_val.width + self.area_val.x:
            object.width = self.area_val.width - object.x

        if object.height + object.y > self.area_val.height + self.area_val.y:
            object.height = self.area_val.height + self.area_val.y - object.y

        return object

        
    def get_item_rectangle(self, rectangle, item_w, item_h, font_h=0):
        """
        calculates the values for a rectangle inside the item tag
        """
        r = copy.copy(rectangle)

        if not r.width:
            r.width = item_w

        if not r.height:
            r.height = item_h

        MAX=item_w
        if isinstance(r.x, str):
            r.x = int(eval(r.x))
        if isinstance(r.width, str):
            r.width = int(eval(r.width))
            
        MAX=item_h
        if isinstance(r.y, str):
            r.y = int(eval(r.y))
        if isinstance(r.height, str):
            r.height = int(eval(r.height))
            
        if r.x < 0:
            item_w -= r.x

        if r.y < 0:
            item_h -= r.y

        return max(item_w, r.width), max(item_h, r.height), r
    

    def fit_item_in_rectangle(self, rectangle, width, height):
        """
        calculates the rectangle geometry and fits it into the area
        """
        x = 0
        y = 0
        r = self.get_item_rectangle(rectangle, width, height)[2]
        if r.width > width:
            r.width, width = width, width - (r.width - width)
        if r.height > height:
            r.height, height = height, height - (r.height - height)
        if r.x < 0:
            r.x, x = 0, -r.x
            width -= x
        if r.y < 0:
            r.y, y = 0, -r.y
            height -= y

        return Geometry(x, y, width, height), r
    

    def init_vars(self, settings, display_type, widget_type = 'menu'):
        """
        check which layout is used and set variables for the object
        """
        redraw = self.redraw
        self.settings = settings

        if widget_type == 'menu':
            # get the correct <menu>
            try:
                area = settings.menu[display_type]
            except:
                if not self.use_images:
                    if self.use_description and \
                           settings.menu.has_key('default description no image'):
                        area = settings.menu['default description no image']
                    else:
                        try:
                            area = settings.menu['default no image']
                        except:
                            area = settings.menu['default']
                elif self.use_description and \
                         settings.menu.has_key('default description'):
                    area = settings.menu['default description']
                else:
                    area = settings.menu['default']

            # get the correct style based on display_style
            if len(area.style) > self.display_style:
                area = area.style[self.display_style]
            else:
                try:
                    area = area.style[0]
                except IndexError:
                    print 'index error for %s %s' % (self.display_style, widget_type)
                    raise

            if area[0] and (not self.use_text_view):
                area = area[0]
            elif area[1]: 
                area = area[1]
            else:
                print 'want to fall back, but no text view defined'
                area = area[0]

        else:
            area = settings.sets[widget_type]
            if hasattr(area, 'style'):
                try:
                    area = area.style[self.display_style][1]
                except:
                    area = area.style[0][1]


        if self.area_name == 'plugin':
            if not self.area_val:
                self.area_val = xml_skin.Area(self.area_name)
                self.area_val.visible = True
                self.area_val.r = (0, 0, osd.width, osd.height)
            return True
        else:
            try:
                area = getattr(area, self.area_name)
            except AttributeError:
                try:
                    area = area.areas[self.area_name]
                except (KeyError, AttributeError):
                    print 'no skin information for %s:%s' % (widget_type, self.area_name)
                    area = xml_skin.Area(self.area_name)
                    area.visible = False

        if (not self.area_val) or area != self.area_val:
            self.area_val = area
            redraw = True
            
        if not area.layout:
            return redraw

        old_layout  = self.layout
        self.layout = area.layout

        if old_layout and old_layout != self.layout:
            redraw = True

        area.r = (area.x, area.y, area.width, area.height)

        return redraw
        

    def __draw_background__(self):
        """
        draw the <background> of the area
        """
        area = self.area_val

        last_watermark = None

        try:
            if self.watermark:
                last_watermark = self.watermark

                try:
                    if self.menu.selected.image != self.watermark:
                        self.watermark = None
                        self.redraw = True
                except:
                    pass
        except:
            pass
        
        for bg in self.layout.background:
            bg = copy.copy(bg)
            if isinstance(bg, xml_skin.Image) and bg.visible:
                self.calc_geometry(bg)
                imagefile = ''
                
                # if this is the real background image, ignore the
                # OVERSCAN to fill the whole screen
                if bg.label == 'background':
                    bg.x -= config.OSD_OVERSCAN_X
                    bg.y -= config.OSD_OVERSCAN_Y
                    bg.width  += 2 * config.OSD_OVERSCAN_X
                    bg.height += 2 * config.OSD_OVERSCAN_Y

                if bg.label == 'watermark' and self.menu.selected.image:
                    imagefile = self.menu.selected.image
                    if last_watermark != imagefile:
                        self.redraw = True
                    self.watermark = imagefile
                else:
                    imagefile = bg.filename

                if self.name == 'screen':
                    bg.label = 'background'
                    
                if imagefile:
                    cname = '%s-%s-%s' % (imagefile, bg.width, bg.height)
                    image = self.imagecache[cname]
                    if not image and config.OVERLAY_DIR:
                        cache = vfs.getoverlay('%s.raw-%sx%s' % (imagefile, bg.width,
                                                                 bg.height))
                        if os.path.isfile(cache) and \
                               os.stat(cache)[stat.ST_MTIME] > \
                               os.stat(imagefile)[stat.ST_MTIME]:
                            f = open(cache, 'r')
                            image = pygame.image.fromstring(str().join(f.readlines()),
                                                            (bg.width,bg.height), 'RGBA')
                            f.close()
                            self.imagecache[cname] = image
                    if not image:
                        image = osd.loadbitmap(imagefile)
                        if image:
                            image = pygame.transform.scale(image,(bg.width,bg.height))
                        if image and config.OVERLAY_DIR:
                            f = vfs.open(cache, 'w')
                            f.write(pygame.image.tostring(image, 'RGBA'))
                            f.close()
                        self.imagecache[cname] = image
                    if image:
                        self.drawimage(image, bg)
                            
            elif isinstance(bg, xml_skin.Rectangle):
                self.calc_geometry(bg)
                self.drawroundbox(bg.x, bg.y, bg.width, bg.height, bg)

            


    # functions for the area to draw stuff on the screen
    #
    # drawroundbox
    # drawimage
    # drawstring

    def drawroundbox(self, x, y, width, height, rect, redraw=True):
        """
        draw a round box ... or better stores the information about this call
        in a variable. The real drawing is done inside draw()
        """
        try:
            self.tmp_objects.rectangles.append(( x, y, x + width, y + height, rect.bgcolor,
                                                 rect.size, rect.color, rect.radius ))
        except AttributeError:
            self.tmp_objects.rectangles.append(( x, y, x + width, y + height, rect[0],
                                                 rect[1], rect[2], rect[3] ))


            
    def drawstring(self, text, font, content, x=-1, y=-1, width=None, height=None,
                   align_h = None, align_v = None, mode='hard', ellipses='...'):
        """
        writes a text ... or better stores the information about this call
        in a variable. The real drawing is done inside draw()
        """

        if not text:
            return (0,0,0,0)

        # set default values from 'content'
        if x == -1:
            x = content.x
        if y == -1:
            y = content.y

        if width == None:
            width  = content.width
        if height == None:
            height = content.height

        if not align_h and content:
            align_h = content.align
        if not align_h:
            align_h = 'left'
                
        if not align_v and content:
            align_v = content.valign
        if not align_v:
            align_v = 'top'

        height2 = height
        if height2 == -1:
            height2 = font.h + 2

        self.tmp_objects.text.append((x, y, x+width, y+height2, _(text), font, height,
                                            align_h, align_v, mode, ellipses))


    def loadimage(self, image, val, redraw=True):
        """
        load an image (use self.imagecache)
        """
        if image.find(config.ICON_DIR) == 0 and image.find(self.settings.icon_dir) == -1:
            new_image = os.path.join(self.settings.icon_dir, image[len(config.ICON_DIR)+1:])
            if os.path.isfile(new_image):
                image = new_image

        if isinstance(val, tuple) or isinstance(val, list):
            w = val[0]
            h = val[1]
        else:
            w = val.width
            h = val.height
            
        cname = '%s-%s-%s' % (image, w, h)
        cimage = self.imagecache[cname]
        if not cimage:
            cimage = osd.loadbitmap(image)
            if cimage and w > 0 and h > 0:
                cimage = pygame.transform.scale(cimage, (w, h))
            self.imagecache[cname] = cimage
        return cimage

        
    def drawimage(self, image, val):
        """
        draws an image ... or better stores the information about this call
        in a variable. The real drawing is done inside draw()
        """

        if not image:
            return 0,0

        if isinstance(image, str):
            if isinstance(val, tuple):
                image = self.loadimage(image, val[2:])
            else:
                image = self.loadimage(image, val)

        if not image:
            return 0,0
        
        if isinstance(val, tuple):
            self.tmp_objects.images.append((val[0], val[1], val[0] + image.get_width(),
                                            val[1] + image.get_height(), image))
            return image.get_width(), image.get_height()

        try:
            if val.label == 'background':
                self.tmp_objects.bgimages.append((val.x, val.y, val.x + val.width,
                                                  val.y + val.height, image))
                return val.width, val.height
        except:
            pass
        
        self.tmp_objects.images.append((val.x, val.y, val.x + val.width,
                                        val.y + val.height, image))
        return val.width, val.height
        


    # compatibility functions, will be removed
    write_text = drawstring
    draw_image = drawimage
