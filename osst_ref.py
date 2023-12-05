#!@PYTHON@

# osst_ref.in
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

import os
import sys
import signal
import locale
import gettext

#VERSION = '@VERSION@'
VERSION = '0.0.2'
pkgdatadir = 'windows'
#localedir = '@localedir@'

sys.path.insert(1, pkgdatadir)
signal.signal(signal.SIGINT, signal.SIG_DFL)
#locale.bindtextdomain('osst_ref', localedir)
#locale.textdomain('osst_ref')
#gettext.install('osst_ref', localedir)

if __name__ == '__main__':
    import gi

#    from gi.repository import Gio
#    resource = Gio.Resource.load(os.path.join(pkgdatadir, 'osst_ref.gresource.xml'))
#    resource._register()

    from osst_ref import main
    sys.exit(main.main(VERSION))
