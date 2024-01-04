from gi.repository import Adw, Gtk, Gio, Gdk, GObject, GLib, GdkPixbuf
import numpy as np
import cv2

PI = 3.14159265359


class CameraFrame:
    """
    A class to deal with cv2 webcam frames, use and interact them
    within a GtkDrawingAre using Cairo
    """

    # NEVER UPDATE THESE MANUALLY
    # original frame
    _frame = None
    _pixbuf = None
    _w = 0
    _h = 0
    _chan = 0
    _aspect = 0.0  # width / height

    def __init__(self, cv2_frame, bgr2rgb=False):
        self._set_frame(cv2_frame)
        if bgr2rgb:
            self.bgr2rgb()

    def __repr__(self):
        return f"{type(self)} of dim (h/w[/chan]) {np.shape(self._frame)}"

    # private methods
    def _set_frame(self, frame):
        self._frame = frame
        self._update_meta()
        self._pixbuf = None

    #        self._create_pixbuf()

    def _update_meta(self):
        """update the metadata for perf readons"""
        shape = np.shape(self._frame)

        if len(shape) == 3:
            self._chan = shape[2]
        else:
            self._chan = 1

        self._w = np.shape(self._frame)[1]
        self._h = np.shape(self._frame)[0]

        self._aspect = self._w / self._h

    def _create_pixbuf(self):
        # bytes from frame
        # using get_rgb_frame, so it also works with grayscale
        glib_bytes = GLib.Bytes.new(self.get_rgb_frame().tobytes())

        self._pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
            glib_bytes,
            colorspace=GdkPixbuf.Colorspace.RGB,
            has_alpha=False,
            bits_per_sample=8,
            width=self._w,
            height=self._h,
            rowstride=self._w * 3,
        )

    # getters
    def get_frame(self):
        return self._frame

    def get_width(self):
        """get width of frame"""
        return self._w

    def get_height(self):
        """get height of frame"""
        return self._h

    def get_channels(self):
        """get number of color channels of frame"""
        return self._chan

    def get_center_cropped(self, crop_size):
        """
        get a center-cropped version of the frame
        """
        start_x = (self._w - crop_size[0]) // 2
        start_y = (self._h - crop_size[1]) // 2
        # crop the image (be aware of the x/y sequence)
        newframe = self._frame[
            start_y : (start_y + crop_size[1]), start_x : (start_x + crop_size[0])
        ]
        return newframe

    def get_grayscale(self):
        """
        get a grayscale version of the object
        it's recommended to store frames in a separate object if
        it's referred to multiple times
        """
        if self._chan == 1:
            return CameraFrame(self._frame)
        else:
            return CameraFrame(cv2.cvtColor(self._frame, cv2.COLOR_RGB2GRAY))

    def get_rgb(self):
        """
        get a 3-channel version of the object
        it's recommended to store frames in a separate object if
        it's referred to multiple times
        """
        if self._chan == 1:
            return CameraFrame(cv2.cvtColor(self._frame, cv2.COLOR_GRAY2RGB))
        else:
            return CameraFrame(self._frame)

    def get_grayscale_frame(self):
        """
        get a grayscale version of the frame
        it's recommended to store frames in a separate object if
        it's referred to multiple times
        """
        if self._chan == 1:
            return self._frame
        else:
            return cv2.cvtColor(self._frame, cv2.COLOR_RGB2GRAY)

    def get_rgb_frame(self):
        """
        get a 3-channel version of the frame
        it's recommended to store frames in a separate object if
        it's referred to multiple times
        """
        if self._chan == 1:
            return cv2.cvtColor(self._frame, cv2.COLOR_GRAY2RGB)
        else:
            return self._frame

    def get_blurred_frame(self, radius):
        """get a Gaussian Blur version of the frame"""
        return cv2.GaussianBlur(self._frame, (radius, radius), 0)

    def get_blurred(self, radius):
        """get a Gaussian Blur version of the object"""
        return CameraFrame(cv2.GaussianBlur(self._frame, (radius, radius), 0))

    def get_pixbuf(self):
        if self._pixbuf is None:
            self._create_pixbuf()
        return self._pixbuf

    def get_scaled_pixbuf(self, width=None, height=None, mode=0):
        if width is None and height is None:
            return None
        elif width is None:
            # calc height from aspect
            width = height * self._aspect
        elif height is None:
            # calc height from aspect
            height = int(width / self._aspect)

        frame = cv2.resize(self.get_rgb_frame(), (width, height))
        glib_bytes = GLib.Bytes.new(frame.tobytes())

        pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
            glib_bytes,
            colorspace=GdkPixbuf.Colorspace.RGB,
            has_alpha=False,
            bits_per_sample=8,
            width=width,
            height=height,
            rowstride=width * 3,
        )

        return pixbuf

    def get_scaled_pixbuf2(self, width=None, height=None, mode=0):
        """
        return a scaled pixbuf
        scaling mode can be chosen
        """
        if self._pixbuf is None:
            self._create_pixbuf()
        # deal with arguments
        if width is None and height is None:
            return None
        elif width is None:
            # calc height from aspect
            width = height * self._aspect
        elif height is None:
            # calc height from aspect
            height = int(width / self._aspect)

        return self._pixbuf.scale_simple(width, height, mode)

    # manipulators
    def rotate_90deg(self, num_rotates):
        """rotates the frame 90 degrees X times"""
        self._set_frame(np.rot90(self._frame, num_rotates))

    def flip_horizontal(self):
        """flips the image horizontally"""
        self._set_frame(np.flip(self._frame, 1))

    def flip_vertical(self):
        """flips the image vertically"""
        self._set_frame(np.flip(self._frame, 0))

    def update(self, frame):
        """update frame"""
        self._set_frame(frame)

    def bgr2rgb(self):
        """convert color channels, used for most webcams"""
        self._set_frame(cv2.cvtColor(self._frame, cv2.COLOR_BGR2RGB))

    def center_crop(self, crop_size):
        """
        crop image centrally in-place
        """
        self._set_frame(self.get_center_cropped(crop_size))

    def blur(self, radius):
        """apply a Gaussian Blur to the object"""
        self.update(self.get_blurred_frame(radius))

    def draw_circle(self, c, color, pos, radius, width=1):
        if self._pixbuf is None:
            self._create_pixbuf()
        Gdk.cairo_set_source_pixbuf(c, self._pixbuf, 0, 0)
        c.set_source_rgb(color[0], color[1], color[2])
        c.set_line_width(width)

        #        Gdk.cairo_set_source_rgba(c, Gdk.RGBA.parse((255, 200, 100, 200)))
        #        c.paint_with_alpha(0.7)

        c.arc(pos[0], pos[1], radius, 0, 2 * PI)

        c.stroke()
