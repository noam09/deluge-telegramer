#
# core.py
#
# Copyright (C) 2016 Noam <noamgit@gmail.com>
# https://github.com/noam09
#
# Much credit to:
# Copyright (C) 2011 Innocenty Enikeew <enikesha@gmail.com>
# https://bitbucket.org/enikesha/deluge-xmppnotify
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
# 	51 Franklin Street, Fifth FloorMarkdown
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

import os
import logging
import traceback
from time import strftime
from deluge.log import LOG as log
###log.setLevel(logging.DEBUG)

def prelog():
    return strftime('%Y-%m-%d %H:%M:%S # Telegramer: ')

if os.name == 'nt':
    """If running on Windows we need to import some modules from
    the local Python installation because Deluge doesn't supply them,
    for that we need to append the appropriate paths to sys.path
    WINDOWS SUPPORT IS STILL IN BETA"""
    try:
        import sys
        import subprocess
        log.info(prelog() + 'Windows detected, trying to append local Python path')
        log.debug(prelog() + 'Current path\n%s' % str(sys.path))
        p = subprocess.Popen('pythonw2 -c "import sys;print sys.path"',
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE)
        output = p.communicate()
        if output:
            j = output[0]
        required_paths = ['site-packages', 'lib', 'python27', 'python26']
        if 'site-packages' in j:
            k = [i[1:-1] for i in j[1:-1].split(', ') if i[1:-1].lower().endswith(tuple(required_paths))]
            if k:
                for pth in k:
                    log.info(prelog() + 'Adding %s to Python path' % pth)
                    sys.path.append(pth.replace('\\\\', '\\'))
                    log.debug(prelog() + 'Current path\n%s' % str(sys.path))
    except Exception as e:
        log.error(prelog() + '%s\n%s' % (str(e), traceback.format_exc()))

try:
    import re
    import requests
    import telebot
    import threading
    from base64 import b64encode
    from time import strftime, sleep
    from string import ascii_letters
    from random import choice, randint
    import deluge.configmanager
    from deluge.ui.client import client
    import deluge.component as component
    from deluge.core.rpcserver import export
    from twisted.internet.task import LoopingCall
    from deluge.plugins.pluginbase import CorePluginBase
    from deluge.common import fsize, fpcnt, fspeed, fpeer, ftime, fdate, is_url, is_magnet
    from twisted.internet import reactor
    from twisted.internet import defer
except ImportError as e:
    log.error(prelog() + 'Import error - %s\n%s' % (str(e), traceback.format_exc()))

DEFAULT_PREFS = {"telegram_token": "Contact @BotFather and create a new bot",
                "telegram_user": "Contact @MyIDbot",
                "telegram_users": "Contact @MyIDbot",
                "telegram_notify_finished": True,
                "telegram_notify_added": True,
                "dir1": "",
                "cat1": "",
                "dir2": "",
                "cat2": "",
                "cat3": "",
                "dir3": ""}

HEADERS = {'User-Agent':
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}

STICKERS = {'lincoln'   : 'BQADBAADGQADyIsGAAE2WnfSWOhfUgI',
            'dali'      : 'BQADBAADHAADyIsGAAFZfq1bphjqlgI',
            'chan'      : 'BQADBAADPQADyIsGAAHaVWyyLugSFAI',
            'marley'    : 'BQADBAADJQADyIsGAAGdzbYn4WkdaAI'}

EMOJI = {'seeding'      : u'\u23eb',
        'queued'        : u'\u23ef',
        'paused'        : u'\u23f8',
        'error'         : u'\u2757\ufe0f',
        'downloading'   : u'\u23ec'}

STRINGS = {'no_label': 'No Label',
            'no_category': 'Use Default Settings',
            'test_success': 'It works!',
            'which_cat': 'Which category?',
            'what_kind': 'What kind?',
            'send_magnet': 'Please send me the magnet link',
            'send_file': 'Please send me the torrent file',
            'send_url': 'Please send me the address',
            'added': 'Added',
            'eta': 'ETA',
            'not_magnet': 'Aw man... That\'s not a magnet link',
            'not_file': 'Aw man... That\'s not a torrent file',
            'not_url': 'Aw man... Bad link',
            'download_fail': 'Aw man... Download failed',
            'no_items': 'No items'}

INFO_DICT = (('queue', lambda i,s: i!=-1 and str(i) or '#'),
             ('state', None),
             ('name', lambda i,s: ' %s *%s* ' % (s['state'] if s['state'].lower() not in EMOJI else EMOJI[s['state'].lower()], i)),
             ('total_wanted', lambda i,s: '(%s) ' % fsize(i)),
             ('progress', lambda i,s: '%s\n' % fpcnt(i/100)),
             ('num_seeds', None),
             ('num_peers', None),
             ('total_seeds', None),
             ('total_peers', lambda i,s: '%s / %s seeds\n' % tuple(map(fpeer,
                                                                   (s['num_seeds'], s['num_peers']),
                                                                   (s['total_seeds'], s['total_peers'])))),
             ('download_payload_rate', None),
             ('upload_payload_rate', lambda i,s: '%s : %s\n' % tuple(map(fspeed, (s['download_payload_rate'], i)))),
             ('eta', lambda i,s: i > 0 and '*ETA:* %s ' % ftime(i) or ''),
             ('time_added', lambda i,s: '*Added:* %s' % fdate(i)))

INFOS = [i[0] for i in INFO_DICT]

try:
    HIDE_KB = telebot.types.ReplyKeyboardRemove()
except:
    HIDE_KB = telebot.types.ReplyKeyboardHide()

def format_torrent_info(torrent):
    status = torrent.get_status(INFOS)
    return ''.join([f(status[i], status) for i, f in INFO_DICT if f is not None])

class Core(CorePluginBase):

    def __init__(self, *args):
        self.core = component.get('Core')
        self.bot = None
        log.debug(prelog() + 'Initialize class')
        super(Core, self).__init__(*args)

    def enable(self):
        try:
            log.info(prelog() + 'Enable')
            self.config = deluge.configmanager.ConfigManager('telegramer.conf', DEFAULT_PREFS)
            self.whitelist = []
            self.set_dirs = {}
            self.label = None
            self.COMMANDS = {'/add'          : self.cmd_add,
                            '/list'         : self.cmd_list,
                            '/down'         : self.cmd_down,
                            '/downloading'  : self.cmd_down,
                            '/up'           : self.cmd_up,
                            '/uploading'    : self.cmd_up,
                            '/seed'         : self.cmd_up,
                            '/seeding'      : self.cmd_up,
                            '/paused'       : self.cmd_paused,
                            '/queued'       : self.cmd_paused,
                            '/?'            : self.cmd_help,
                            '/help'         : self.cmd_help,
                            '/start'        : self.cmd_help,
                            '/reload'       : self.restart_telegramer,
                            '/commands'     : self.cmd_help}

            log.debug(prelog() + 'Initialize bot')
            if self.config['telegram_token'] != DEFAULT_PREFS['telegram_token']:
                self.bot = telebot.TeleBot(self.config['telegram_token'])
                self.bot.set_update_listener(self.telegram_handle_messages)
                if self.config['telegram_user']:
                    telegram_user_list = None
                    self.whitelist.append(str(self.config['telegram_user']))
                    if self.config['telegram_users']:
                        telegram_user_list = filter(None,
                            [x.strip() for x in str(self.config['telegram_users']).split(',')])
                        # Merge with whitelist and remove duplicates - order will be lost
                        self.whitelist = list(set(self.whitelist + telegram_user_list))

                reactor.callLater(2, self.connect_events)
                log.error(prelog() + 'Start thread for polling')
                # Initialize polling thread
                bot_thread = threading.Thread(target=self.telegram_poll_start, args=())
                # Daemonize thread
                bot_thread.daemon = True
                # Start thread
                bot_thread.start()
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def disable(self):
        try:
            log.info(prelog() + 'Disable')
            reactor.callLater(2, self.disconnect_events)
            self.whitelist = []
            self.telegram_poll_stop()
            self.bot = None
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def update(self):
        pass

    def telegram_send(self, message, to=None, parse_mode=None):
        if self.bot:
            log.debug(prelog() + 'Send message')
            if not to:
                to = self.config['telegram_user']
            if parse_mode:
                #return self.bot.send_message(self.config['telegram_user'], message,
                #    parse_mode='Markdown')
                return self.bot.send_message(to, message,
                    parse_mode='Markdown')
            else:
                #return self.bot.send_message(self.config['telegram_user'], message)
                return self.bot.send_message(to, message)
        return

    def telegram_poll_start(self):
        """Like non_stop, this will run forever
        this way suspend/sleep won't kill the thread"""
        while True:
            try:
                if self.bot:
                    log.debug(prelog() + 'Start polling')
                    self.bot.polling()
                    while True:
                        sleep(10)
            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc() + ' - Sleeping...')
                sleep(10)

    def telegram_poll_stop(self):
        try:
            log.debug(prelog() + 'Stop polling')
            # This was in the code but apparently doesn't work
            if self.bot:
                self.bot.stop_polling()
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def telegram_handle_messages(self, messages):
        try:
            log.debug(prelog() + 'Handle messages')
            if messages and self.bot:
                for msg in messages:
                    if str(msg.chat.id) in self.whitelist:
                        try:
                            # Check command
                            if msg.text in self.COMMANDS.keys():
                                self.COMMANDS[str(msg.text)](msg)
                        except Exception as e:
                            log.error(prelog() + str(e) + '\n' + traceback.format_exc())
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def cmd_help(self, msg):
        #since the id is checked in telegram_handle_messages, there should be no need to check every command for valid id
        #if str(msg.chat.id) in self.whitelist:
            help_msg = ['/add - Add a new torrent',
                    '/list - List all torrents',
                    '/down - List downloading torrents',
                    '/up - List uploading torrents',
                    '/paused - List paused torrents',
                    '/help - Show this help message']
            self.telegram_send('\n'.join(help_msg), to=msg.chat.id, parse_mode='Markdown')

    def cmd_list(self, msg):
        #if str(msg.chat.id) in self.whitelist:
            #log.error(self.list_torrents())
            self.telegram_send(self.list_torrents(), to=msg.chat.id, parse_mode='Markdown')

    def cmd_down(self, msg):
        #if str(msg.chat.id) in self.whitelist:
            self.telegram_send(self.list_torrents(lambda t: t.get_status(('state',))['state'] == 'Downloading'),
                to=msg.chat.id, parse_mode='Markdown')

    def cmd_up(self, msg):
        #if str(msg.chat.id) in self.whitelist:
            self.telegram_send(self.list_torrents(lambda t: t.get_status(('state',))['state'] == 'Seeding'),
                to=msg.chat.id, parse_mode='Markdown')

    def cmd_paused(self, msg):
        #if str(msg.chat.id) in self.whitelist:
            self.telegram_send(self.list_torrents(lambda t: t.get_status(('state',))['state']  in ('Paused', 'Queued')),
                to=msg.chat.id, parse_mode='Markdown')

    def cmd_add(self, msg):
        self.set_dirs = {}
        self.opts = {}
        self.label = None
        """Currently there are 3 possible categories so
        loop through cat1-3 and dir1-3, check if directories exist
        """
        for i in xrange(1, 4):
            if os.path.isdir(self.config['dir'+str(i)]):
                self.set_dirs[self.config['cat'+str(i)]] = self.config['dir'+str(i)]
        if self.set_dirs:
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, row_width=3)
            for k in self.set_dirs.keys():
                #markup.row(k)
                markup.add(telebot.types.KeyboardButton(k))
            markup.row(STRINGS['no_category'])
            msg = self.bot.reply_to(msg, STRINGS['which_cat'], reply_markup=markup)
        self.bot.register_next_step_handler(msg, self.process_category)

    def process_category(self, msg):
        if msg.text == '/add' or msg.text == STRINGS['no_category']:
            self.opts = {}
        else:
            for i in xrange(1, 4):
                if self.config['cat'+str(i)] == msg.text:
                        cat_id = str(i)
                        # move_completed_path vs download_location
                        self.opts = {'move_completed_path': self.config['dir'+cat_id],
                            'move_completed': True}

        self.label = None
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, row_width=3)
        component.get('Core').enable_plugin('Label')
        label_plugin = component.get('CorePlugin.Label')
        if label_plugin:
            # Create label if neccessary
            for g in label_plugin.get_labels():
                #markup.row(g)
                markup.add(telebot.types.KeyboardButton(g))
        markup.row(STRINGS['no_label'])
        msg = self.bot.reply_to(msg, 'Which label?', reply_markup=markup)
        self.bot.register_next_step_handler(msg, self.process_label)

    def process_label(self, msg):
        self.label = msg.text
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.row('Magnet', '.torrent', 'URL')
        msg = self.bot.reply_to(msg, STRINGS['what_kind'], reply_markup=markup)
        self.bot.register_next_step_handler(msg, self.process_type)

    def process_type(self, msg):
        if str(msg.chat.id) in self.whitelist:
            try:
                msg_chat_id = str(msg.chat.id)
                if msg.text == 'Magnet':
                    msg = self.bot.reply_to(msg, STRINGS['send_magnet'])
                    self.bot.register_next_step_handler(msg, self.process_magnet)
                elif msg.text == '.torrent':
                    msg = self.bot.reply_to(msg, STRINGS['send_file'])
                    self.bot.register_next_step_handler(msg, self.process_torrent)
                elif msg.text == 'URL':
                    msg = self.bot.reply_to(msg, STRINGS['send_url'])
                    self.bot.register_next_step_handler(msg, self.process_url)
            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def process_magnet(self, msg):
        if str(msg.chat.id) in self.whitelist:
            try:
                #options = None
                metainfo = msg.text
                """Adds a torrent with the given options.
                metainfo could either be base64 torrent data or a magnet link.
                Available options are listed in deluge.core.torrent.TorrentOptions.
                """
                if self.opts is None:
                    self.opts = {}
                if is_magnet(metainfo):
                    log.info(prelog() + 'Adding torrent from magnet URI `%s` using options `%s` ...', metainfo, self.opts)
                    tid = self.core.add_torrent_magnet(metainfo, self.opts)
                    self.apply_label(tid)
                else:
                    self.bot.reply_to(msg, STRINGS['not_magnet'])
            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def process_torrent(self, msg):
        if str(msg.chat.id) in self.whitelist:
            try:
                #options = None
                if msg.document.mime_type == 'application/x-bittorrent':
                    # Get file info
                    file_info = self.bot.get_file(msg.document.file_id)
                    # Download file
                    file = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(self.config['telegram_token'],
                        file_info.file_path))
                    if file.status_code == requests.codes.ok:
                        # Base64 encode file data
                        metainfo = b64encode(file.content)
                        if self.opts is None:
                            self.opts = {}
                        log.info(prelog() + 'Adding torrent from base64 string using options `%s` ...', self.opts)
                        tid = self.core.add_torrent_file(None, metainfo, self.opts)
                        self.apply_label(tid)
                    else:
                        self.bot.reply_to(msg, STRINGS['download_fail'])
                else:
                    self.bot.reply_to(msg, STRINGS['not_file'])
            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def process_url(self, msg):
        if str(msg.chat.id) in self.whitelist:
            try:
                #options = None
                if is_url(msg.text):
                    # Download file
                    file = requests.get(msg.text, headers=HEADERS, verify=False)
                    if file.status_code == requests.codes.ok:
                        # Base64 encode file data
                        metainfo = b64encode(file.content)
                        if self.opts is None:
                            self.opts = {}
                        log.info(prelog() + 'Adding torrent from base64 string using options `%s` ...', self.opts)
                        tid = self.core.add_torrent_file(None, metainfo, self.opts)
                        self.apply_label(tid)
                    else:
                        self.bot.reply_to(msg, STRINGS['download_fail'])
                else:
                    self.bot.reply_to(msg, STRINGS['not_url'])
            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.print_exc())

    def apply_label(self, tid):
        if self.label is not None and self.label != STRINGS['no_label']:
            # Enable Label plugin
            component.get('Core').enable_plugin('Label')
            label_plugin = component.get('CorePlugin.Label')
            if label_plugin:
                # Add label if neccessary
                if self.label not in label_plugin.get_labels():
                    label_plugin.add(self.label.lower())
                    label_plugin.set_torrent(tid, self.label.lower())
                    log.info(prelog() + 'Set label %s to torrent %s' % (self.label.lower(), tid))

    def update_stats(self):
        log.debug('update_stats')

    def connect_events(self):
        event_manager = component.get('EventManager')
        event_manager.register_event_handler('TorrentFinishedEvent', self.on_torrent_finished)
        event_manager.register_event_handler('TorrentAddedEvent', self.on_torrent_added)

    def disconnect_events(self):
        event_manager = component.get('EventManager')
        event_manager.deregister_event_handler('TorrentFinishedEvent', self.on_torrent_finished)
        event_manager.deregister_event_handler('TorrentAddedEvent', self.on_torrent_added)

    def on_torrent_added(self, torrent_id):
        if (self.config['telegram_notify_added'] == False):
            return
        try:
            #torrent_id = str(alert.handle.info_hash())
            torrent = component.get('TorrentManager')[torrent_id]
            torrent_status = torrent.get_status({})
            message = _('Added Torrent *%(name)s*') % torrent_status
            log.info(prelog() + 'Sending torrent added message')
            return self.telegram_send(message, parse_mode='Markdown')
        except Exception, e:
            log.error('error in alert %s' % e)

    def on_torrent_finished(self, torrent_id):
        try:
            if (self.config['telegram_notify_finished'] == False):
                return
            #torrent_id = str(alert.handle.info_hash())
            torrent = component.get('TorrentManager')[torrent_id]
            torrent_status = torrent.get_status({})
            message = _('Finished Downloading *%(name)s*') % torrent_status
            log.info(prelog() + 'Sending torrent finished message')
            return self.telegram_send(message, parse_mode='Markdown')
        except Exception, e:
            log.error(prelog() + 'Error in alert %s' % str(e) + '\n' + traceback.format_exc())

    def list_torrents(self, filter=lambda _:True):
        return '\n'.join([format_torrent_info(t) for t
            in component.get('TorrentManager').torrents.values()
            if filter(t)] or [STRINGS['no_items']])

    @export
    def set_config(self, config):
        """Sets the config dictionary"""
        log.debug(prelog() + 'Set config')
        dirty = False
        for key in config.keys():
            if self.config[key] != config[key]:
                dirty = True
                self.config[key] = config[key]
        if dirty:
            log.info(prelog() + 'Config changed, reloading')
            self.config.save()
            # Restart bot service
            self.disable()
            self.enable()

    @export
    def restart_telegramer(self):
        """Disable and enable plugin"""
        log.info(prelog() + 'Restarting Telegramer plugin')
        self.disable()
        self.enable()

    @export
    def get_config(self):
        """Returns the config dictionary"""
        log.debug(prelog() + 'Get config')
        return self.config.config

    @export
    def telegram_do_test(self):
        """Sends Telegram test message"""
        log.info(prelog() + 'Send test')
        self.bot.send_sticker(self.config['telegram_user'],
            choice(list(STICKERS.values())))
        self.telegram_send(STRINGS['test_success'])
