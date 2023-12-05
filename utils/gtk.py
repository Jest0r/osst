import sys
import gi
import numpy as np

import cv2

PI = 3.14159265359

# https://github.com/Taiko2k/GTK4PythonTutorial

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject, GLib, Gdk, GdkPixbuf

MIN_WIN_WIDTH = 800
MIN_WIN_HEIGHT = 400


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_size(800, 500)
        self.set_title("TestApp")

        # Add a box
        self.rootbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.centerbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.mainbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.sidebox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.statusbarbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        # set minimum window size
        self.rootbox.set_size_request(width=MIN_WIN_WIDTH, height=MIN_WIN_HEIGHT)

        # Add a button
        self.button = Gtk.Button(label="Hello")
        self.button.connect("clicked", self.hello)

        # Place stuff
        self.set_child(self.rootbox)
        self.rootbox.append(self.centerbox)
        self.rootbox.append(self.statusbarbox)

        self.centerbox.append(self.mainbox)
        self.centerbox.append(self.sidebox)

        self.sidebox.append(self.button)

        self.notebook1 = Gtk.Notebook()
        self.page1 = Gtk.Box()
        self.page2 = Gtk.Box()

        self.notebook1.append_page(self.page1, Gtk.Label(label="first"))
        self.notebook1.append_page(self.page2, Gtk.Label(label="second"))

        self.mainbox.append(self.notebook1)

        w, h = self.get_default_size()
        self.orig_draw_w = w // 2
        self.orig_draw_h = h // 2

        self.maindrawing = Gtk.DrawingArea()
        self.maindrawing.set_content_width(w // 2)
        self.maindrawing.set_content_height(h // 2)
        self.maindrawing.set_draw_func(self.draw, None)
        self.maindrawing.connect("realize", self.realize)

        self.caminfo = Gtk.TextView()
        tb = self.caminfo.get_buffer()
        tb.set_text("This is a test for the camera settings")
        self.caminfo.set_buffer(tb)

        self.page1.append(self.maindrawing)
        self.f = Gtk.Frame()
        self.f.set_label("framelabel")
        self.statusbarbox.append(self.f)
        self.statusbarbox.append(self.caminfo)

        self.frame = None
        self.raw_frame = None
        self.pixbuf = None

    def hello(self):
        print("button pressed")

    def realize(self, widget):
        print("realize")
        self.cam = cv2.VideoCapture(0, cv2.CAP_ANY)

    def expose_event(self, widget, event):
        print("expose")

    def resize(self, area, w, h):
        print(type(area))

    def draw(self, area, c, w, h, data):
        # if there is camera input, show it
        if self.pixbuf is not None:
            Gdk.cairo_set_source_pixbuf(c, self.pixbuf, 0, 0)
            c.rectangle(0, 0, 400, 250)
            c.fill()
        else:
            c.scale(0.5, 2)
            c.set_source_rgb(0, 0, 0)
            c.arc(w // 2, h // 2, w // 4, 0, 2 * PI)
            c.stroke()

            c.translate(200, 150)

    def hello(self, button):
        print("Hello world")

    def on_resize(self, win):
        print("hello")

    def on_timeout(self, data):
        # get drawing area size
        width = self.maindrawing.get_size(Gtk.Orientation.HORIZONTAL)
        height = self.maindrawing.get_size(Gtk.Orientation.VERTICAL)
        if width == 0 or height == 0:
            return False

        # read camera and resize to drawing area size
        ret, self.raw_frame = self.cam.read()
        self.raw_frame = cv2.cvtColor(self.raw_frame, cv2.COLOR_BGR2RGB)

        self.frame = cv2.resize(self.raw_frame, (400, 250))
        fbytes = self.frame.tobytes()

        fb = GLib.Bytes.new(fbytes)

        # convert to pixbuf
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
            fb,
            colorspace=GdkPixbuf.Colorspace.RGB,
            has_alpha=False,
            bits_per_sample=8,
            width=width,
            height=height,
            rowstride=width * 3,
        )

        self.maindrawing.queue_draw()
        print("-")
        return True


class MyApp(Gtk.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()

        GLib.timeout_add(100, self.on_timeout, None)

    def on_timeout(self, data):
        self.win.on_timeout(data)
        return True


app = MyApp(application_id="com.github.jest0r.osst")
app.run(sys.argv)
