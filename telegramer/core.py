# encoding: utf-8
#
# core.py
#
# Copyright (C) 2016-2019 Noam <noamgit@gmail.com>
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
#   The Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor
#   Boston, MA  02110-1301, USA.
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

# import sys
# reload(sys)
# sys.setdefaultencoding('utf8')

#############################
# log.setLevel(logging.DEBUG)
#############################


def prelog():
    return strftime('%Y-%m-%d %H:%M:%S # Telegramer: ')


try:
    import re
    import urllib.request, urllib.error, urllib.parse
    from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot, Update)
    from telegram.ext import (Updater, CallbackContext, CommandHandler, MessageHandler,
                              RegexHandler, ConversationHandler, BaseFilter, Filters)
    from telegram.utils.request import Request
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


# class _FilterMagnets(BaseFilter):
#     def filter(self, message):
#         return 'magnet:?' in message.text


CATEGORY, SET_LABEL, TORRENT_TYPE, ADD_MAGNET, ADD_TORRENT, ADD_URL, RSS_FEED, FILE_NAME, REGEX = list(range(9))

DEFAULT_PREFS = {"telegram_token":                "Contact @BotFather and create a new bot",
                 "telegram_user":                 "Contact @MyIDbot",
                 "telegram_users":                "Contact @MyIDbot",
                 "telegram_users_notify":         "Contact @MyIDbot",
                 "telegram_notify_finished":      True,
                 "telegram_notify_added":         True,
                 "proxy_url":                     "",
                 'urllib3_proxy_kwargs_username': "",
                 "urllib3_proxy_kwargs_password": "",
                 "regex_exp":                     {},
                 "categories":                    {},
                 "message_added":                 "Added Torrent *TORRENTNAME*",
                 "message_finished":              "Finished Downloading *TORRENTNAME*",
                 "minimum_speed":                 int(-1),
                 "user_timer":                    int(60)
                 }


HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
                         '(KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'}

STICKERS = {'lincoln':  'BQADBAADGQADyIsGAAE2WnfSWOhfUgI',
            'dali':     'BQADBAADHAADyIsGAAFZfq1bphjqlgI',
            'chan':     'BQADBAADPQADyIsGAAHaVWyyLugSFAI',
            'marley':   'BQADBAADJQADyIsGAAGdzbYn4WkdaAI',
            'snow':     'CAADAgADZQUAAgi3GQJyjRNCuIA54gI',
            'borat':    'CAADBAADmwQAAjJQbQAB5DpM4iETWoQC'}

EMOJI = {'seeding':     '\u23eb',
         'queued':      '\u23ef',
         'paused':      '\u23f8',
         'error':       '\u2757\ufe0f',
         'downloading': '\u23ec'}

REGEX_SUBS_WORD = r"NAME"

STRINGS = {'no_label': 'No Label',
           'no_category': 'Use Default Settings',
           'cancel': 'Send /cancel at any time to abort',
           'test_success': 'It works!',
           'torrent_or_rss': 'What would you like to add ?',
           'which_cat': 'Which category/directory?\nRemember to quote ' +
                        'directory paths ("/path/to/dir")',
           'which_label': 'Which label?',
           'what_kind': 'What kind?',
           'send_magnet': 'Please send me the magnet link',
           'send_file': 'Please send me the torrent file',
           'send_url': 'Please send me the address',
           'added_rss': 'Successfully added RSS subscription!',
           'eta': 'ETA',
           'error': 'Error',
           'not_magnet': 'Aw man... That\'s not a magnet link',
           'no_magnet_found': 'Magnet not found in message',
           'not_file': 'Aw man... That\'s not a torrent file',
           'not_url': 'Aw man... Bad link',
           'download_fail': 'Aw man... Download failed',
           'no_items': 'No items',
           'torrent': 'Torrent',
           'rss': 'RSS',
           'which_rss_feed': 'Which RSS feed?',
           'which_regex': 'Which RSS regex template to use?',
           'no_rss_found': 'No RSS feeds configured in YaRSS2 plugin',
           'file_name': 'What to search for in the release name?',
           'no_name': 'The regex you chose does not contain the "' + REGEX_SUBS_WORD +
                     '" keyword - please choose another',
           'no_regex': 'No regex templates found in Telegramer settings'}

INFO_DICT = (('queue', lambda i, s: i != -1 and str(i) or '#'),
             ('state', None),
             ('name', lambda i, s: ' %s *%s* ' %
              (s['state'] if s['state'].lower() not in EMOJI
               else EMOJI[s['state'].lower()],
               i)),
             ('total_wanted', lambda i, s: '(%s) ' % fsize(i)),
             ('progress', lambda i, s: '%s\n' % fpcnt(i/100)),
             ('num_seeds', None),
             ('num_peers', None),
             ('total_seeds', None),
             ('total_peers', lambda i, s: '%s / %s seeds\n' %
              tuple(map(fpeer, (s['num_seeds'], s['num_peers']),
                               (s['total_seeds'], s['total_peers'])))),
             ('download_payload_rate', None),
             ('upload_payload_rate', lambda i, s: '%s : %s\n' %
              tuple(map(fspeed, (s['download_payload_rate'], i)))),
             ('eta', lambda i, s: i > 0 and '*ETA:* %s ' % ftime(i) or ''),
             ('time_added', lambda i, s: '*Added:* %s' % fdate(i)))

INFOS = [i[0] for i in INFO_DICT]

# filter_magnets = _FilterMagnets()


def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def format_torrent_info(torrent):
    status = torrent.get_status(INFOS)
    log.debug(prelog())
    log.debug(status)
    status_string = ''
    try:
        status_string = ''.join([f(status[i], status) for i, f in INFO_DICT if f is not None])
    # except UnicodeDecodeError as e:
    except Exception as e:
        status_string = ''
        log.error(prelog() + str(e) + '\n' + traceback.format_exc())
    return status_string


class Core(CorePluginBase):
    def __init__(self, *args):
        self.opts = {}
        self.bot = None
        self.updater = None
        self.is_rss = False
        self.yarss_data = YarssData()
        self.yarss_config = None
        self.yarss_plugin = None

        log.debug(prelog() + 'Initialize class')
        super(Core, self).__init__(*args)

    def enable(self):
        try:
            log.info(prelog() + 'Enable')
            self.config = deluge.configmanager.ConfigManager('telegramer.conf',
                                                             DEFAULT_PREFS)
            self.whitelist = []
            self.notifylist = []
            self.label = None
            self.magnet_only = False
            self.check_speed_timer = None
            self.COMMANDS = {'list':        self.cmd_list,
                             'down':        self.cmd_down,
                             'downloading': self.cmd_down,
                             'up':          self.cmd_up,
                             'uploading':   self.cmd_up,
                             'seed':        self.cmd_up,
                             'seeding':     self.cmd_up,
                             'paused':      self.cmd_paused,
                             'queued':      self.cmd_paused,
                             # '?':           self.cmd_help,
                             'cancel':      self.cancel,
                             'help':        self.cmd_help,
                             'start':       self.cmd_help,
                             'reload':      self.restart_telegramer,
                             # 'rss':         self.cmd_add_rss,
                             'commands':    self.cmd_help}

            log.debug(prelog() + 'Initialize bot')

            if self.config['telegram_token'] != DEFAULT_PREFS['telegram_token']:
                if self.config['telegram_user']:
                    telegram_user_list = None
                    self.whitelist.append(str(self.config['telegram_user']))
                    self.notifylist.append(str(self.config['telegram_user']))
                    if self.config['telegram_users']:
                        telegram_user_list = [_f for _f in [x.strip() for x in
                                                    str(self.config['telegram_users']).split(',')] if _f]
                        # Merge with whitelist and remove duplicates - order will be lost
                        self.whitelist = list(set(self.whitelist + telegram_user_list))
                        log.debug(prelog() + 'Whitelist: ' + str(self.whitelist))
                    if self.config['telegram_users_notify']:
                        n = [_f for _f in [x.strip() for x in
                                   str(self.config['telegram_users_notify']).split(',')] if _f]
                        telegram_user_list_notify = [a for a in n if is_int(a)]
                        # Merge with notifylist and remove duplicates - order will be lost
                        self.notifylist = list(set(self.notifylist +
                                                   telegram_user_list_notify))
                        log.debug(prelog() + 'Notify: ' + str(self.notifylist))

                reactor.callLater(2, self.connect_events)
                # Slow torrent notifications
                if self.config['minimum_speed'] > -1:
                    try:
                        self.check_speed_timer = LoopingCall(self.check_speed)
                        self.check_speed_timer.start(int(self.config['user_timer']), now=False)
                    except Exception as e:
                        log.error(prelog() + str(e) + '\n' + traceback.format_exc())
                # Proxy args
                REQUEST_KWARGS = {
                    'proxy_url': self.config['proxy_url'],
                    'urllib3_proxy_kwargs': {
                        'username': self.config['urllib3_proxy_kwargs_username'],
                        'password': self.config['urllib3_proxy_kwargs_password'],
                    }
                }
                bot_request = Request(**REQUEST_KWARGS)
                self.bot = Bot(self.config['telegram_token'], request=bot_request)
                # Create the EventHandler and pass it bot's token.
                # self.updater = Updater(self.config['telegram_token'], bot=self.bot, request_kwargs=REQUEST_KWARGS)
                self.updater = Updater(bot=self.bot, use_context=True, request_kwargs=REQUEST_KWARGS)
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
                # Add torrent paused
                conv_handler_paused = ConversationHandler(
                    entry_points=[CommandHandler('addpaused', self.add_paused)],
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
                conv_handler_rss = ConversationHandler(
                    entry_points=[CommandHandler('rss', self.cmd_add_rss)],
                    states={
                        RSS_FEED: [MessageHandler(Filters.text, self.rss_feed)],
                        REGEX: [MessageHandler(Filters.text, self.regex)],
                        FILE_NAME: [MessageHandler(Filters.text, self.rss_file_name)],
                        CATEGORY: [MessageHandler(Filters.text, self.category)]
                    },
                    fallbacks=[CommandHandler('cancel', self.cancel)]
                )

                dp.add_handler(conv_handler)
                dp.add_handler(conv_handler_paused)
                dp.add_handler(conv_handler_rss)
                dp.add_handler(MessageHandler(Filters.document, self.add_torrent))
                dp.add_handler(MessageHandler(Filters.regex(r'magnet:\?'), self.find_magnet))

                for key, value in self.COMMANDS.items():
                    dp.add_handler(CommandHandler(key, value))

                # Log all errors
                dp.add_error_handler(self.error)
                #######################################################################
                """
                log.error(prelog() + 'Start thread for polling')
                # Initialize polling thread
                bot_thread = threading.Thread(target=self.telegram_poll_start, args=())
                # Daemonize thread
                bot_thread.daemon = True
                # Start thread
                bot_thread.start()
                """
                #######################################################################
                # Start the Bot
                self.updater.start_polling(poll_interval=0.05)
                # self.updater.idle() # blocks
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def error(self, update: Update, context: CallbackContext):
        log.warn('Update "%s" caused error "%s"' % (update, context.error))

    def disable(self):
        try:
            if self.check_speed_timer:
                self.check_speed_timer.stop()
            log.info(prelog() + 'Disable')
            reactor.callLater(2, self.disconnect_events)
            self.whitelist = []
            self.telegram_poll_stop()
            # self.bot = None
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def update(self):
        pass

    def telegram_send(self, message, to=None, parse_mode=None):
        if self.bot:
            log.debug(prelog() + 'Send message')
            if not to:
                log.debug(prelog() + '"to" not set')
                to = self.config['telegram_user']
            else:
                log.debug(prelog() + 'send_message, to set')
            if not isinstance(to, list):
                log.debug(prelog() + 'Convert "to" to list')
                to = [to]
            log.debug(prelog() + "[to] " + str(to))
            for usr in to:
                # Every outgoing message filtered here
                if str(usr) in self.whitelist or str(usr) in self.notifylist:
                    log.debug(prelog() + "to: " + str(usr))
                    if len(message) > 4096:
                        log.debug(prelog() +
                                  'Message length is {}'.format(str(len(message))))
                        tmp = ''
                        for line in message.split('\n'):
                            tmp += line + '\n'
                            if len(tmp) > 4000:
                                msg = self.bot.send_message(usr, tmp,
                                                            parse_mode='Markdown')
                                tmp = ''
                    else:
                        if parse_mode:
                            msg = self.bot.send_message(usr, message,
                                                        parse_mode='Markdown')
                        else:
                            msg = self.bot.send_message(usr, message)
        log.debug(prelog() + 'return')
        return

    def telegram_poll_start(self):
        # Skip this - for testing only
        pass
        """Like non_stop, this will run forever
        this way suspend/sleep won't kill the thread"""

        """
        while True:
            try:
                if self.updater:
                    log.debug(prelog() + 'Start polling')
                    # self.bot.polling()
                    self.updater.start_polling(poll_interval=0.05)
                    # self.updater.idle()
                    while True:     # and bot running HTTPSConnectionPool
                        sleep(10)
            except Exception as e:
                if self.updater:
                    self.updater.stop()
                log.error(prelog() + str(e) + '\n' +
                          traceback.format_exc() + ' - Sleeping...')
                sleep(10)
        """

    def telegram_poll_stop(self):
        try:
            log.debug(prelog() + 'Stop polling')
            # if self.updater.dispatcher:
            #     self.updater.dispatcher.stop()
            if self.updater:
                self.updater.stop()
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def cancel(self, update: Update, context: CallbackContext):
        if str(update.message.chat.id) in self.whitelist:
            log.info("User %s canceled the conversation."
                     % str(update.message.chat.id))
            update.message.reply_text('Operation cancelled',
                                      reply_markup=ReplyKeyboardRemove())
            self.is_rss = False
            self.magnet_only = False
            self.yarss_data.clear()
            return ConversationHandler.END

    def cmd_help(self, update: Update, context: CallbackContext):
        log.debug(prelog() + "Entered cmd_help")
        if str(update.message.chat.id) in self.whitelist:
            log.debug(prelog() + str(update.message.chat.id) + " in whitelist")
            help_msg = ['/add - Add a new torrent',
                        '/addpaused - Add a new torrent paused',
                        '/rss - Add a new RSS filter',
                        '/list - List all torrents',
                        '/down - List downloading torrents',
                        '/up - List uploading torrents',
                        '/paused - List paused torrents',
                        '/cancel - Cancels the current operation',
                        '/help - Show this help message']
            log.debug(prelog() + "telegram_send to " +
                      str([update.message.chat.id]))
            self.telegram_send('\n'.join(help_msg),
                               to=[update.message.chat.id],
                               parse_mode='Markdown')

    def cmd_list(self, update: Update, context: CallbackContext):
        if str(update.message.chat.id) in self.whitelist:
            # log.error(self.list_torrents())
            self.telegram_send(self.list_torrents(lambda t:
                               t.get_status(('state',))['state'] in
                               ('Active', 'Downloading', 'Seeding',
                                'Paused', 'Checking', 'Error', 'Queued')),
                               to=[update.message.chat.id],
                               parse_mode='Markdown')

    def cmd_down(self, update: Update, context: CallbackContext):
        if str(update.message.chat.id) in self.whitelist:
            self.telegram_send(self.list_torrents(lambda t:
                               t.get_status(('state',))['state'] == 'Downloading'),
                               to=[update.message.chat.id],
                               parse_mode='Markdown')

    def cmd_up(self, update: Update, context: CallbackContext):
        if str(update.message.chat.id) in self.whitelist:
            self.telegram_send(self.list_torrents(lambda t:
                               t.get_status(('state',))['state'] == 'Seeding'),
                               to=[update.message.chat.id],
                               parse_mode='Markdown')

    def cmd_paused(self, update: Update, context: CallbackContext):
        if str(update.message.chat.id) in self.whitelist:
            self.telegram_send(self.list_torrents(lambda t:
                               t.get_status(('state',))['state'] in
                               ('Paused', 'Queued')),
                               to=[update.message.chat.id],
                               parse_mode='Markdown')

    def add(self, update: Update, context: CallbackContext):
        if str(update.message.chat.id) in self.whitelist:
            self.opts = {}
            self.is_rss = False
            self.magnet_only = False
            return self.prepare_categories(update, context)
            """
            if "YaRSS2" in component.get('Core').get_available_plugins():
                return self.prepare_torrent_or_rss(update, context)
            else:
                return self.prepare_categories(update, context)
            """

    def add_paused(self, update: Update, context: CallbackContext):
        # log.error(type(update.message.chat.id) + str(update.message.chat.id))
        if str(update.message.chat.id) in self.whitelist:
            self.opts = {}
            self.opts["addpaused"] = True
            self.is_rss = False
            self.magnet_only = False
            return self.prepare_categories(update, context)

    def cmd_add_rss(self, update: Update, context: CallbackContext):
        # log.error(type(update.message.chat.id) + str(update.message.chat.id))
        if str(update.message.chat.id) in self.whitelist:
            if "YaRSS2" in component.get('Core').get_available_plugins():
                return self.add_rss(update, context)
            else:
                update.message.reply_text('YaRSS2 plugin not available',
                                          reply_markup=ReplyKeyboardRemove())
                self.is_rss = False
                self.yarss_data.clear()
                return ConversationHandler.END
                # return self.prepare_categories(update, context)

    # def prepare_torrent_or_rss(self, update: Update, context: CallbackContext):
    #     try:
    #         keyboard_options = [[STRINGS['torrent']], [STRINGS['rss']]]
    #         update.message.reply_text(
    #             '%s\n%s' % (STRINGS['torrent_or_rss'], STRINGS['cancel']),
    #             reply_markup=ReplyKeyboardMarkup(keyboard_options,
    #                                              one_time_keyboard=True))
    #         return TORRENT_OR_RSS
    #
    #     except Exception as e:
    #         log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def torrent_or_rss(self, update: Update, context: CallbackContext):
        try:
            if str(update.message.chat.id) not in self.whitelist:
                return

            if STRINGS['torrent'] == update.message.text:
                return self.prepare_categories(update, context)

            if STRINGS['rss'] == update.message.text:
                return self.add_rss(update, context)

        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def prepare_categories(self, update: Update, context: CallbackContext):
        try:
            keyboard_options = []
            filtered_dict = {c: d for c, d in self.config["categories"].items() if os.path.isdir(d)}
            missing = {c: d for c, d in self.config["categories"].items() if not os.path.isdir(d)}
            if len(missing) > 0:
                for k in list(missing.keys()):
                    log.error(prelog() + "Missing directory for category {} ({})".format(k, missing[k]))
            for c, d in filtered_dict.items():
                log.error(prelog() + c + ' : ' + d)
                keyboard_options.append([c])

            keyboard_options.append([STRINGS['no_category']])
            update.message.reply_text(
                '%s\n%s' % (STRINGS['which_cat'], STRINGS['cancel']),
                reply_markup=ReplyKeyboardMarkup(keyboard_options,
                                                 one_time_keyboard=True))
            return CATEGORY
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def prepare_torrent_type(self, update: Update, context: CallbackContext):
        if str(update.message.chat.id) in self.whitelist:
            try:
                # Request torrent type
                keyboard_options = []
                keyboard_options.append(['Magnet'])
                keyboard_options.append(['.torrent'])
                keyboard_options.append(['URL'])

                update.message.reply_text(
                    STRINGS['what_kind'],
                    reply_markup=ReplyKeyboardMarkup(keyboard_options,
                                                     one_time_keyboard=True))
                return TORRENT_TYPE
            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def category(self, update: Update, context: CallbackContext):
        if str(update.message.chat.id) in self.whitelist:
            try:
                if STRINGS['no_category'] == update.message.text:
                    self.opts = self.opts
                else:
                    if update.message.text in list(self.config["categories"].keys()):
                        # move_completed_path vs download_location
                        self.opts["move_completed_path"] = self.config["categories"][update.message.text]
                        self.opts["move_completed"] = True

                    # If none of the existing categories were selected,
                    # maybe user is trying to save to a new directory
                    else:  # if not self.opts:
                        try:
                            log.debug(prelog() + 'Custom directory entered: ' +
                                      str(update.message.text))
                            if update.message.text[0] == '"' and \
                                    update.message.text[-1] == '"':
                                otherpath = os.path.abspath(os.path.realpath(
                                    update.message.text[1:-1]))
                                log.debug(prelog() +
                                          'Attempt to create and save to: ' +
                                          str(otherpath))
                                if not os.path.exists(otherpath):
                                    log.debug(prelog() + 'mkdir {}'.format(otherpath))
                                    os.makedirs(otherpath)
                                self.opts["move_completed_path"] = otherpath
                                self.opts["move_completed"] = True
                        except Exception as e:
                            log.error(prelog() + str(e) + '\n' +
                                      traceback.format_exc())
                if self.is_rss:
                    log.debug(prelog() + "is_rss, calling RSS_APPLY")
                    return self.rss_apply(update, context)

                log.debug(prelog() + "Label segment")
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
                    reply_markup=ReplyKeyboardMarkup(keyboard_options,
                                                     one_time_keyboard=True))

                return SET_LABEL

                """
                if len(keyboard_options) > 0:
                    keyboard_options.append([STRINGS['no_label']])

                    update.message.reply_text(
                        STRINGS['which_label'],
                        reply_markup=ReplyKeyboardMarkup(keyboard_options,
                                                         one_time_keyboard=True))
                    return SET_LABEL
                else:
                    if self.is_rss:
                        return self.prepare_rss_feed(update, context)
                    else:
                        return self.prepare_torrent_type(update)
                """

            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def prepare_rss_feed(self, update: Update, context: CallbackContext):
        if self.yarss_plugin is None:
            self.yarss_plugin = component.get('CorePlugin.YaRSS2')
        if self.yarss_plugin:
            self.yarss_config = self.yarss_plugin.get_config()
            feeds = {}
            # Create dictionary with feed name:url
            for rss_feed in list(self.yarss_config["rssfeeds"].values()):
                feeds[rss_feed["name"]] = rss_feed["url"]
            # If feed(s) found
            count = 0
            if len(feeds) > 0:
                count = count + 1
                feedlist = "\n".join(["{}) [{}]({})".format(count, f, feeds[f]) for f in list(feeds.keys())])
                keyboard_options = [list(feeds.keys())]
                update.message.reply_text(
                    '%s\n\n%s\n\n%s' % (STRINGS['which_rss_feed'], feedlist, STRINGS['cancel']),
                    reply_markup=ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True),
                    parse_mode='Markdown')
                return RSS_FEED
            # If no feed(s) found
            else:
                log.debug(prelog() + STRINGS['no_rss_found'])
                update.message.reply_text('%s' % (STRINGS['no_rss_found']),
                                          reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END

        return ConversationHandler.END

    def rss_feed(self, update: Update, context: CallbackContext):
        if not str(update.message.chat.id) in self.whitelist:
            return
        self.is_rss = True
        try:
            rss_feed = next(rss_feed for rss_feed in list(self.yarss_config["rssfeeds"].values())
                            if rss_feed["name"] == update.message.text)

            self.yarss_data.subscription_data["rssfeed_key"] = rss_feed["key"]
            log.debug(prelog() + 'User chose rss_feed "' + rss_feed["name"] + '"')

            log.debug(self.config["regex_exp"])

            keyboard_options = [[regex_name] for regex_name in list(self.config["regex_exp"].keys()) if regex_name != '']

            if len(keyboard_options) > 0:
                update.message.reply_text(
                    '%s\n%s' % (STRINGS['which_regex'], STRINGS['cancel']),
                    reply_markup=ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True))
                return REGEX
            else:
                update.message.reply_text(
                    '%s\n%s' % (STRINGS['no_regex'], STRINGS['cancel']),
                    reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def regex(self, update: Update, context: CallbackContext):
        if not str(update.message.chat.id) in self.whitelist:
            return
        if REGEX_SUBS_WORD in self.config["regex_exp"][update.message.text]:
            self.yarss_data.subscription_data["regex_include"] = self.config["regex_exp"][update.message.text]

            log.debug(prelog() + 'User chose regex ' + update.message.text)
            update.message.reply_text(
                '%s\n%s' % (STRINGS['file_name'], STRINGS['cancel']),
                reply_markup=ReplyKeyboardRemove())
            return FILE_NAME
        else:
            keyboard_options = [[regex_name] for regex_name in list(self.config["regex_exp"].keys())]
            update.message.reply_text(
                '%s\n%s' % (STRINGS['no_name'], STRINGS['cancel']),
                reply_markup=ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True))
            return REGEX

    def rss_file_name(self, update: Update, context: CallbackContext):
        if not str(update.message.chat.id) in self.whitelist:
            return

        log.debug(prelog() + update.message.text)
        update.message.text = re.sub(' +', ' ', update.message.text)

        self.yarss_data.subscription_data["regex_include"] = re.sub(REGEX_SUBS_WORD, update.message.text,
                                                                    self.yarss_data.subscription_data["regex_include"])
        self.yarss_data.subscription_data["regex_include"] = re.sub(r" ", ".*",
                                                                    self.yarss_data.subscription_data["regex_include"])
        log.debug(prelog() + "Adding regex " + self.yarss_data.subscription_data["regex_include"])

        self.yarss_data.subscription_data["label"] = self.label
        self.yarss_data.subscription_data["name"] = update.message.text

        return self.prepare_categories(update, context)

    def rss_apply(self, update: Update, context: CallbackContext):
        log.debug(prelog() + "entered rss_apply")
        if str(update.message.chat.id) in self.whitelist:
            log.debug(prelog() + "in whitelist")
            try:
                log.debug(prelog() + "rss_apply opts: {}".format(self.opts))
                if len(self.opts) > 0:
                    log.debug(prelog() + "Setting download location: " + self.opts["move_completed_path"])
                    self.yarss_data.subscription_data["download_location"] = self.opts["move_completed_path"]
                r = self.yarss_data.addRss()
                if r:
                    update.message.reply_text('%s' % (STRINGS['added_rss']),
                                              reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())
        else:
            log.debug(prelog() + "not in whitelist")

    def set_label(self, update: Update, context: CallbackContext):
        if str(update.message.chat.id) in self.whitelist:
            try:
                # user = update.message.chat.id
                self.label = update.message.text
                log.debug(prelog() + "Label: %s" % (update.message.text))

                return self.prepare_torrent_type(update, context)

                """
                # Request torrent type
                if self.is_rss:
                    return self.prepare_rss_feed(update, context)
                else:
                    return self.prepare_torrent_type(update)
                """

            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def torrent_type(self, update: Update, context: CallbackContext):
        if str(update.message.chat.id) in self.whitelist:
            try:
                user = update.message.chat.id
                torrent_type_selected = update.message.text

                if torrent_type_selected == 'Magnet':
                    update.message.reply_text(STRINGS['send_magnet'],
                                              reply_markup=ReplyKeyboardRemove())
                    return ADD_MAGNET

                elif torrent_type_selected == '.torrent':
                    update.message.reply_text(STRINGS['send_file'],
                                              reply_markup=ReplyKeyboardRemove())
                    return ADD_TORRENT

                elif torrent_type_selected == 'URL':
                    update.message.reply_text(STRINGS['send_url'],
                                              reply_markup=ReplyKeyboardRemove())
                    return ADD_URL

                else:
                    update.message.reply_text(STRINGS['error'],
                                              reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END

            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def add_magnet(self, update: Update, context: CallbackContext):
        if str(update.message.chat.id) in self.whitelist:
            try:
                if self.magnet_only:
                    # Reset bool
                    self.magnet_only = False
                    m = re.findall(r'magnet:\?.*\b', update.message.text)
                    if len(m) == 1:
                        metainfo = m[0]
                        self.opts = {}
                        if is_magnet(metainfo):
                            log.debug(prelog() + 'Adding torrent from magnet ' +
                                      'URI `%s` using options `%s` ...',
                                      metainfo, self.opts)
                            tid = component.get('Core').add_torrent_magnet(metainfo, self.opts)
                            return ConversationHandler.END
                    else:
                        log.error("Magnet not found in message")
                else:
                    user = update.message.chat.id
                    log.debug("addmagnet of %s: %s" % (str(user), update.message.text))
                    # options = None
                    metainfo = update.message.text
                    """Adds a torrent with the given options.
                    metainfo could either be base64 torrent
                    data or a magnet link. Available options
                    are listed in deluge.core.torrent.TorrentOptions.
                    """
                    if self.opts is None:
                        self.opts = {}
                    if is_magnet(metainfo):
                        log.debug(prelog() + 'Adding torrent from magnet ' +
                                  'URI `%s` using options `%s` ...',
                                  metainfo, self.opts)
                        tid = component.get('Core').add_torrent_magnet(metainfo, self.opts)
                        r = self.apply_label(tid)
                    else:
                        update.message.reply_text(STRINGS['not_magnet'],
                                                  reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())

            # except Exception as e:
            #     log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def find_magnet(self, update: Update, context: CallbackContext):
        if str(update.message.chat.id) in self.whitelist:
            try:
                log.debug("Find magnets in message")
                try:
                    # options = None
                    m = re.findall(r'magnet:\?.*\b', update.message.text)
                    if len(m) > 0:
                        mag = m[0]
                        self.magnet_only = True
                        return self.add_magnet(update, context)
                    else:
                        log.debug("Magnet not found in message")
                        update.message.reply_text(STRINGS['no_magnet_found'],
                                                  reply_markup=ReplyKeyboardRemove())
                        return ConversationHandler.END
                except Exception as e:
                    log.error(prelog() + str(e) + '\n' + traceback.format_exc())

                return ConversationHandler.END

            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def add_torrent(self, update: Update, context: CallbackContext):
        if str(update.message.chat.id) in self.whitelist:
            try:
                user = update.message.chat.id
                log.debug("addtorrent of %s: %s" %
                          (str(user), update.message.document))

                if update.message.document.mime_type == 'application/x-bittorrent':
                    # Get file info
                    file_info = self.bot.getFile(update.message.document.file_id)
                    # Download file
                    request = urllib.request.Request(file_info.file_path, headers=HEADERS)
                    status_code = urllib.request.urlopen(request).getcode()
                    if status_code == 200:
                        file_contents = urllib.request.urlopen(request).read()
                        # Base64 encode file data
                        metainfo = b64encode(file_contents)
                        if self.opts is None:
                            self.opts = {}
                        log.info(prelog() + 'Adding torrent from base64 string' +
                                 'using options `%s` ...', self.opts)
                        tid = component.get('Core').add_torrent_file(None, metainfo, self.opts)
                        r = self.apply_label(tid)
                    else:
                        update.message.reply_text(STRINGS['download_fail'],
                                                  reply_markup=ReplyKeyboardRemove())
                else:
                    update.message.reply_text(STRINGS['not_file'],
                                              reply_markup=ReplyKeyboardRemove())

                return ConversationHandler.END

            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def add_url(self, update: Update, context: CallbackContext):
        if str(update.message.chat.id) in self.whitelist:
            try:
                user = update.message.chat.id
                log.debug("addurl of %s: %s" % (str(user), update.message.text))

                if is_url(update.message.text):
                    try:
                        # Download file
                        request = urllib.request.Request(update.message.text.strip(),
                                                  headers=HEADERS)
                        status_code = urllib.request.urlopen(request).getcode()
                        if status_code == 200:
                            file_contents = urllib.request.urlopen(request).read()
                            # Base64 encode file data
                            metainfo = b64encode(file_contents)
                            if self.opts is None:
                                self.opts = {}
                            log.info(prelog() + 'Adding torrent from base64 string' +
                                     'using options `%s` ...', self.opts)
                            tid = component.get('Core').add_torrent_file(None, metainfo, self.opts)
                            r = self.apply_label(tid)
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

    def add_rss(self, update: Update, context: CallbackContext):
        try:
            component.get('Core').enable_plugin('YaRSS2')
            self.is_rss = True
            return self.prepare_rss_feed(update, context)
            # return self.prepare_categories(update, context)
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
                    log.debug(prelog() + 'Set label %s to torrent %s' %
                              (self.label.lower(), tid))
                    return True
            return False
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.print_exc())

    def update_stats(self):
        log.debug('update_stats')

    def check_speed(self):
        log.debug("Minimum speed: %s", self.config["minimum_speed"])
        try:
            for t in list(component.get('TorrentManager').torrents.values()):
                if t.get_status(("state",))["state"] == "Downloading":
                    if t.status.download_rate < (self.config['minimum_speed'] * 1024):
                        message = _('Torrent *%(name)s* is slower than minimum speed!') % t.get_status({})
                        self.telegram_send(message, to=self.notifylist, parse_mode='Markdown')
        except Exception as e:
            log.error(prelog() + 'Unexpected behavior %s.' % str(e))
        return

    def connect_events(self):
        event_manager = component.get('EventManager')
        event_manager.register_event_handler('TorrentFinishedEvent',
                                             self.on_torrent_finished)
        event_manager.register_event_handler('TorrentAddedEvent',
                                             self.on_torrent_added)

    def disconnect_events(self):
        event_manager = component.get('EventManager')
        event_manager.deregister_event_handler('TorrentFinishedEvent',
                                               self.on_torrent_finished)
        event_manager.deregister_event_handler('TorrentAddedEvent',
                                               self.on_torrent_added)

    def on_torrent_added(self, torrent_id, from_state):
        if (self.config['telegram_notify_added'] is False):
            return
        try:
            custom_message = False
            torrent = component.get('TorrentManager')[torrent_id]
            torrent_status = torrent.get_status(['name'])
            # Check if label shows up here
            log.debug("get_status for {}".format(torrent_id))
            log.debug(torrent_status)
            message = _('Added Torrent *%(name)s*') % torrent_status
            # Check if custom message
            if self.config["message_added"] is not DEFAULT_PREFS["message_added"] \
               and len(self.config["message_added"]) > 0:
                custom_message = True
                user_message = self.config["message_added"]
                if "TORRENTNAME" not in self.config["message_added"]:
                    log.info(prelog() + "Custom message does not contain the torrent name (TORRENTNAME)")
                    # message = "{}".format(user_message.replace("TORRENTNAME", re.escape(torrent_status["name"])))
                message = "{}".format(user_message.replace("TORRENTNAME", torrent_status["name"]))
            log.info(prelog() + 'Sending torrent added message to ' +
                     str(self.notifylist))
            return self.telegram_send('{}'.format(message), to=self.notifylist, parse_mode='Markdown')
        except Exception as e:
            log.error(prelog() + 'Error in alert %s' % str(e))

    def on_torrent_finished(self, torrent_id):
        try:
            if (self.config['telegram_notify_finished'] is False):
                return
            custom_message = False
            torrent = component.get('TorrentManager')[torrent_id]
            torrent_status = torrent.get_status(['name'])
            # Check if label shows up here
            log.debug("get_status for {}".format(torrent_id))
            log.debug(torrent_status)
            message = _('Finished Downloading *%(name)s*') % torrent_status
            # Check if custom message
            if self.config["message_finished"] is not DEFAULT_PREFS["message_finished"] \
               and len(self.config["message_finished"]) > 0:
                custom_message = True
                user_message = self.config["message_finished"]
                if "TORRENTNAME" not in self.config["message_finished"]:
                    log.info(prelog() + "Custom message does not contain the torrent name (TORRENTNAME)")
                    # message = "{}".format(user_message.replace("TORRENTNAME", re.escape(torrent_status["name"])))
                message = "{}".format(user_message.replace("TORRENTNAME", torrent_status["name"]))
            log.info(prelog() + 'Sending torrent finished message to ' +
                     str(self.notifylist))
            return self.telegram_send('{}'.format(message), to=self.notifylist, parse_mode='Markdown')
        except Exception as e:
            log.error(prelog() + 'Error in alert %s' %
                      str(e) + '\n' + traceback.format_exc())

    def list_torrents(self, filter=lambda _: True):
        return '\n'.join([format_torrent_info(t) for t
                         in list(component.get('TorrentManager').torrents.values())
                         if list(filter(t))] or [STRINGS['no_items']])

    @export
    def set_config(self, config):
        """Sets the config dictionary"""
        log.debug(prelog() + 'Set config')
        dirty = False
        for key in list(config.keys()):
            if ("categories" == key and self.config[key] == config[key]) or \
                    self.config[key] != config[key]:
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
        self.telegram_send(STRINGS['test_success'], to=self.config['telegram_user'])


class YarssData:

    def __init__(self):
        self.subscription_data = {}
        self.subscription_data["regex_exclude"] = ""
        self.subscription_data["regex_include_ignorecase"] = True
        self.subscription_data["regex_exclude_ignorecase"] = False
        self.subscription_data["custom_text_lines"] = ""
        self.subscription_data["last_match"] = ""
        self.subscription_data["ignore_timestamp"] = False
        self.subscription_data["active"] = True
        self.subscription_data["max_download_speed"] = -2
        self.subscription_data["max_upload_speed"] = -2
        self.subscription_data["max_connections"] = -2
        self.subscription_data["max_upload_slots"] = -2
        self.subscription_data["add_torrents_in_paused_state"] = "Default"
        self.subscription_data["auto_managed"] = "Default"
        self.subscription_data["sequential_download"] = "Default"
        self.subscription_data["prioritize_first_last_pieces"] = "Default"
        # Get notifications from notifications list
        self.subscription_data["email_notifications"] = {}
        self.subscription_data["move_completed"] = ""
        self.clear()

    def clear(self):
        self.subscription_data["name"] = ""
        self.subscription_data["label"] = ""
        self.subscription_data["rssfeed_key"] = ""
        self.subscription_data["regex_include"] = ""
        self.subscription_data["download_location"] = ""

    def addRss(self):
        try:
            self.yarss2_plugin = component.get('CorePlugin.YaRSS2')
            self.yarss2_plugin.save_subscription(subscription_data=self.subscription_data, delete=False)
            return True
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())
            return False
