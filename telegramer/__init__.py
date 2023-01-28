#
# __init__.py
#
# Copyright (C) 2016-2019 Noam <noamgit@gmail.com>
# https://github.com/noam09
#
# Package inclusion method thanks to YaRSS2 developers
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
# Copyright (C) 2009 Camillo Dell'mour <cdellmour@gmail.com>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#

import sys
from deluge.log import LOG as log

import pkg_resources
from deluge.plugins.init import PluginInitBase


def load_libs():
    egg = pkg_resources.require("Telegramer")[0]
    for name in egg.get_entry_map("telegramer.libpaths"):
        ep = egg.get_entry_info("telegramer.libpaths", name)
        location = "%s/%s" % (egg.location, ep.module_name.replace(".", "/"))
        if location not in sys.path:
            sys.path.append(location)
        log.error("NOTANERROR: Appending to sys.path: '%s'" % location)


class CorePlugin(PluginInitBase):
    def __init__(self, plugin_name):
        load_libs()
        from .core import Core as _plugin_cls
        self._plugin_cls = _plugin_cls
        super(CorePlugin, self).__init__(plugin_name)


class GtkUIPlugin(PluginInitBase):
    def __init__(self, plugin_name):
        load_libs()
        from .gtkui import GtkUI as _plugin_cls
        self._plugin_cls = _plugin_cls
        super(GtkUIPlugin, self).__init__(plugin_name)


class WebUIPlugin(PluginInitBase):
    def __init__(self, plugin_name):
        load_libs()
        from .webui import WebUI as _plugin_cls
        self._plugin_cls = _plugin_cls
        super(WebUIPlugin, self).__init__(plugin_name)


class Gtk3UIPlugin(PluginInitBase):
    def __init__(self, plugin_name):
        load_libs()
        from .gtk3ui import Gtk3UI as GtkUIPluginClass
        self._plugin_cls = GtkUIPluginClass
        super(Gtk3UIPlugin, self).__init__(plugin_name)


