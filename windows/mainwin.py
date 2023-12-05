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

from gi.repository import Adw
from gi.repository import Gtk

def toggle_sidebar(b):
    print("functoggle")

@Gtk.Template(filename='windows/mainwin.ui')
class OsstWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'OsstWindow'

    # 'read' the object from the xml template
    split_view = Gtk.Template.Child("split_view")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # create a template 
    @Gtk.Template.Callback()
    def split_view__toggle_sidebar(self, b):
        print("functoggle osstwindow")
        self.split_view.set_collapsed(not self.split_view.get_collapsed())
