# main.py
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

import sys
import gi
import sys

from datetime import datetime
from timeit import default_timer as timer

TIMEOUT_MS = 50

TRAIL_DURATION = 10

# ------- Exit handling
EXIT_SUCCESS = 0
EXIT_NO_CAMERA = 1
EXIT_MSG = [None, "Cannot read from Camera. Camera ID ok?"]


# https://lazka.github.io/pgi-docs/#Template-1.0/classes.html
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio, Adw, GLib
from windows.mainwin import OsstWindow

from classes.target import *
from classes.shots import Shot, Shots
from classes import disag
from classes import camera


def toggle_sidebar(b):
    print("functoggle")


class OsstApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(
            application_id="com.github.jest0r.osst",
            # s            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.create_action("quit", lambda *_: self.quit(), ["<primary>q"])
        self.create_action("about", self.on_about_action)
        self.create_action("show-help-overlay", self.on_help_action)
        self.create_action("preferences", self.on_preferences_action)

        # self.create_handler('toggle_sidebar', self.toggle_sidebar)
        self.target = Target(800, DISKTYPE_LG, TRAIL_DURATION, 30)

        self.connect("activate", self.on_activate)

        self.win = None

        self.preview_skip = 0

        self.status_messages = []
        self.status_message_max_len = 5

        # init default camera
        self.camera = camera.Camera()

        self.cams_info = camera.get_devices()

        # get available cameras
        if self.cams_info is False:
            print("No Camera detected, exitting")
            sys.exit(1)

        self.framecount = 0
        self.fps = 0
        self.starttime = datetime.now()

        self.use_disag = False
        self.use_mic = False

        # start disag UDP broadcast listener
        self.disag_server = disag.DisagServer()
        self.disag_server.listen()

    def toggle_sidebar(self, b):
        print("toggle app")
        self.split_view.set_collapsed(not self.split_view.get_collapsed())

    def set_webcam(self, cam_name, cam_id):
        print(f"select webcam {cam_name} - {cam_id}")
        if self.camera is not None:
            self.camera.quit()
        self.camera = camera.Camera(cam_name, cam_id)

        # set frame center as default offset
        fs = self.camera.get_crop_size()
        self.target.set_tracker_source_offset([fs[0] // 2, fs[1] // 2])
        # self.target.set_tracker_source_offset([fs[1] // 2, fs[0] // 2])

    def add_status(self, status_msg):
        self.status_messages.append(status_msg)
        if len(self.status_messages) > self.status_message_max_len:
            self.status_messages.pop(0)
        msg = "\n".join(self.status_messages)

    #        self.win.update_status_messages(msg)

    def set_target_type(self, b):
        if b.get_active() is True:
            print(f"set target to LP")
            self.target.set_disk_type(DISKTYPE_LP)
        else:
            print(f"set target to LG")
            self.target.set_disk_type(DISKTYPE_LG)
        self.win.target_surf.queue_draw()

    def on_activate(self, app):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        # win = self.props.active_window
        # if not win:
        #     win = OsstWindow(application=self)

        self.win = OsstWindow(application=app)
        # win.maximize()

        # self.win.set_draw_func(self.draw)

        self.win.target_surf.set_draw_func(self.target.draw)
        self.win.preview1_surf.set_draw_func(self.win.on_preview_draw1)
        self.win.preview2_surf.set_draw_func(self.win.on_preview_draw2)
        self.win.preview3_surf.set_draw_func(self.win.on_preview_draw3)
        self.win.preview4_surf.set_draw_func(self.win.on_preview_draw4)

        self.win.set_zoom_func(self.target.zoom)
        self.win.set_drag_funcs(self.target.on_drag_start, self.target.on_drag)
        self.win.set_offset_func(self.target.set_tracker_source_offset)

        self.win.set_cam_list(self.cams_info)

        self.win.present()

        GLib.timeout_add(20, self.mainloop, None, priority=GLib.PRIORITY_HIGH)

    def prep_exit(self, retval=0):
        """exit mainloop with certain return value and message"""
        self.disag_server.end()
        self.camera.quit()
        if retval > 0:
            print(f"ERROR: {EXIT_MSG[retval]}")
        sys.exit(retval)

    def mainloop(self, data):
        # set sleep timer for next mainloop call
        sleep = int(1000 / self.camera.get_fps())

        # read camera
        t_start = timer()
        cam_read_success = self.camera.read()
        dur1 = timer()

        # update fps counter
        self._update_fps()

        if not cam_read_success:
            self.prep_exit(EXIT_NO_CAMERA)

        if self.use_mic and self.camera.detect_shot_triggered():
            print("Shot detected by camera!")
        if self.use_disag and self.disag_server.data_received():
            d = self.disag_server.get_data()
            print("Disag server found shot")
            shot = Shot(d, json=True)
            self.target.add_shot(shot)
            x,y = shot.pos()
            print(shot.pos())

        circle_found = self.camera.detect_circles()
        # if there is a circle, record the target position
        if circle_found:
            self.target.add_position(self.camera.target_pos)
        dur2 = timer()

        duration = (timer() - t_start) * 1000
        wait_time = sleep - duration - 5  # 5ms extra for fluctuatoins in read time
        GLib.timeout_add(
            max(5, wait_time), self.mainloop, None, priority=GLib.PRIORITY_HIGH
        )
        #        GLib.timeout_add(5, self.mainloop, None)

        # queue a draw. this should be the last thing to do
        # if we are late in the cycle, skip the draw

        # only give debug output ever xth time
        self.preview_skip = (self.preview_skip + 1) % 5

        # still try to draw the target at every frame
        # that might not work
        self.win.target_surf.queue_draw()

        if self.preview_skip != 0:
            return False

        # only preview every 5th frame
        self.win.preview1_surf.queue_draw()
        self.win.preview2_surf.queue_draw()
        self.win.preview3_surf.queue_draw()
        self.win.preview4_surf.queue_draw()

        disp_t = int((timer() - dur2) * 1000)
        detect_t = int((dur2 - dur1) * 1000)
        read_t = int((dur1 - t_start) * 1000)
        total_t = int((timer() - t_start) * 1000)

        # print(
        #     f"max ms for 30fps: {sleep}. read: {read_t}, detect: {detect_t}, disp: {disp_t} total: {total_t} -> next call in {int(wait_time)}"
        # )

        # return false to reset the regular timeout
        return False

    def _update_fps(self):
        self.framecount += 1
        if (datetime.now() - self.starttime).total_seconds() >= 1:
            # fps
            self.starttime = datetime.now()
            self.fps = self.framecount
            self.framecount = 0
            self.win.update_fps(self.fps)
            # circle detection vs fails
            # self.circle_success_per_second = detected_counter
            # detected_counter = 0
            # self.circle_fails_per_second = fail_counter
            # fail_counter = 0

    def on_help_action(self, widget, _):
        print("help")

    def on_about_action(self, widget, _):
        """Callback for the app.about action."""
        about = Gtk.AboutDialog()
        about.set_authors(["Helmut M"])
        about.set_program_name("Open Sports Shooting Tracker")
        about.set_comments("Track and analyze your targetting movements")
        about.set_version("0.0.3 dev")
        about.set_wrap_license("GPL 3")
        about.set_website("https://github.com/Jest0r/osst")
        about.set_website_label("OSST on Github")
        about.present()

    def on_preferences_action(self, widget, _):
        """Callback for the app.preferences action."""
        print("app.preferences action activated")

    def reset_target(self):
        self.camera.target_pos = None
        print("Resetting Target Pos")

    def set_linestyle_curve(self):
        self.target.set_line_style(LINESTYLE_CURVE)

    def set_linestyle_lines(self):
        self.target.set_line_style(LINESTYLE_LINES)

    def set_target_trail_fade(self, state):
        self.target.set_trail_fade(state)

    def set_target_trail_len(self, seconds):
        self.target.set_trail_len(seconds)

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    """The application's entry point."""
    app = OsstApplication()
    app.run(sys.argv)
    print("exit")


if __name__ == "__main__":
    main(0)
