# encoding: utf-8
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
from deluge.log import LOG as log

# import sys
# reload(sys)
# sys.setdefaultencoding('utf8')

#############################
log.setLevel(logging.DEBUG)
#############################


def prelog():
    return strftime('%Y-%m-%d %H:%M:%S # Telegramer: ')

try:
    import re
    import urllib2
    from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot)
    from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                              RegexHandler, ConversationHandler)
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

CATEGORY, SET_LABEL, TORRENT_TYPE, ADD_MAGNET, ADD_TORRENT, ADD_URL, TOR_OR_RSS, RSS_FEED, FILE_NAME, \
REGEX = range(10)

DEFAULT_PREFS = {"telegram_token":           "Contact @BotFather and create a new bot",
                 "telegram_user":            "Contact @MyIDbot",
                 "telegram_users":           "Contact @MyIDbot",
                 "telegram_users_notify":    "Contact @MyIDbot",
                 "telegram_notify_finished": True,
                 "telegram_notify_added":    True,
                 "proxy_url":                "",
                 'urllib3_proxy_kwargs_username': "",
                 "urllib3_proxy_kwargs_password": "",
                 "categories": {}}

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
           '(KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'}

STICKERS = {'lincoln':  'BQADBAADGQADyIsGAAE2WnfSWOhfUgI',
            'dali':     'BQADBAADHAADyIsGAAFZfq1bphjqlgI',
            'chan':     'BQADBAADPQADyIsGAAHaVWyyLugSFAI',
            'marley':   'BQADBAADJQADyIsGAAGdzbYn4WkdaAI',
            'snow':     'CAADAgADZQUAAgi3GQJyjRNCuIA54gI',
            'borat':    'CAADBAADmwQAAjJQbQAB5DpM4iETWoQC'}

EMOJI = {'seeding':     u'\u23eb',
         'queued':      u'\u23ef',
         'paused':      u'\u23f8',
         'error':       u'\u2757\ufe0f',
         'downloading': u'\u23ec'}

REGEX_SUBS_WORD = "NAME"

STRINGS = {'no_label': 'No Label',
           'no_category': 'Use Default Settings',
           'cancel': 'Send /cancel at any time to abort',
           'test_success': 'It works!',
           'torrent_or_rss': 'What you wish to add ?',
           'which_cat': 'Which category/directory?\nRemember to quote ' +
                        'directory paths ("/path/to/dir")',
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
           'no_items': 'No items',
           "torrent":'Torrent',
           "rss":"RSS",
           "which_rss_feed":'Which RSS feed?',
           "which_regex":'Which ReGex template to use?',
           "no_rss_found":'No RSS feeds found - exiting',
           "file_name":'What is the movie name?',
           "noNAME":'The regex you choose dosn\'t contains \'' + REGEX_SUBS_WORD +
                    '\' sequence - please choose another',
           "no_regex":'No regex found - exiting'}

INFO_DICT = (('queue', lambda i, s: i != -1 and str(i) or '#'),
             ('state', None),
             ('name', lambda i, s: u' %s *%s* ' %
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
        status_string = u''.join([f(status[i], status) for i, f in INFO_DICT if f is not None])
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
        self.isRss = False
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
            self.COMMANDS = {'list':        self.cmd_list,
                             'down':        self.cmd_down,
                             'downloading': self.cmd_down,
                             'up':          self.cmd_up,
                             'uploading':   self.cmd_up,
                             'seed':        self.cmd_up,
                             'seeding':     self.cmd_up,
                             'paused':      self.cmd_paused,
                             'queued':      self.cmd_paused,
                             '?':           self.cmd_help,
                             'cancel':      self.cancel,
                             'help':        self.cmd_help,
                             'start':       self.cmd_help,
                             'reload':      self.restart_telegramer,
                             'commands':    self.cmd_help}

            log.debug(prelog() + 'Initialize bot')

            if self.config['telegram_token'] != DEFAULT_PREFS['telegram_token']:
                if self.config['telegram_user']:
                    telegram_user_list = None
                    self.whitelist.append(str(self.config['telegram_user']))
                    self.notifylist.append(str(self.config['telegram_user']))
                    if self.config['telegram_users']:
                        telegram_user_list = filter(None, [x.strip() for x in
                                                    str(self.config['telegram_users']).split(',')])
                        # Merge with whitelist and remove duplicates - order will be lost
                        self.whitelist = list(set(self.whitelist + telegram_user_list))
                        log.debug(prelog() + 'Whitelist: ' + str(self.whitelist))
                    if self.config['telegram_users_notify']:
                        n = filter(None, [x.strip() for x in
                                   str(self.config['telegram_users_notify']).split(',')])
                        telegram_user_list_notify = [a for a in n if is_int(a)]
                        # Merge with notifylist and remove duplicates - order will be lost
                        self.notifylist = list(set(self.notifylist +
                                                   telegram_user_list_notify))
                        log.debug(prelog() + 'Notify: ' + str(self.notifylist))

                reactor.callLater(2, self.connect_events)
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
                self.updater = Updater(self.config['telegram_token'], request_kwargs=REQUEST_KWARGS)
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
                        ADD_URL: [MessageHandler(Filters.text, self.add_url)],
                        TOR_OR_RSS: [MessageHandler(Filters.text, self.tor_or_rss)],
                        RSS_FEED: [MessageHandler(Filters.text, self.rss_feed)],
                        REGEX: [MessageHandler(Filters.text, self.regex)],
                        FILE_NAME: [MessageHandler(Filters.text, self.rss_file_name)]
                    },
                    fallbacks=[CommandHandler('cancel', self.cancel)]
                )

                dp.add_handler(conv_handler)

                for key, value in self.COMMANDS.iteritems():
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


        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def error(self, bot, update, error):
        log.warn('Update "%s" caused error "%s"' % (update, error))

    def disable(self):
        try:
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
        if 1:  # str(update.message.chat.id) in self.whitelist:
            if self.bot:
                log.debug(prelog() + 'Send message')
                if not to:
                    to = self.config['telegram_user']
                else:
                    log.debug(prelog() + 'send_message, to set')
                if not isinstance(to, (list,)):
                    log.debug(prelog() + 'Convert to to list')
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

    def telegram_poll_stop(self):
        try:
            log.debug(prelog() + 'Stop polling')
            if self.updater:
                self.updater.stop()
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def cancel(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            log.info("User %s canceled the conversation."
                     % str(update.message.chat.id))
            update.message.reply_text('Operation cancelled',
                                      reply_markup=ReplyKeyboardRemove())
            self.isRss = False
            self.yarss_data.clear()
            return ConversationHandler.END

    def cmd_help(self, bot, update):
        log.debug(prelog() + "Entered cmd_help")
        if str(update.message.chat.id) in self.whitelist:
            log.debug(prelog() + str(update.message.chat.id) + " in whitelist")
            help_msg = ['/add - Add a new torrent',
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

    def cmd_list(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            # log.error(self.list_torrents())
            self.telegram_send(self.list_torrents(lambda t:
                               t.get_status(('state',))['state'] in
                               ('Active', 'Downloading', 'Seeding',
                                'Paused', 'Checking', 'Error', 'Queued')),
                               to=[update.message.chat.id],
                               parse_mode='Markdown')

    def cmd_down(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            self.telegram_send(self.list_torrents(lambda t:
                               t.get_status(('state',))['state'] == 'Downloading'),
                               to=[update.message.chat.id],
                               parse_mode='Markdown')

    def cmd_up(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            self.telegram_send(self.list_torrents(lambda t:
                               t.get_status(('state',))['state'] == 'Seeding'),
                               to=[update.message.chat.id],
                               parse_mode='Markdown')

    def cmd_paused(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            self.telegram_send(self.list_torrents(lambda t:
                               t.get_status(('state',))['state'] in
                               ('Paused', 'Queued')),
                               to=[update.message.chat.id],
                               parse_mode='Markdown')

    def add(self, bot, update):
        # log.error(type(update.message.chat.id) + str(update.message.chat.id))
        if str(update.message.chat.id) in self.whitelist:
            if "YaRSS2" in component.get('Core').get_available_plugins():
                return self.prepare_torrents_or_rss(bot, update)
            else:
                return self.prepare_categoies(bot, update)

    def prepare_torrents_or_rss(self, bot, update):
        try:
            keyboard_options = [[STRINGS['torrent']], [STRINGS['rss']]]
            update.message.reply_text(
                '%s\n%s' % (STRINGS['torrent_or_rss'], STRINGS['cancel']),
                reply_markup=ReplyKeyboardMarkup(keyboard_options,
                                                 one_time_keyboard=True))
            return TOR_OR_RSS

        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def tor_or_rss(self, bot, update):
        try:
            if str(update.message.chat.id) not in self.whitelist:
                return

            if STRINGS['torrent'] == update.message.text:
                return self.prepare_categoies(bot, update)

            if STRINGS['rss'] == update.message.text:
                return self.add_rss(bot, update)

        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def prepare_categoies(self, bot, update):
        try:
            keyboard_options = []
            filtered_dict = {c: d for c, d in self.config["categories"].iteritems() if os.path.isdir(d)}
            for c, d in filtered_dict.iteritems():
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


    def prepare_torrent_type(self, update):
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

    def category(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            try:
                if STRINGS['no_category'] == update.message.text:
                    self.opts = {}
                else:
                    if update.message.text in self.config["categories"].keys():
                        # move_completed_path vs download_location
                        self.opts = {'move_completed_path':
                                         self.config["categories"][update.message.text],
                                     'move_completed': True}

                        # If none of the existing categories were selected,
                        # maybe user is trying to save to a new directory
                        if not self.opts:
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
                                        os.makedirs(otherpath)
                                    self.opts = {'move_completed_path': otherpath,
                                                 'move_completed': True}
                            except Exception as e:
                                log.error(prelog() + str(e) + '\n' +
                                          traceback.format_exc())

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
                    log.error(prelog() + str(e) + '\n' +traceback.format_exc())

                if len(keyboard_options) > 0:
                    keyboard_options.append([STRINGS['no_label']])

                    update.message.reply_text(
                        STRINGS['which_label'],
                        reply_markup=ReplyKeyboardMarkup(keyboard_options,
                                                         one_time_keyboard=True))
                    return SET_LABEL
                else:
                    if self.isRss:
                        return self.prepare_rss_feed(bot, update)
                    else:
                        return self.prepare_torrent_type(update)

            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def prepare_rss_feed(self, bot, update):

        if self.yarss_plugin is None:
            self.yarss_plugin = component.get('CorePlugin.YaRSS2')
        if self.yarss_plugin:
            self.yarss_config = self.yarss_plugin.get_config()
            keyboard_options = [[rss_feed["name"]] for rss_feed in self.yarss_config["rssfeeds"].values()]
            # if no rss_feeds found
            if not bool(keyboard_options):
                log.debug(prelog() + STRINGS['no_rss_found'])
                update.message.reply_text('%s' % (STRINGS['no_rss_found']),
                                          reply_markup=ReplyKeyboardMarkup([],one_time_keyboard=True))
                return ConversationHandler.END

            update.message.reply_text(
                '%s\n%s' % (STRINGS['which_rss_feed'], STRINGS['cancel']),
                reply_markup=ReplyKeyboardMarkup(keyboard_options,one_time_keyboard=True))

            return RSS_FEED
        return ConversationHandler.END

    def rss_feed(self, bot, update):
        if not str(update.message.chat.id) in self.whitelist:
            return
        self.isRss = True
        rss_feed = next(rss_feed for rss_feed in self.yarss_config["rssfeeds"].values()
                            if rss_feed["name"] == update.message.text)

        self.yarss_data.subscription_data["rssfeed_key"] = rss_feed["key"]
        log.debug(prelog() + 'user choose rss_feed' + rss_feed["name"])

        keyboard_options = [[regex_name] for regex_name in self.config["regex_exp"].keys() if  regex_name != '']

        if not bool(keyboard_options):
            update.message.reply_text(
                '%s\n%s' % (STRINGS['no_regex'], STRINGS['cancel']),
                reply_markup=ReplyKeyboardMarkup([], one_time_keyboard=True))
            return ConversationHandler.END

        update.message.reply_text(
            '%s\n%s' % (STRINGS['which_regex'], STRINGS['cancel']),
            reply_markup=ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True))
        return REGEX

    def regex(self, bot, update):
        if not str(update.message.chat.id) in self.whitelist:
            return
        if REGEX_SUBS_WORD in self.config["regex_exp"][update.message.text]:
            self.yarss_data.subscription_data["regex_include"] = self.config["regex_exp"][update.message.text]

            log.debug(prelog() + 'user choose regex ' + update.message.text)
            update.message.reply_text(
                '%s\n%s' % (STRINGS['file_name'], STRINGS['cancel']),
                reply_markup=ReplyKeyboardMarkup([],one_time_keyboard=True))
            return FILE_NAME
        else:
            keyboard_options = [[regex_name] for regex_name in self.config["regex_exp"].keys()]
            update.message.reply_text(
                '%s\n%s' % (STRINGS['noNAME'], STRINGS['cancel']),
                reply_markup=ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True))
            return REGEX


    def rss_file_name(self, bot, update):
        if not str(update.message.chat.id) in self.whitelist:
            return

        log.debug(prelog() + update.message.text)
        update.message.text = re.sub(' +', ' ', update.message.text)

        self.yarss_data.subscription_data["regex_include"] = re.sub(r"NAME", update.message.text,
                                                                    self.yarss_data.subscription_data["regex_include"])
        self.yarss_data.subscription_data["regex_include"] = re.sub(r" ", ".*",
                                                                    self.yarss_data.subscription_data["regex_include"])
        log.debug(prelog() + "Adding Regex " + self.yarss_data.subscription_data["regex_include"])

        self.yarss_data.subscription_data["label"] = self.label
        self.yarss_data.subscription_data["name"] = update.message.text
        if self.opts is not None:
            self.yarss_data.subscription_data["download_location"] = self.opts["move_completed_path"]

        self.yarss_data.addRss()
        update.message.reply_text(
            '%s' % (STRINGS['added']),
            reply_markup=ReplyKeyboardMarkup([], one_time_keyboard=True))
        return ConversationHandler.END

    def set_label(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            try:
                user = update.message.chat.id

                self.label = update.message.text
                log.debug(prelog() + "Label: %s" % (update.message.text))

                # Request torrent type
                if self.isRss:
                    return self.prepare_rss_feed(bot, update)
                else:
                    return self.prepare_torrent_type(update)

            except Exception as e:
                log.error(prelog() + str(e) + '\n' + traceback.format_exc())

    def torrent_type(self, bot, update):
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

    def add_magnet(self, bot, update):
        if str(update.message.chat.id) in self.whitelist:
            try:
                user = update.message.chat.id
                log.debug("addmagnet of %s: %s" % (str(user), update.message.text))

                try:
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
                        tid =component.get('Core').add_torrent_magnet(metainfo, self.opts)
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
                log.debug("addtorrent of %s: %s" %
                          (str(user), update.message.document))

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
                        log.info(prelog() + 'Adding torrent from base64 string' +
                                 'using options `%s` ...', self.opts)
                        tid =component.get('Core').add_torrent_file(None, metainfo, self.opts)
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
                            log.info(prelog() + 'Adding torrent from base64 string' +
                                     'using options `%s` ...', self.opts)
                            tid =component.get('Core').add_torrent_file(None, metainfo, self.opts)
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

    def add_rss(self, bot, update):
        try:
            component.get('Core').enable_plugin('YaRSS2')
            self.isRss = True
            return self.prepare_categoies(bot, update)
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
        except Exception as e:
            log.error(prelog() + str(e) + '\n' + traceback.print_exc())

    def update_stats(self):
        log.debug('update_stats')

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

    def on_torrent_added(self, torrent_id):
        if (self.config['telegram_notify_added'] is False):
            return
        try:
            # torrent_id = str(alert.handle.info_hash())
            torrent = component.get('TorrentManager')[torrent_id]
            torrent_status = torrent.get_status({})
            message = _('Added Torrent *%(name)s*') % torrent_status
            log.info(prelog() + 'Sending torrent added message to ' +
                     str(self.notifylist))
            return self.telegram_send(message, to=self.notifylist, parse_mode='Markdown')
        except Exception as e:
            log.error(prelog() + 'Error in alert %s' % str(e))

    def on_torrent_finished(self, torrent_id):
        try:
            if (self.config['telegram_notify_finished'] is False):
                return
            # torrent_id = str(alert.handle.info_hash())
            torrent = component.get('TorrentManager')[torrent_id]
            torrent_status = torrent.get_status({})
            message = _('Finished Downloading *%(name)s*') % torrent_status
            log.info(prelog() + 'Sending torrent finished message to ' +
                     str(self.notifylist))
            return self.telegram_send(message, to=self.notifylist, parse_mode='Markdown')
        except Exception, e:
            log.error(prelog() + 'Error in alert %s' %
                      str(e) + '\n' + traceback.format_exc())

    def list_torrents(self, filter=lambda _: True):
        return '\n'.join([format_torrent_info(t) for t
                         in component.get('TorrentManager').torrents.values()
                         if filter(t)] or [STRINGS['no_items']])

    @export
    def set_config(self, config):
        """Sets the config dictionary"""
        log.debug(prelog() + 'Set config')
        dirty = False
        for key in config.keys():
            if ("categories" == key and cmp(self.config[key], config[key])) or \
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
        self.telegram_send(STRINGS['test_success'])


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
        self.yarss2_plugin = component.get('CorePlugin.YaRSS2')
        self.yarss2_plugin.save_subscription(subscription_data=self.subscription_data, delete=False)
