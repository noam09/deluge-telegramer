#
# core.py
#
# Copyright (C) 2016-2017 Noam <noamgit@gmail.com>
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

#############################
# log.setLevel(logging.DEBUG)
#############################

def prelog():
    return strftime('%Y-%m-%d %H:%M:%S # Telegramer: ')

try:
    import re
    import urllib2
    from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot)
    from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                              ConversationHandler)
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

CATEGORY, SET_LABEL, TORRENT_TYPE, ADD_MAGNET, ADD_TORRENT, ADD_URL = range(6)

DEFAULT_PREFS = {"telegram_token": "Contact @BotFather and create a new bot",
                "telegram_user": "Contact @MyIDbot",
                "telegram_users": "Contact @MyIDbot",
                "telegram_notify_finished": True,
                "telegram_notify_added": True,
                "dir1": "",
                "cat1": "",
                "dir2": "",
                "cat2": "",
                "dir3": "",
                "cat3": ""}

HEADERS = {'User-Agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'}

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
            'cancel': 'Send /cancel at any time to abort',
            'test_success': 'It works!',
            'which_cat': 'Which category/directory?\nRemember to quote directory paths ("/path/to/dir")',
            'which_label': 'Which label?',
            'what_kind': 'What kind?',
            'send_magnet': 'Please send me the magnet link',
            'send_file': 'Please send me the torrent file',
            'send_url': 'Please send me the address',
            'added': 'Added',
            'eta': 'ETA',
            'error': 'Error',
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

def format_torrent_info(torrent):
    status = torrent.get_status(INFOS)
    return ''.join([f(status[i], status) for i, f in INFO_DICT if f is not None])

class Core(CorePluginBase):
    def __init__(self, *args):
        self.core = component.get('Core')
        self.bot = None
        self.updater = None
        log.debug(prelog() + 'Initialize class')
        super(Core, self).__init__(*args)


    def enable(self):

        try:
            log.info(prelog() + 'Enable')
            self.config = deluge.configmanager.ConfigManager('telegramer.conf', DEFAULT_PREFS)
            self.whitelist = []
            self.set_dirs = {}
            self.label = None
            self.COMMANDS = { 'list'         : self.cmd_list,
                            'down'         : self.cmd_down,
                            'downloading'  : self.cmd_down,
                            'up'           : self.cmd_up,
                            'uploading'    : self.cmd_up,
                            'seed'         : self.cmd_up,
                            'seeding'      : self.cmd_up,
                            'paused'       : self.cmd_paused,
                            'queued'       : self.cmd_paused,
                            '?'            : self.cmd_help,
                            'help'         : self.cmd_help,
                            'start'        : self.cmd_help,
                            'reload'       : self.restart_telegramer,
                            'commands'     : self.cmd_help}

            log.debug(prelog() + 'Initialize bot')

            if self.config['telegram_token'] != DEFAULT_PREFS['telegram_token']:
                if self.config['telegram_user']:
                    telegram_user_list = None
                    self.whitelist.append(str(self.config['telegram_user']))
                    if self.config['telegram_users']:
                        telegram_user_list = filter(None,
                            [x.strip() for x in str(self.config['telegram_users']).split(',')])
                        # Merge with whitelist and remove duplicates - order will be lost
                        self.whitelist = list(set(self.whitelist + telegram_user_list))
                        log.debug(prelog() + str(self.whitelist))

                reactor.callLater(2, self.connect_events)

                self.bot = Bot(self.config['telegram_token'])
                # Create the EventHandler and pass it bot's token.
                self.updater = Updater(self.config['telegram_token'])
                # Get the dispatcher to register handlers
                dp = self.updater.dispatcher
                # Add conversation handler with the different states
                conv_handler = ConversationHandler(
                    entry_points=[CommandHandler('add', self.add)],
                    states={
                        CATEGORY: [MessageHandler(Filters.text, self.category)],
                        SET_LABEL: [MessageHandler(Filters.text, self.set_label)],
                        TORRENT_TYPE: [MessageHandler(Filters.text, self.torrent_type)],
                        ADD_MAGNET: [MessageHandler(Filters.text, self.add_magnet)],
                        ADD_TORRENT: [MessageHandler(Filters.document, self.add_torrent)],
                        ADD_URL: [MessageHandler(Filters.text, self.add_url)]
                    },
                    fallbacks=[CommandHandler('cancel', self.cancel)]
                )

                dp.add_handler(conv_handler)

                for key, value in self.COMMANDS.iteritems():
                    dp.add_handler(CommandHandler(key, value))

                # Log all errors
                dp.add_error_handler(self.error)
                # Start the Bot
                self.updater.start_polling(poll_interval=0.05)

        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())


    def error(self, bot, update, error):
        logger.warn('Update "%s" caused error "%s"' % (update, error))


    def disable(self):
        try:
            log.info(prelog() + 'Disable')
            reactor.callLater(2, self.disconnect_events)
            self.whitelist = []
            self.telegram_poll_stop()
            #self.bot = None
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())


    def update(self):
        pass


    def telegram_send(self, message, to=None, parse_mode=None):
        if 1:#str(update.message.chat.id) in self.whitelist:
            if self.bot:
                log.debug(prelog() + 'Send message')
                if not to:
                    to = self.config['telegram_user']
                if parse_mode:
                    return self.bot.send_message(to, message,
                        parse_mode='Markdown')
                else:
                    return self.bot.send_message(to, message)
            return


    def telegram_poll_start(self):
        """Like non_stop, this will run forever
        this way suspend/sleep won't kill the thread"""
        pass


    def telegram_poll_stop(self):
        try:
            log.debug(prelog() + 'Stop polling')
            if self.updater:
                self.updater.stop()
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())


    def cancel(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            log.info("User %s canceled the conversation." % str(update.message.chat.id))
            update.message.reply_text('Operation cancelled',
                                      reply_markup=ReplyKeyboardRemove())

            return ConversationHandler.END


    def cmd_help(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            help_msg = ['/add - Add a new torrent',
                    '/list - List all torrents',
                    '/down - List downloading torrents',
                    '/up - List uploading torrents',
                    '/paused - List paused torrents',
                    '/help - Show this help message']
            self.telegram_send('\n'.join(help_msg), to=update.message.chat.id, parse_mode='Markdown')


    def cmd_list(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            #log.error(self.list_torrents())
            self.telegram_send(self.list_torrents(), to=update.message.chat.id, parse_mode='Markdown')


    def cmd_down(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            self.telegram_send(self.list_torrents(lambda t: t.get_status(('state',))['state'] == 'Downloading'),
                to=update.message.chat.id, parse_mode='Markdown')


    def cmd_up(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            self.telegram_send(self.list_torrents(lambda t: t.get_status(('state',))['state'] == 'Seeding'),
                to=update.message.chat.id, parse_mode='Markdown')


    def cmd_paused(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            self.telegram_send(self.list_torrents(lambda t: t.get_status(('state',))['state']  in ('Paused', 'Queued')),
                to=update.message.chat.id, parse_mode='Markdown')


    def add(self, bot, update):
        #log.error(type(update.message.chat.id) + str(update.message.chat.id))
        if str(update.message.chat.id) in self.whitelist:
            try:
                self.set_dirs = {}
                self.opts = {}
                keyboard_options = []
                """Currently there are 3 possible categories so
                loop through cat1-3 and dir1-3, check if directories exist
                """
                for i in range(3):
                    i = i+1
                    if os.path.isdir(self.config['dir'+str(i)]):
                        log.debug(prelog() + self.config['cat'+str(i)] + ' ' + self.config['dir'+str(i)])
                        self.set_dirs[self.config['cat'+str(i)]] = self.config['dir'+str(i)]

                if self.set_dirs:
                    for k in self.set_dirs.keys():
                        log.debug(prelog() + k)
                        keyboard_options.append([k])
                keyboard_options.append([STRINGS['no_category']])

                update.message.reply_text(
                    '%s\n%s' % (STRINGS['which_cat'], STRINGS['cancel']),
                    reply_markup=ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True))

                return CATEGORY

            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())


    def category(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            try:
                if update.message.text == '/add' or update.message.text == STRINGS['no_category']:
                    self.opts = {}
                else:
                    for i in range(3):
                        i = i+1
                        if self.config['cat'+str(i)] == update.message.text:
                            cat_id = str(i)
                            # move_completed_path vs download_location
                            self.opts = {'move_completed_path': self.config['dir'+cat_id],
                                'move_completed': True}
                    # If none of the existing categories were selected, maybe user is trying to
                    # save to a new directory
                    if not self.opts:
                        try:
                            log.debug(prelog() + 'Custom directory entered: ' + str(update.message.text))
                            if update.message.text[0] == '"' and update.message.text[-1] == '"':
                                otherpath = os.path.abspath(os.path.realpath(update.message.text[1:-1]))
                                log.debug(prelog() + 'Attempting to create and save to: ' + str(otherpath))
                                if not os.path.exists(otherpath):
                                    os.makedirs(otherpath)
                                self.opts = {'move_completed_path': otherpath,
                                    'move_completed': True}
                        except Exception as e:
                            log.error(prelog() + str(e) + '\n' + traceback.format_exc())

                keyboard_options = []
                self.label = None
                try:
                    component.get('Core').enable_plugin('Label')
                    label_plugin = component.get('CorePlugin.Label')
                    if label_plugin:
                        # Create label if neccessary
                        for g in label_plugin.get_labels():
                            keyboard_options.append([g])
                except Exception as e:
                    log.debug(prelog() + 'Enabling Label plugin failed')
                    log.error(prelog() + str(e) + '\n' + traceback.format_exc())
                keyboard_options.append([STRINGS['no_label']])

                update.message.reply_text(
                    STRINGS['which_label'],
                    reply_markup=ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True))

                return SET_LABEL

            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())


    def set_label(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            try:
                user = update.message.chat.id

                self.label = update.message.text
                log.debug(prelog() + "Label: %s" % (update.message.text))

                # Request torrent type
                keyboard_options = []
                keyboard_options.append(['Magnet'])
                keyboard_options.append(['.torrent'])
                keyboard_options.append(['URL'])

                update.message.reply_text(
                    STRINGS['what_kind'],
                    reply_markup=ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True))

                return TORRENT_TYPE

            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())


    def torrent_type(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            try:
                user = update.message.chat.id
                torrent_type_selected = update.message.text

                if torrent_type_selected == 'Magnet':
                    update.message.reply_text(STRINGS['send_magnet'])
                    return ADD_MAGNET

                elif torrent_type_selected == '.torrent':
                    update.message.reply_text(STRINGS['send_file'])
                    return ADD_TORRENT

                elif torrent_type_selected == 'URL':
                    update.message.reply_text(STRINGS['send_url'])
                    return ADD_URL

                else:
                    update.message.reply_text(STRINGS['error'],
                        reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END

            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())


    def add_magnet(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            try:
                user = update.message.chat.id
                log.debug("addmagnet of %s: %s" % (str(user), update.message.text))

                try:
                    #options = None
                    metainfo = update.message.text
                    """Adds a torrent with the given options.
                    metainfo could either be base64 torrent data or a magnet link.
                    Available options are listed in deluge.core.torrent.TorrentOptions.
                    """
                    if self.opts is None:
                        self.opts = {}
                    if is_magnet(metainfo):
                        log.debug(prelog() + 'Adding torrent from magnet URI `%s` using options `%s` ...', metainfo, self.opts)
                        tid = self.core.add_torrent_magnet(metainfo, self.opts)
                        self.apply_label(tid)
                    else:
                        update.message.reply_text(STRINGS['not_magnet'],
                            reply_markup=ReplyKeyboardRemove())
                except Exception as e:
                    log.error(prelog() + str(e) + '\n' + traceback.format_exc())

                return ConversationHandler.END

            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())


    def add_torrent(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            try:
                user = update.message.chat.id
                log.debug("addtorrent of %s: %s" % (str(user), update.message.document))

                if update.message.document.mime_type == 'application/x-bittorrent':
                    # Get file info
                    file_info = self.bot.getFile(update.message.document.file_id)
                    # Download file
                    request = urllib2.Request(file_info.file_path, headers=HEADERS)
                    status_code = urllib2.urlopen(request).getcode()
                    if status_code == 200:
                        file_contents = urllib2.urlopen(request).read()
                        # Base64 encode file data
                        metainfo = b64encode(file_contents)
                        if self.opts is None:
                            self.opts = {}
                        log.info(prelog() + 'Adding torrent from base64 string using options `%s` ...', self.opts)
                        tid = self.core.add_torrent_file(None, metainfo, self.opts)
                        self.apply_label(tid)
                    else:
                        update.message.reply_text(STRINGS['download_fail'],
                            reply_markup=ReplyKeyboardRemove())
                else:
                    update.message.reply_text(STRINGS['not_file'],
                        reply_markup=ReplyKeyboardRemove())

                return ConversationHandler.END

            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())


    def add_url(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            try:
                user = update.message.chat.id
                log.debug("addurl of %s: %s" % (str(user), update.message.text))

                if is_url(update.message.text):
                    try:
                        # Download file
                        request = urllib2.Request(update.message.text.strip(),
                            headers=HEADERS)
                        status_code = urllib2.urlopen(request).getcode()
                        if status_code == 200:
                            file_contents = urllib2.urlopen(request).read()
                            # Base64 encode file data
                            metainfo = b64encode(file_contents)
                            if self.opts is None:
                                self.opts = {}
                            log.info(prelog() + 'Adding torrent from base64 string using options `%s` ...', self.opts)
                            tid = self.core.add_torrent_file(None, metainfo, self.opts)
                            self.apply_label(tid)
                        else:
                            update.message.reply_text(STRINGS['download_fail'],
                                reply_markup=ReplyKeyboardRemove())
                    except Exception as e:
                        update.message.reply_text(STRINGS['download_fail'],
                            reply_markup=ReplyKeyboardRemove())
                        log.error(prelog() + str(e) + '\n' + traceback.format_exc())
                else:
                    update.message.reply_text(STRINGS['not_url'],
                        reply_markup=ReplyKeyboardRemove())

                return ConversationHandler.END

            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())


    def apply_label(self, tid):
        try:
            if self.label is not None and self.label != STRINGS['no_label']:
                # Enable Label plugin
                component.get('Core').enable_plugin('Label')
                label_plugin = component.get('CorePlugin.Label')
                if label_plugin:
                    # Add label if neccessary
                    if self.label not in label_plugin.get_labels():
                        label_plugin.add(self.label.lower())
                    label_plugin.set_torrent(tid, self.label.lower())
                    log.debug(prelog() + 'Set label %s to torrent %s' % (self.label.lower(), tid))
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.print_exc())


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
        except Exception as e:
            log.error(prelog() + 'Error in alert %s' % str(e))


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
        self.bot.sendSticker(self.config['telegram_user'],
            choice(list(STICKERS.values())))
        self.telegram_send(STRINGS['test_success'])
