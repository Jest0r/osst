import sys
import gi
import numpy as np

#import cv2

PI = 3.14159265359

# https://github.com/Taiko2k/GTK4PythonTutorial

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, GLib, Gdk, GdkPixbuf



class MainWindow(Gtk.ApplicationWindow):
    '''
    window class - gui stuff goes here
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # main split view
        self.SV1 = Adw.NavigationSplitView()
        self.set_child(self.SV1)

        # sidebars for split view
        self.sidebar = Adw.NavigationPage()
        self.content = Adw.NavigationPage()

        self.SV1.set_sidebar(self.sidebar)
        self.SV1.set_content(self.content)
        self.SV1.set_show_content(self.content)

        # sidebar properties
        self.SV1.set_min_sidebar_width(100)
        self.SV1.set_max_sidebar_width(400)

        # define what goes into side- and mainbar         
        self.mainbox = Gtk.Box()
        self.content.set_child(self.mainbox)

        self.sidebox = Gtk.Box()
        self.sidebar.set_child(self.sidebox)

        # some test buttons
        self.hello_button = Gtk.Button(label="sidebar")
        self.hello_button.connect('clicked', self.toggle_sidebar)

        self.collapse_button = Gtk.Button(label="Collapse sidebar")
        self.collapse_button.connect('clicked', self.toggle_sidebar)

        self.sidebox.append(self.hello_button)
        self.mainbox.append(self.collapse_button)
    
    def toggle_sidebar(self, b):
        self.SV1.set_collapsed(not self.SV1.get_collapsed())
        


        


class AdwOsst(Adw.Application):
    '''
    main appliation - all the logic goes here
    '''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()

# ---------------------------------------------------------
#
# M A I N
#
# ---------------------------------------------------------
def main():
    ''' Main. Not a lot should happen here'''
    osst = AdwOsst(application_id="com.github.jest0r.osst")
    osst.run(sys.argv)


if __name__ == "__main__":
    main()
