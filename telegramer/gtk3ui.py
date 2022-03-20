#
# gtkui.py
#
# Copyright (C) 2016-2019 Noam <noamgit@gmail.com>
# https://github.com/noam09
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


try:
    from deluge.log import LOG as log
except Exception as e:
    print('Telegramer: Exception - %s' % str(e))

try:
    from gi.repository import Gtk
    import deluge.common
    from .common import get_resource
    from deluge.ui.client import client
    import deluge.component as component
    from deluge.plugins.pluginbase import Gtk3PluginBase
except ImportError as e:
    log.error('Telegramer: Import error - %s', str(e))

REGEX_SUBS_WORD = "NAME"


class Gtk3UI(Gtk3PluginBase):
    def enable(self):
        self.builder = Gtk.Builder.new_from_file(get_resource("config.ui"))
        self.builder.connect_signals({
            "on_button_test_clicked": self.on_button_test_clicked,
            "on_button_save_clicked": self.on_button_save_clicked,
            "on_button_reload_clicked": self.on_button_reload_clicked
        })
        component.get("Preferences").add_page("Telegramer", self.builder.get_object("prefs_box"))
        component.get("PluginManager").register_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").register_hook("on_show_prefs", self.on_show_prefs)

    def disable(self):
        component.get("Preferences").remove_page("Telegramer")
        component.get("PluginManager").deregister_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").deregister_hook("on_show_prefs", self.on_show_prefs)

    def on_apply_prefs(self):
        log.debug("Telegramer: applying prefs for Telegramer")
        config = {
            "telegram_notify_added": self.builder.get_object("telegram_notify_added").get_active(),
            "telegram_notify_finished": self.builder.get_object("telegram_notify_finished").get_active(),
            "telegram_token": self.builder.get_object("telegram_token").get_text(),
            "telegram_user": self.builder.get_object("telegram_user").get_text(),
            "telegram_users": self.builder.get_object("telegram_users").get_text(),
            "telegram_users_notify": self.builder.get_object("telegram_users_notify").get_text(),
            "minimum_speed": self.builder.get_object("minimum_speed").get_text(),
            "user_timer": self.builder.get_object("user_timer").get_text(),
            "proxy_url": self.builder.get_object("proxy_url").get_text(),
            "urllib3_proxy_kwargs_username": self.builder.get_object("urllib3_proxy_kwargs_username").get_text(),
            "urllib3_proxy_kwargs_password": self.builder.get_object("urllib3_proxy_kwargs_password").get_text(),
            "categories": {self.builder.get_object("cat1").get_text():
                           self.builder.get_object("dir1").get_text(),
                           self.builder.get_object("cat2").get_text():
                           self.builder.get_object("dir2").get_text(),
                           self.builder.get_object("cat3").get_text():
                           self.builder.get_object("dir3").get_text()
                           },
            "regex_exp": {self.builder.get_object("rname1").get_text():
                          self.builder.get_object("reg1").get_text(),
                          self.builder.get_object("rname2").get_text():
                          self.builder.get_object("reg2").get_text(),
                          self.builder.get_object("rname3").get_text():
                          self.builder.get_object("reg3").get_text()
                          }
            }

        client.telegramer.set_config(config)
        for ind, (n, r) in enumerate(config["regex_exp"].items()):
            if REGEX_SUBS_WORD not in r:
                log.error("Your regex " + n + " template does not contain the "
                          + REGEX_SUBS_WORD + " keyword")
                break

    def on_show_prefs(self):
        client.telegramer.get_config().addCallback(self.cb_get_config)

    def cb_get_config(self, config):
        "callback for on show_prefs"
        self.builder.get_object("telegram_notify_added").set_active(config["telegram_notify_added"])
        self.builder.get_object("telegram_notify_finished").set_active(config["telegram_notify_finished"])
        self.builder.get_object("telegram_token").set_text(config["telegram_token"])
        self.builder.get_object("telegram_user").set_text(config["telegram_user"])
        self.builder.get_object("telegram_users").set_text(config["telegram_users"])
        self.builder.get_object("telegram_users_notify").set_text(config["telegram_users_notify"])
        # Slow
        self.builder.get_object("minimum_speed").set_text(str(config["minimum_speed"]))
        self.builder.get_object("user_timer").set_text(str(config["user_timer"]))
        # Proxy
        self.builder.get_object("proxy_url").set_text(config["proxy_url"]),
        self.builder.get_object('urllib3_proxy_kwargs_username').set_text(config["urllib3_proxy_kwargs_username"]),
        self.builder.get_object("urllib3_proxy_kwargs_password").set_text(config["urllib3_proxy_kwargs_password"]),
        # Categories
        for ind, (c, d) in enumerate(config["categories"].items()):
            self.builder.get_object("cat"+str(ind+1)).set_text(c)
            self.builder.get_object("dir"+str(ind+1)).set_text(d)
        # RSS
        for ind, (n, r) in enumerate(config["regex_exp"].items()):
            self.builder.get_object("rname"+str(ind+1)).set_text(n)
            self.builder.get_object("reg"+str(ind+1)).set_text(r)

    def on_button_test_clicked(self, Event=None):
        client.telegramer.telegram_do_test()

    def on_button_save_clicked(self, Event=None):
        self.on_apply_prefs()

    def on_button_reload_clicked(self, Event=None):
        client.telegramer.restart_telegramer()
