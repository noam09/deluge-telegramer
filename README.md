## Telegramer

Telegramer is a Deluge plugin for sending notifications, adding and viewing torrents using [Telegram](https://telegram.org/) messenger. It features both a GTK and Web UI. 

The plugin runs a [Telegram bot](https://telegram.org/blog/bot-revolution) on the host machine which listens for commands the user sends, allowing you to list active torrents, download new torrents, and receive notifications when torrents are added to Deluge and when they finish downloading.

Since the bot runs locally and is owned by the same user running it, Telegramer provides the best of both worlds: [privacy](https://telegram.org/privacy) and [security](https://telegram.org/faq#security). Only you can execute your bot's commands.

## Requirements

Currently Telegramer has been tested mainly on Linux. Support for Windows is in the works.
Make sure you have Python [`setuptools`](https://pypi.python.org/pypi/setuptools#installation-instructions) installed in order to build the plugin.
The plugin itself requires the [`PyTelegramBotAPI`](https://github.com/eternnoir/pyTelegramBotAPI) Python module to be installed, as well as the [`requests`](http://docs.python-requests.org/) module.
To install these, use your operating system's package manager, install them manually, or use [`pip`](https://pip.pypa.io/en/stable/installing/):

```sh
$ pip install --upgrade PyTelegramBotAPI
$ pip install --upgrade requests
```

## Installation

Installing Telegramer is easy:
* [Determine Deluge Python version](http://dev.deluge-torrent.org/wiki/Troubleshooting#PythonVersion)
* Build or download a plugin egg:
    * To build a Python egg, [download the source code](https://github.com/noam09/deluge-telegramer/archive/master.zip) and extract the archive anywhere.
    * Open a Command Prompt or Terminal window and navigate to the extracted archive directory.
    * Run `python setup.py bdist_egg` to build the plugin. If you have Python 3 installed as well, you may need to run `python2 setup.py bdist_egg` instead.
    * To install the plugin using the Deluge GUI, go to `Preferences -> Plugins` and click `Install Plugin`. Locate the plugin egg and select it to install. You should be able to find it in the extracted archve directory, inside the `dist` directory.
    * For more detailed installation instructions, see the [Deluge wiki](http://dev.deluge-torrent.org/wiki/Plugins#InstallingPluginEggs).

After installing the plugin, restarting Deluge and the Deluge daemon is recommended to avoid errors. 

## Usage

After you've installed and enabled the plugin using the Deluge GTK or Web UI, you will need to configure a bot token and Telegram user ID. In order to do so, send a message to [@BotFather](https://telegram.me/BotFather) and create a new bot according to BotFather's instructions. Once you've created your bot, you will be able to generate a token for your newly created bot. Copy it to the plugin's configuration under "Telegram Bot Token". Before you continue, make sure you initiate a conversation with your new bot by sending it the `/start` command. 

Afterwards, send a message to [@MyIDbot](https://telegram.me/myidbot) and send it the `/getid` command to receive your Telegram user ID. Copy your user ID to the Telegramer's configuration under "Telegram User ID".

Now, test these settings by clicking the **`Test`** button. you should receive a message from your newly created bot. Hooray!

**Commands:** Send your bot the `/help` command to see what commands are supported.
* The `/list` command will allow you to see a list of all torrents, whereas the `/down` and `/up` commands will show you only those downloading or uploading. 
* The `/add` command allows you to add a torrent to Deluge, using either a magnet link, a torrent file URL, or an actual torrent file!
* Contact [@BotFather](https://telegram.me/BotFather) again to give your bot a profile photo, change its name, or add quick-access commands to your bot using `/setcommands`. 

**Categories:** You may also notice the Category fields in the Telegramer configuration panel. This is an optional feature which allows you to set pairs of Categories and matching Directories to which you would like to save torrent contents. For example, if you set `Category 1` to `Music` and `Directory 1` to `C:\Music` or `/home/Music`, your bot will prompt you save in the `Music` category when you use the `/add` command to add a new torrent. Now the torrent you download will be saved to the appropriate directory! Make sure the directories you set in the category configuration really exist, or else the categories won't show up as options when adding a new torrent.

**Labels:** 
In addition to Categories, you can use the built-in Label plugin to label torrents using existing labels or by creating a new label.

## Development

Want to contribute? Great!

If you have any suggestions for improvement or new features you think might help others, posting Issues and Pull Requests are always welcome.
If you'd like to help out, the next big goal is full support for Windows systems.

**Issues** can be reported on the GitHub [issue tracker](http://github.com/noam09/deluge-telegramer/issues), 
just make sure to post the issue with a clear title, description and a log snippet if you know how. Remember to close your issue once it's solved, and if you found the solution yourself, please comment so that others benefit from it.

**Feature requests** can also be posted on the GitHub [issue tracker](http://github.com/noam09/deluge-telegramer/issues).

**Support** the project by implementing new features, solving support tickets and providing bug fixes.

## Screenshots

GTK UI:

![preview thumb](http://i.imgur.com/aWh2i4e.jpg)

Web UI:

![preview thumb](http://i.imgur.com/GIkoCV3.jpg)

Example bot:

![preview thumb](http://i.imgur.com/qnZWIip.jpg)

Initiating communication with the new bot:

![preview thumb](http://i.imgur.com/h7TaMtz.jpg)

Typing a slash ("/") brings up the quick-access commands. These can be set by contacting [@BotFather](https://telegram.me/BotFather) and sending `/setcommands`.

![preview thumb](http://i.imgur.com/HoM9j6O.jpg)

When adding a new torrent, you will first be prompted to pick a category:

![preview thumb](http://i.imgur.com/VaBVlYs.jpg)

Afterwards you may pick an existing label, or create a new one:

![preview thumb](http://i.imgur.com/Obs3DZj.jpg)

Then just pick a type:

![preview thumb](http://i.imgur.com/gBYLQ5j.jpg)

You can add a new torrent URL:

![preview thumb](http://i.imgur.com/LYPDy3y.jpg)

Or you can send a .torrent file:

![preview thumb](http://i.imgur.com/jdGO6TI.jpg)

Or add a new magnet link:

![preview thumb](http://i.imgur.com/BiOh7lw.jpg)

You can always list the torrents Deluge is currently downloading:

![preview thumb](http://i.imgur.com/S7Zf2fN.jpg)

Once the download is complete, you may choose to receive a Telegram notification. You can then check the status of torrents you are seeding:

![preview thumb](http://i.imgur.com/CRdBwJa.jpg)

## Known Issues

* DestroyKeyboard doesn't work properly - Custom markup keyboard stays intact 

## License
This is free software under the GPL v3 open source license. Feel free to do with it what you wish, but any modification must be open sourced. A copy of the license is included.
