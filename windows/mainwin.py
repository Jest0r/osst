# window.py
#
# Copyright 2023 Helmut M
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Adw, Gtk, Gio, Gdk, GObject, GLib, GdkPixbuf

# import numpy as np

# import cv2

PI = 3.14159265359


class CamType(GObject.Object):
    """
    simple Camera Type object for the DropDown to work
    I haven't found a better way yet
    """

    __gtype_name___ = "Webcam"

    def __init__(self, cam_id, cam_name):
        super().__init__()

        self._cam_id = cam_id
        self._cam_name = cam_name

    @GObject.Property
    def cam_id(self):
        return self._cam_id

    @GObject.Property
    def cam_name(self):
        return self._cam_name


@Gtk.Template(filename="windows/mainwin_gtk.ui")
class OsstWindow(Adw.ApplicationWindow):
    __gtype_name__ = "OsstWindow"

    split_view = Gtk.Template.Child("split_view")
    target_surf = Gtk.Template.Child("target_surf")
    target_pane = Gtk.Template.Child("target_pane")
    target_frame = Gtk.Template.Child("target_frame")
    #    preview_pane = Gtk.Template.Child("previews")
    previews_frame = Gtk.Template.Child("previews_frame")
    settings_frame = Gtk.Template.Child("settings_frame")
    preview1_surf = Gtk.Template.Child("preview1_surf")
    preview2_surf = Gtk.Template.Child("preview2_surf")
    preview3_surf = Gtk.Template.Child("preview3_surf")
    preview4_surf = Gtk.Template.Child("preview4_surf")
    # status_output = Gtk.Template.Child("status_output")
    cam_chooser = Gtk.Template.Child("cam_chooser")
    cam_status_label = Gtk.Template.Child("cam_status_label")
    gray_threshold_level = Gtk.Template.Child("gray_thres_scale")
    blur_radius_level = Gtk.Template.Child("blur_radius_scale")
    target_radius_level = Gtk.Template.Child("target_radius_scale")

    preview_scale = None

    # controller objects
    # mouse moves
    target_drag_control = Gtk.Template.Child("target_drag_control")
    # mouse clicks
    target_click_control = Gtk.Template.Child("target_click_control")
    preview_click_control = Gtk.Template.Child("preview_click_control")
    # mouse scrolling
    scroll_control = Gtk.Template.Child("scroll_control")
    # keyboard
    key_events = Gtk.Template.Child("key_events")
    # target_type
    target_type_lp = Gtk.Template.Child("target_type_lp")

    #    status_bar = Gtk.Statusbar.get_context_id("status_bar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.application = kwargs["application"]
        self.pixbuf = None
        self.context = None
        self.width = None
        self.height = None

        self.offset_func = None
        self.zoom_func = None
        self.drag_func = None
        self.drag_start_func = None

        self.selected_webcam = None

        self.target_surf.connect("realize", self.on_target_realize)
        self.target_surf.connect("resize", self.on_target_resize)
        self.preview1_surf.connect("realize", self.on_preview_realize)
        self.preview1_surf.connect("resize", self.on_preview_resize)
        #        self.target_frame.connect("resize", self.on_target_pane_resize)

        self.connect("realize", self.on_show)

        # set callbacks for controller events
        self.scroll_control.connect("scroll", self.on_zoom)
        self.preview_click_control.connect("pressed", self.on_preview_click)
        self.target_click_control.connect("pressed", self.on_target_click)
        self.target_drag_control.connect("drag_update", self.on_target_drag)
        self.target_drag_control.connect("drag_begin", self.on_target_drag_start)
        self.key_events.connect("key-pressed", self.on_keypress)

        self.gray_threshold_level.connect("change-value", self.on_change_thres)
        self.blur_radius_level.connect("change-value", self.on_change_blur_rad)
        self.target_radius_level.connect("change-value", self.on_change_target_rad)

        #        self.split_view.connect("notify::size-allocate", self.on_split_view_resize)
        # add controllers
        # for the complete window
        self.add_controller(self.key_events)
        self.add_controller(self.scroll_control)
        # # for selected widgets
        self.target_type_lp.connect("toggled", self.application.set_target_type)

        self.target_surf.add_controller(self.target_drag_control)
        self.target_surf.add_controller(self.target_click_control)

        self.preview1_surf.add_controller(self.preview_click_control)
        self.preview2_surf.add_controller(self.preview_click_control)
        self.preview3_surf.add_controller(self.preview_click_control)
        self.preview4_surf.add_controller(self.preview_click_control)

        self.queue_draw()

    def on_target_realize(self, widget):
        self.target_surf.queue_draw()
        #        self.queue_draw()
        print("realize")

    def on_size_change(self, widget):
        #        self.target_surf.queue_draw()
        self.queue_draw()
        print("size change")

    def on_preview_click(self, gesture, num_press, x, y):
        """
        evaluates a mouse click in the preview window
        and set this as the midpoint of the camera in relation to the sight
        """
        self.offset_func([x * self.preview_scale, y * self.preview_scale])
        self.application.reset_target()

    def on_target_click(self, gesture, num_press, x, y):
        print("click")

    def on_target_drag(self, sgesture, offset_x, offset_y):
        print(f"dragging: {offset_x} {offset_y}")
        if self.drag_func is not None:
            self.drag_func(offset_x, offset_y)

            self.target_surf.queue_draw()

    def on_target_drag_start(self, sgesture, start_x, start_y):
        print(f"begin drag: {start_x} {start_y}")
        if self.drag_start_func is not None:
            self.drag_start_func(start_x, start_y)

            self.target_surf.queue_draw()

    def on_keypress(self, event_controller_key, keyval, keycode, state):
        print(event_controller_key, keyval, keycode, state)

    def on_zoom(self, event_controller_scroll, dx, dy):
        #        print(f"zoom {dx} {dy}")
        if self.zoom_func is not None:
            self.zoom_func(dy)

            self.target_surf.queue_draw()

    def target_Surf__scroll(self, w, e):
        print("scrollevent", w, e)

    def set_draw_func(self, draw_func):
        print("setting draw func")

        self.target_surf.set_draw_func(draw_func, None)

    def set_offset_func(self, offset_func):
        """sets the function that gets called with the recorded midpoint-offset"""
        self.offset_func = offset_func

    def set_zoom_func(self, zoomfunc):
        self.zoom_func = zoomfunc

    def set_drag_funcs(self, drag_start_func, drag_func):
        self.drag_start_func = drag_start_func
        self.drag_func = drag_func

    def get_context(self):
        return self.context

    def get_height(self):
        return self.height

    def get_width(self):
        return self.width

    def on_scroll(self, widget, event):
        print(widget, event)

    def add_status_text(self, status_text):
        status_text = f"{status_text.strip()}\n"
        textbuf = self.status_output.get_buffer()
        textbuf.insert_at_cursor(status_text, len(status_text))
        self.status_output.set_buffer(textbuf)
        self.queue_draw()

    def update_status_messages(self, messages):
        print(messages)
        t = Gtk.TextBuffer()
        t.set_text(messages, len(messages))
        self.status_output.set_buffer(t)
        self.queue_draw()

    def set_cam_list(self, camlist):
        self.model = Gio.ListStore(item_type=CamType)

        for cam_id, cam_name in camlist.items():
            self.model.append(CamType(cam_id=cam_id, cam_name=cam_name))

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)

        self.cam_chooser.connect("notify::selected-item", self._on_selected_item_notify)

        self.cam_chooser.set_factory(factory)
        self.cam_chooser.set_model(self.model)

    def _on_factory_setup(self, factory, list_item):
        label = Gtk.Label()
        list_item.set_child(label)

    def _on_factory_bind(self, factory, list_item):
        label = list_item.get_child()
        cam = list_item.get_item()
        label.set_text(cam.cam_name)

    def _on_selected_item_notify(self, item, _):
        cam = item.get_selected_item()
        self.selected_webcam = cam

        self.application.set_webcam(cam.cam_name, cam.cam_id)
        print(f"selected item {cam.cam_name} ({cam.cam_id})")

    def on_draw(self, area, c, w, h, data):
        print("mainwin draw")
        # if there is camera input, show it
        if self.pixbuf is not None:
            print(".")
            Gdk.cairo_set_source_pixbuf(c, self.pixbuf, 0, 0)
            c.rectangle(0, 0, 400, 250)
            c.fill()
        else:
            c.scale(1, 1)
            c.set_source_rgb(0, 0, 0)
            c.arc(w // 2, h // 2, w // 4, 0, 2 * PI)
            c.stroke()

            c.translate(200, 150)

    def on_show(self, w):
        self.target_surf.queue_draw()
        print("onshow")

    def on_target_resize(self, c, w, h):
        print(f"target resize {w}, {h}")

    def on_preview_realize(self, widget):
        self.target_surf.queue_draw()
        print("realize preview")
        #        self.queue_draw()

    def on_preview_resize(self, c, w, h):
        print(f"resize preview {w}, {h}")

    def on_preview_draw1(self, area, c, w, h):
        self.on_preview_draw(area, c, w, h, self.application.camera.raw_frame)

    def on_preview_draw2(self, area, c, w, h):
        self.on_preview_draw(area, c, w, h, self.application.camera.gray_frame)

    def on_preview_draw3(self, area, c, w, h):
        self.on_preview_draw(area, c, w, h, self.application.camera.thresh_frame)

    def on_preview_draw4(self, area, c, w, h):
        self.on_preview_draw(area, c, w, h, self.application.camera.edge_frame)

    def on_preview_draw(self, area, c, w, h, frame):
        if frame is None:
            return

        pixbuf = frame.get_scaled_pixbuf2(width=w)
        if pixbuf is not None:
            Gdk.cairo_set_source_pixbuf(c, pixbuf, 0, 0)
            c.rectangle(
                0,
                0,
                w,
                h,
            )
            c.fill()
            self.preview_scale = frame.get_width() / w

        c.scale(1 / self.preview_scale, 1 / self.preview_scale)
        self.mark_target(c, frame)
        self.mark_center(c, frame)

    def mark_center(self, c, frame):
        """marks the current center of the camera, i.e. wher a shot would hit"""
        sz = 30
        pos = self.application.target.get_tracker_offset()

        c.set_source_rgb(0.3, 1, 1)
        c.set_line_width(3)
        c.move_to(pos[0] - sz, pos[1])
        c.line_to(pos[0] + sz, pos[1])
        c.move_to(pos[0], pos[1] - sz)
        c.line_to(pos[0], pos[1] + sz)
        c.stroke()

    def mark_target(self, c, frame):
        """mark where the target was located"""
        # getting target
        pos, rad = self.application.camera.get_target()
        col_green = (0, 1, 0.5)
        col_red = (1, 0.5, 0.5)
        if rad is not None and rad > 0:
            frame.draw_circle(c, col_green, pos, rad, width=5)
            frame.draw_circle(
                c, col_red, pos, self.application.camera.target_min_radius, width=5
            )
            frame.draw_circle(
                c, col_red, pos, self.application.camera.target_max_radius, width=5
            )
            self.application.target.set_tracker_source_scale(rad)

    def update_fps(self, fps):
        new_label = f"Refresh: {fps} fps"
        self.cam_status_label.set_label(new_label)

    def on_change_thres(self, range, scroll, value):
        self.application.camera.gray_threshold = value

    def on_change_blur_rad(self, range, scroll, value):
        self.application.camera.blur_radius = ((int(value) + 1) // 2 * 2) - 1

    def on_change_target_rad(self, range, scroll, value):
        print(value)
        self.application.camera.target_min_radius = int(value)
        self.application.camera.target_max_radius = int(value * 2)

    #        self.application.mainloop(None)

    def on_target_pane_resize(self):
        print("target_pane resize!")
        quit()

    # -----------------------------------------------------------------------
    #
    # Callbacks
    #
    # -----------------------------------------------------------------------
    # create a template
    @Gtk.Template.Callback()
    def split_view__toggle_sidebar(self, b):
        print("functoggle osstwindow")
        self.previews_frame.set_visible(not self.previews_frame.get_visible())

    @Gtk.Template.Callback()
    def split_view__toggle_settings(self, b):
        print("functoggle osstwindow")
        self.settings_frame.set_visible(not self.settings_frame.get_visible())

    @Gtk.Template.Callback()
    def trail_style__select(self, b):
        if b.get_active():
            self.application.set_linestyle_curve()
        else:
            self.application.set_linestyle_lines()

    @Gtk.Template.Callback()
    def trail_fade__toggle(self, switch, state):
        self.application.set_target_trail_fade(state)

    @Gtk.Template.Callback()
    def trail_len__chooser(self, b):
        self.application.set_target_trail_len(int(b.get_value()))

    @Gtk.Template.Callback()
    def shot_detect__select(self, b):
        # ToDo: there must be a better way to get that info
        if b.get_label() == "DISAG":
            self.application.use_disag = b.get_active()
        elif b.get_label() == "Mic":
            self.application.use_mic = b.get_active()
