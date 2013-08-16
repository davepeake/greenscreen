#!/usr/bin/env python

import sys

import cv2 as cv
import numpy as np

try:
    import pygtk
    pygtk.require("2.0")
except:
    pass

try:
    import gtk
    import gtk.glade
    import gobject
except:
    print "You need to install pyGTK or GTKv2 ",
    print "or set your PYTHONPATH correctly."
    print "try: export PYTHONPATH=",
    print "/usr/local/lib/python2.2/site-packages/"
    sys.exit(1)

class appgui:
    def __init__(self):
        gladefile = "greenscreen.glade"
        windowname = "mainwindow"
        self.wTree=gtk.glade.XML(gladefile, windowname)

        dic = { "on_quitbutton_clicked" :(gtk.main_quit),
                "on_fudge_spin_change_value" : self.fudge_change,
                "on_background_refresh_clicked" : self.refresh_background,
                "on_loadphoto_clicked": self.load_photo,
                "on_rescombo_changed": self.resolution_change,
                "on_radiobkg_clicked": self.chromatype_change,
                "on_segimg_button_release_event": self.segimg_click,
                "on_mask_toggle_toggled": self.mask_toggle,
                "on_savebutton_clicked": self.save_photo,
                "on_photo_eventbox_motion_notify_event": self.photo_drag,
                "on_mainwindow_destroy" : (gtk.main_quit) }

        self.wTree.signal_autoconnect(dic)

        self.cam = cv.VideoCapture()
        self.cam.open(-1)

        self.fudge = 0;

        combo_item = self.wTree.get_widget('rescombo').set_active(0)

        (val, self.img) = self.cam.read()
        self.background = self.img
        self.background_max = self.background * 1.1
        self.background_min = self.background * 0.9

        self.photo_pixbuf = None # no photo loaded yet
        self.photo_mask = None
        self.combined_photo = None 
        self.chroma_colour = [0,255,0]
        self.show_mask = False 

        self.chroma_technique = 0 # background subtraction

        self.update_image()

        event_box = self.wTree.get_widget('seg_eventbox')
        event_box.connect("button-release-event", self.segimg_click)


        gobject.timeout_add(200, self.update_image)
 
    def photo_drag(self, widget, event):
        if self.photo_mask == None:
            return

        cx = event.x
        cy = event.y

        cx_l = cx-20; # x lower
        if cx_l < 0:
            cx_l = 0
        cx_u = cx+20;
        if cx_u > self.photo_mask.shape[1]:
            cx_u = self.photo_mask.shape[1]
            
        cy_l = cy-20; # x lower
        if cy_l < 0:
            cy_l = 0
        cy_u = cy+20;
        if cy_u > self.photo_mask.shape[0]:
            cy_u = self.photo_mask.shape[0]

        
        if (event.state & gtk.gdk.BUTTON1_MASK):
            self.photo_mask[cy_l:cy_u, cx_l:cx_u] = 0;
        elif (event.state & gtk.gdk.BUTTON3_MASK):
            self.photo_mask[cy_l:cy_u, cx_l:cx_u] = 1;

        #print cx_l, cx_u, cy_l, cy_u

    def mask_toggle(self, widget):
        self.show_mask = widget.get_active()

    def chromatype_change(self,widget):
        chroma_radio = self.wTree.get_widget('chromaradio')
        bkg_radio = self.wTree.get_widget('radiobkg')

        if chroma_radio.get_active():
            self.chroma_technique = 0
        else:
            self.chroma_technique = 1

    def segimg_click(self, widget, event):
        self.chroma_colour = self.img[event.y, event.x, :]
        print 'Chroma colour set to %s', self.chroma_colour

    def load_photo(self, widget):
        mainwin = self.wTree.get_widget('mainwindow')
        chooser = gtk.FileChooserDialog('Open...', None, action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                        buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))

        chooser.set_default_response(gtk.RESPONSE_OK)

        filter = gtk.FileFilter()
        filter.set_name("Images")
        filter.add_mime_type("image/jpeg")
        filter.add_mime_type("image/png")
        filter.add_mime_type("image/bmp")
        chooser.add_filter(filter)

        #chooser.set_modal(True)
        response = chooser.run()

        if response == gtk.RESPONSE_OK:
            self.filename = chooser.get_filename()

            self.scale_photo()

            photo_event_box = self.wTree.get_widget('photo_eventbox')        
            photo_event_box.connect("motion-notify-event", self.photo_drag)

        elif response == gtk.RESPONSE_CANCEL:
            print 'Closed, no files selected'
        chooser.destroy()

    def scale_photo(self):
        self.photo_pixbuf = gtk.gdk.pixbuf_new_from_file(self.filename)
        self.photo_pixbuf = self.photo_pixbuf.scale_simple(self.img.shape[1], self.img.shape[0], gtk.gdk.INTERP_BILINEAR)
        photo_img = self.wTree.get_widget('photoimg')

        photo_img.set_from_pixbuf(self.photo_pixbuf)

        self.photo_mask = (np.ones([self.img.shape[0], self.img.shape[1]]) == 1)

    def save_photo(self, widget):
        if self.combined_photo == None:
            print 'No photo to save, you muppet.'
            return

        mainwin = self.wTree.get_widget('mainwindow')
        chooser = gtk.FileChooserDialog('Save...', None, action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                        buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))

        chooser.set_default_response(gtk.RESPONSE_OK)

        filter = gtk.FileFilter()
        filter.set_name("Images")
        filter.add_mime_type("image/jpeg")
        filter.add_mime_type("image/png")
        filter.add_mime_type("image/bmp")
        chooser.add_filter(filter)

        #chooser.set_modal(True)
        response = chooser.run()

        if response == gtk.RESPONSE_OK:
            filename = chooser.get_filename()

            self.combined_photo.save(filename,'jpeg')

        chooser.destroy()

    def resolution_change(self, widget):
        print "combo box value: %d"%(widget.get_active())
        
        combo_item = widget.get_active()
        if combo_item == 0:
                self.cam.set(cv.cv.CV_CAP_PROP_FRAME_WIDTH,640)
                self.cam.set(cv.cv.CV_CAP_PROP_FRAME_HEIGHT,480)
        elif combo_item == 1:
                self.cam.set(cv.cv.CV_CAP_PROP_FRAME_WIDTH,800)
                self.cam.set(cv.cv.CV_CAP_PROP_FRAME_HEIGHT,448)
        elif combo_item == 2:
                self.cam.set(cv.cv.CV_CAP_PROP_FRAME_WIDTH,1280)
                self.cam.set(cv.cv.CV_CAP_PROP_FRAME_HEIGHT,720)

        self.refresh_background(None)
        try:
            if self.photo_pixbuf is not None:
                self.scale_photo()
        except: 
            pass

    def refresh_background(self, widget):
        (val, self.img) = self.cam.read()
        self.background = self.img
        self.background_max = self.background * 1.1
        self.background_min = self.background * 0.9

    def fudge_change(self, widget):        
        self.fudge = widget.get_value()
        #print 'fudge factor changed to %f'%(widget.get_value())

    def update_image(self):
        raw_img = self.wTree.get_widget('rawimg')
        seg_img = self.wTree.get_widget('segimg')

        if raw_img == None:
            return False

        (val, self.img) = self.cam.read()

        self.img = self.img[:,:,[2,1,0]] # images are in BGR order (see VideoReader docs)

        img_pixbuf = gtk.gdk.pixbuf_new_from_data(self.img.tostring(),
                                                  gtk.gdk.COLORSPACE_RGB,
                                                  False,
                                                  8,
                                                  self.img.shape[1],
                                                  self.img.shape[0],
                                                  self.img.shape[1]*self.img.shape[2])

        raw_img.set_from_pixbuf(img_pixbuf)
        raw_img.show()

        # segmented image
        #imgsum = self.img
        #img_mask = (imgsum < self.background_max) & (imgsum > self.background_min)

        #self.img[img_mask] = 0

        '''
        thoughts.
        The mask equals 1 where we want the img to bleed through to the composite. 
        For the background, we then want where the image equals the background (no change) for the mask to be zero.
        Therefore we want the mask to be where the background-img is greater than some value.

        Can be done a million times better with a mathematical approach to background subtraction, segmenting out the foreground and background.

        For chromakey
        Ideally we're just looking for one colour (green, blue) and we make the mask == 0 for that colour. 
        For robustness we'll need to fudge around that point (also the camera isn't 100% colour stable anyway)
        So if the mask colour is [0,255,0] then we should also mask out colours between [-ff, 255-ff, 0-ff] to [ff,255+ff,ff] in all dimensions
        '''

        if self.chroma_technique == 0: # chromakey
            # three times for each channel
            color_fudge = [i - self.fudge for i in self.chroma_colour]
            img_mask_lower = (self.img[:,:,0] >= color_fudge[0]) & \
                             (self.img[:,:,1] >= color_fudge[1]) & \
                             (self.img[:,:,2] >= color_fudge[2])

            color_fudge = [i + self.fudge for i in self.chroma_colour]
            img_mask_upper = (self.img[:,:,0] <=  color_fudge[0]) & \
                             (self.img[:,:,1] <= color_fudge[1]) & \
                             (self.img[:,:,2] <= color_fudge[2])

            img_mask = ~(img_mask_lower & img_mask_upper)
        else: # background subtraction
            imgdiff = abs(self.img-self.background)
            img_mask = imgdiff.max(2) > self.fudge  # see notes above

        self.segimg = self.img.copy()
        self.segimg[img_mask,:] = [0,255,0] 
        self.segimg[~img_mask,:] = [255,0,0]
        
        if self.show_mask:
            img_pixbuf = gtk.gdk.pixbuf_new_from_data(self.segimg.tostring(),
                                                      gtk.gdk.COLORSPACE_RGB,
                                                      False,
                                                      8,
                                                      self.segimg.shape[1],
                                                      self.segimg.shape[0],
                                                      self.segimg.shape[1]*self.segimg.shape[2])
        seg_img.set_from_pixbuf(img_pixbuf)
        seg_img.show()

        if self.photo_pixbuf is not None:
            img_mask = img_mask & self.photo_mask

            photo_data_copy = self.photo_pixbuf.copy()
            photo_data_buff = photo_data_copy.get_pixels_array()

            photo_data_buff[img_mask,:] = self.img[img_mask,:]

            photo_data_with_mask = self.photo_pixbuf.copy()
            photo_data_with_mask_pix = photo_data_with_mask.get_pixels_array()
            photo_data_with_mask_pix[~self.photo_mask,:] = [255,0,0]

            self.wTree.get_widget('photoimg').set_from_pixbuf(photo_data_with_mask)

            '''
            combined_pixbuf = gtk.gdk.pixbuf_new_from_data(photo_data_buff.tostring(),
                                                            gtk.gdk.COLORSPACE_RGB,
                                                            False,
                                                            8,
                                                            photo_data_buff.shape[1],
                                                            photo_data_buff.shape[0],
                                                            photo_data_buff.shape[1]*photo_data_buff.shape[2])
            '''
            photo_data_copy = photo_data_copy.scale_simple(self.img.shape[1], self.img.shape[0], gtk.gdk.INTERP_BILINEAR)

            self.combined_photo = photo_data_copy.copy() # for saving

            self.wTree.get_widget('combimg').set_from_pixbuf(photo_data_copy)

        return True

if __name__ == '__main__':
    app = appgui()
    gtk.main()
