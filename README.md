# tptools — Tools to export data from TournamentSoftware

`tptools` is a collection of Python tools to facilitate working with [TournamentSoftware](https://www.tournamentsoftware.com/).

> [!NOTE]
> While TournamentSoftware seems to handle a variety of sports, *`tptools` was developed in the context of squash, and squash only*. Therefore, it is likely highly squash-specific. That said, patches to make it usable across other sports are welcome!

Under the hood, TournamentSoftware is a Microsoft Access Database (MDB) stored in a file that has the extension `.TP`, rather than `.mdb`. The mostpart of `tptools` is a collection of classes to make sense of the stored data, and provide usable data structures. These classes are arguably kept simple, and they cover only a small part of the functionality of TournamentSoftware, but they are test-covered, and hopefully make it possible to work with the data in ways better than trying to make sense of the actual data structures stored in the MDB file.

> [!IMPORTANT]
> The TP database is password-protected, and it is up to you to decide whether you want to obtain this password to be able to read the data, and where to get it. **`tptools` does not include this password, nor will we disclose it**, and none of the tools here will work without it.

In addition to simple Python classes, `tptools` provides a command-line utility designed to provide data to other tools, such as [Squore](https://squore.double-yellow.be/) and [tcboard](https://github.com/madduck/tcboard): `tpsrv`. See below for details.

> [!WARNING]
> Microsoft Access is not a database designed for concurrent access. `tpsrv` relies on TournamentSoftware writing out every change to the tournament data to the corresponding database file. This is probably not guaranteed to work, but it seems to be the case. It's entirely possible that on odd-numbered Tuesdays, with a crescent moon and only when it's not raining in the summer months, then changes won't be available to the tools within due time, and there is nothing that can be done given the design choices by TournamentSoftare. You've been warned.

## Preparation

To use `tptools`, you must prepare your Windows machine running TournamentSoftware as follows:

### Installing Python for Windows

`tptools` is written in Python, and thus you need to get Python running on Windows first. We need Python 3.11 or higher. The official installer can be downloaded from [Python.org](https://www.python.org/downloads/windows/) or installed via the Microsoft Store.

If installing from Python.org, please ensure to add `Python.exe` to the `PATH`:

![Screenshot of Python Installer](https://github.com/madduck/tptools/blob/main/assets/screenshots/win-install-python.png?raw=true)

Subsequently, please verify that you have a working Python installation, by opening the Command Prompt or PowerShell to run:

```
> python -c "print('It seems to work')"
It seems to work
```

Finally, you almost certainly need to upgrade `pip`, the "Package installer for Python", another good way to verify your installation is working:

```
> python.exe -m pip install --upgrade pip
[…]
> pip --version
pip 25.0.1 from C:\Users\martin\AppData\Local\Programs\Python\Python313\Lib\site-packages\pip (python 3.13)
```

### Installing the Microsoft Access Database Engine

I know way too little about Microsoft Windows or all their other stuff to make sense of how things are supposed to work, nor do I care. I run Windows in a virtual machine on top of Linux, with the sole purpose to run TournamentSoftware. I do not have Microsoft Office installed, and I think I read somewhere that the following is only necessary if you also do not have this software locally available.

The `pyodbc` repo has [a page on Connecting to Microsoft Access](https://github.com/mkleehammer/pyodbc/wiki/Connecting-to-Microsoft-Access) with more information.

To test whether you need to install the Microsoft Access Database Engine haha (sorry, I crack up every time someone mentions Microsoft and "database" in the same sentence), you can run the following:

```
> pip install pyodbc
> python -c "import pyodbc; print('No, I am fine' if [d for d in pyodbc.drivers() if '*.mdb' in d] else 'Yes, I need to install the engine')"
```

If you get a "Yes", please download and install the [Microsoft Access Database Engine 2016 Redistributable](https://www.microsoft.com/en-us/download/details.aspx?id=54920).

### Installing (and upgrading) `tptools`

`tptools` is under development and not yet published as an officially available Python software. To install `tptools`, please run the following command:

```
> pip install https://github.com/madduck/tptools/archive/refs/heads/main.zip
```

If you run this command again, it will download the latest version and upgrade any previously installed. Thus, please **also use this command regularly to upgrade your installation of `tptools`**.

To verify that `tptools` are working, you may now run e.g.

```
> tpsrv --help
Usage: tpsrv [OPTIONS]
[…]
```

### Configuring the Windows firewall

When `tpsrv` is invoked the first time, Windows is expected to raise a hand and ask about how to handle a new program trying to bind a port. This is impressive!

![Screenshot of Windows Firewall](https://github.com/madduck/tptools/blob/main/assets/screenshots/win-firewall.png?raw=true)

Please ensure to allow access for `Python.exe`. Unfortunately, doing so via this dialogue means that all Python scripts can use any port, but it's better than nothing. If you care about security, please make sure that only the actual listening port is open.

Once running, the server has two modes:

1. it provides HTTP endpoints, currently only for Squore:

2. it pushes information about all matches to all URLs provided, as well as the console, if `--stdout` is specified.

## Configuration

There is a common configuration file for `tptools` to get default settings from. These settings can then be overridden with command-line options. The configuration file must be in [TOML format](https://en.wikipedia.org/wiki/TOML) and lives in `$XDG_CONFIG_DIR/tptools/cfg.toml`, which is `%LOCALAPPDATA%\tptools\cfg.toml` on Windows. This location can be overridden by specifying `--cfgfile` on the command-line.

The following is an example of this configuration file:

```
[tpsrv]
port = 8080
tpfile = "%USERPROFILE%\Documents\Tournaments\Demo.tp"
tppasswd = "ThisIsNotTheRealPassword"
pollfreq = 15
urls = [ "http://tcboard/api/tp/matches" ]
```

[Squore](https://squore.double-yellow.be/) is an amazing app for Android that can be used to score matches. To facilitate its use, Squore can subscribe to a feed of matches for referees to pick from, such that the player data do not have to be entered manually.

## Usage of `tpsrv`

At its core, `tpsrv` is an asynchronous web server designed to serve data on
request to apps, such as Squore. The listening socket can be configured using CLI options.

It also has the ability to inform remote services, such as TCBoard, and send the current data there, whenever the data change. Look into the `--stdout` and `--url` options for this mode.

```
> tpsrv --help
Usage: tpsrv [OPTIONS] COMMAND [ARGS]...

  Serve match and player data via HTTP

Options:
  -c, --cfgfile PATH  Config file to read instead of default  [default:
                      %LOCALAPPDATA%\tptools\cfg.toml]
  -h, --host IP       Host to listen on (bind to)  [default: 0.0.0.0]
  -p, --port PORT     Port to listen on  [default: 8000; 1024<=x<=65535]
  -u, --url URL       POST data to this URL when the input changes
                      (can be specified more than once)
  -o, --stdout        Print data to stdout when the input changes
  -v, --verbose       Increase verbosity of log output
  -q, --quiet         Output as little information as possible
  --help              Show this message and exit.

Commands:
  tp  Serve match and player data from a TP file
```

The actual work is done by components, listed here as "Commands". For now, only `tp` exists as a sub-command, which causes `tpsrv` to read data from a TP file. In the future, other access methods will be provided, such as accessing SQlite exports, or maybe TournamentSoftware APIs.

Here is the `tp` sub-command:

```
> tpsrv.exe tp --help
Usage: tpsrv tp [OPTIONS] TP_FILE

  Serve match and player data from a TP file

Options:
  -u, --user UID          User name to access TP file  [default: Admin]
  -p, --passwd PASSWORD   Password to access TP file
  -f, --pollfreq SECONDS  Frequency in seconds to poll TP file in the absence
                          of inotify  [default: 30; x>=1]
  -c, --work-on-copy      Always make a copy of the TP file before reading it
  -a, --asynchronous      Access TP file asynchronously (BUGGY)
  --help                  Show this message and exit.
```

On Linux, `tpsrv tp` can use `inotify` to react to changes; On Windows, `tpsrv tp` must resort to polling at regular intervals, which can be controlled with `--pollfreq`.

In an ideal world, access to the TP file would be done asynchronously. However, due to [a bug in aioodbc](https://github.com/aio-libs/aioodbc/issues/463), this does not work reliably. Thus, `tpsrv tp` loads the TP file synchronously on change, which shouldn't be a problem in practice. Asynchronous mode can be activated with `--asynchhronous`, though here be dragons.

> [!NOTE]
> In the `winscripts` directory, you may find a batch file that starts `tpsrv tp` with a TP file, when you drag-drop the file onto the script. A little tool exists to create a shortcut to this file on the desktop, which you can run from the command prompt: `tpshortcut tpsrv tp`. Now you just need to drag the TP file onto this new shortcut, and the web server will be started (using the configuration file mentioned above for all the other settings).

### The Squore endpoints

These are accessible via `HTTP GET`:

   1. `/squore/players` — returns an alphabetically sorted list of all players in the tournament, one player per line;
   2. `/squore/matches` — returns matches scheduled in TournamentSoftware.

The `/squore/matches` endpoint can be controlled using query parameters:

| Parameter           | Type   | Effect                                 |
|---------------------|--------|----------------------------------------|
| `include_played`    | truthy | Include completed matches in output    |
| `include_not_ready` | truthy | Include unscheduled matches in output  |
| `court`             | text   | List matches on this court first       |
| `only_this_court`   | truthy | Do not include matches on other courts |

For instance:

```
> curl "http://192.0.2.34/squore/matches?court=3&only_this_court=1"
{"config": {"Placeholder_Match": "${time} Uhr : ${FirstOfList:~${A}~${A.name}~} - ${FirstOfList:~${B}~${B.name}~} (${field}) : ${result}"}, "\u00a03": [{"id": 38, "court": "3", "A": {"name":
…
```

The court parameter must match the exact court name used in TournamentSoftware.

> [!NOTE]
> The `config` dictionary served to Squore has yet to be parametrised and is currently hard-coded.

## Contributing

To contribute, please ensure you have the appropriate dependencies installed:

```
> pip install -e .[dev]
```

and then install the Git pre-commit hooks that ensure that any commits conform with the Flake8 and Black conventions used by this project:

```
> pre-commit install
```

## Legalese

`tptools` is © 2024–5 martin f. krafft <tptools@pobox.madduck.net>.

It is released under the terms of the MIT Licence.
