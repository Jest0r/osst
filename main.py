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

# https://lazka.github.io/pgi-docs/#Template-1.0/classes.html
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1.4")

from gi.repository import Gtk, Gio, Adw
from windows.mainwin import OsstWindow


def toggle_sidebar(b):
    print("functoggle")


class OsstApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(
            application_id="com.github.jest0r.osst",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.create_action("quit", lambda *_: self.quit(), ["<primary>q"])
        self.create_action("about", self.on_about_action)
        self.create_action("show-help-overlay", self.on_help_action)
        self.create_action("preferences", self.on_preferences_action)
        # self.create_handler('toggle_sidebar', self.toggle_sidebar)

    def toggle_sidebar(self, b):
        print("toggle app")
        self.split_view.set_collapsed(not self.split_view.get_collapsed())

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            win = OsstWindow(application=self)
        win.present()

    def on_help_action(self, widget, _):
        print("help")

    def on_about_action(self, widget, _):
        """Callback for the app.about action."""
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name="Open Sport Shooting Tracker",
            application_icon="com.github.jest0r.osst",
            developer_name="Helmut M",
            version="0.0.1 dev",
            developers=["Helmut M"],
            copyright="© 2023 Helmut M",
        )
        about.present()

    def on_preferences_action(self, widget, _):
        """Callback for the app.preferences action."""
        print("app.preferences action activated")

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


#    def create_handler(self, name, callback):
#        handler = GTK.Builder.bonnect_signa


def main(version):
    """The application's entry point."""
    app = OsstApplication()
    app.run(sys.argv)
    print("exit")


if __name__ == "__main__":
    main(0)
