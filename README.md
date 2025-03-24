# tptools — Tools to export data from TournamentSoftware

`tptools` is a collection of Python tools to facilitate working with [TournamentSoftware](https://www.tournamentsoftware.com/).

> [!NOTE]
> While TournamentSoftware seems to handle a variety of sports, *`tptools` was developed in the context of squash, and squash only*. Therefore, it is likely highly squash-specific. That said, patches to make it usable across other sports are welcome!

Under the hood, TournamentSoftware is a Microsoft Access Database (MDB) stored in a file that has the extension `.TP`, rather than `.mdb`. The mostpart of `tptools` is a collection of classes to make sense of the stored data, and provide usable data structures. These classes are arguably kept simple, and they cover only a small part of the functionality of TournamentSoftware, but they are test-covered, and hopefully make it possible to work with the data in ways better than trying to make sense of the actual data structures stored in the MDB file.

> [!IMPORTANT]
> The TP database is password-protected, and it is up to you to decide whether you want to obtain this password to be able to read the data, and where to get it. **`tptools` does not include this password, nor will we disclose it**, and none of the tools here will work without it.

In addition to simple Python classes, `tptools` comprises a number of command-line utilities (using these classes) that are mainly designed to provide the data to other tools:

* `squoresrv` — a simple web server to provide so-called "matches" and "players" feeds in the format expected by [Squore](https://squore.double-yellow.be/);

* `tpwatcher` — a worker that submits planned matches to a server, such as provided by [tcboard](https://github.com/madduck/tcboard).

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
> tpwatcher --help
Usage: tpwatcher [OPTIONS]

Options:
  -u, --url TEXT          URL to send events to (stdout if not provided)
  -i, --tpfile PATH       TP file to watch and read
  -U, --tpuser TEXT       User name to use for TP file  [default: Admin]
  -P, --tppasswd TEXT     Password to use for TP file
  -p, --pollsecs INTEGER  Frequency in seconds to poll TP file in the absence
                          of inotify
  -v, --verbose           Increase verbosity of log output
  -q, --quiet             Output as little information as possible
  -t, --test              Use test data for this run
  --help                  Show this message and exit.
```

## Configuration

All utilities in this package read a common configuration file to get default settings from. These settings can then be overridden with command-line options. The configuration file must be in [TOML format](https://en.wikipedia.org/wiki/TOML) and lives in `XDG_CONFIG_DIR/tptools/cfg.toml`, which is `%LOCALAPPDATA%\tptools\cfg.toml` on Windows. This location can be overridden by specifying `--cfgfile` on the command-line.

The following is an example of this configuration file:

```
tpfile = "%USERPROFILE%\Documents\Tournaments\Demo.tp"
tppasswd = "topfsiekrit"
pollfreq = 15

[squoresrv]
port = 8080
```

## Usage

### `squoresrv` — making matches available to Squore

[Squore](https://squore.double-yellow.be/) is an amazing app for Android that can be used to score matches. To facilitate its use, Squore can subscribe to a feed of matches for referees to pick from, such that the player data do not have to be entered manually.

> [!WARNING]
> Microsoft Access is not a database designed for concurrent access. `squoresrv` relies on TournamentSoftware writing out every change to the tournament data to the corresponding database file. This is probably not guaranteed to work, but it seems to be the case. It's entirely possible that on odd-numbered Tuesdays, with a crescent moon and only when it's not raining in the summer months, then changes won't be available to `squoresrv` within due time, and there is nothing that can be done given the design choices by TournamentSoftare. You've been warned.

`squoresrv` is an asynchronous web server that reads matches from TournamentSoftware and makes them available in the format expected by Squore:

```
$ squoresrv --help
Usage: squoresrv [OPTIONS]

Options:
  -i, --tpfile PATH       TP file to watch and read
  -U, --tpuser TEXT       User name to use for TP file  [default: Admin]
  -P, --tppasswd TEXT     Password to use for TP file
  -f, --pollsecs INTEGER  Frequency in seconds to poll TP file in the absence
                          of inotify  [default: 30]
  -h, --host TEXT         Host to listen on (bind to)  [default: 0.0.0.0]
  -p, --port INTEGER      Port to listen on  [default: 80]
  -c, --cfgfile PATH      Config file to read instead of default  [default:
                          %LOCALAPPDATA%\tptools\cfg.toml]
  -v, --verbose           Increase verbosity of log output
  -q, --quiet             Output as little information as possible
  -a, --asynchronous      Query database asynchronously (BUGGY!)
  --help                  Show this message and exit.
```

The options relating to accessing the TP file have to be provided. The two options `--host` and `--port` are optional, and if not provided, then the web server will bind to port 80 on all local interfaces/IPs.

> [!NOTE]
> In the `winscripts` directory, you may find a batch file that starts `squoresrv` with a TP file, when you drag-drop the file onto the script. A little tool exists to create a shortcut to this file on the desktop, which you can run from the command prompt: `tpshortcut squoresrv`. Now you just need to drag the TP file onto this new shortcut, and the web server will be started (using the configuration file mentioned above).

Once running, the server provides two HTTP `GET` endpoints:

1. `/players` — returns an alphabetically sorted list of all players in the tournament, one player per line;
2. `/matches` — returns matches scheduled in TournamentSoftware.

The `/matches` endpoint can be controlled using query parameters:

| Parameter           | Type   | Effect                                 |
|---------------------|--------|----------------------------------------|
| `include_played`    | truthy | Include completed matches in output    |
| `include_not_ready` | truthy | Include unscheduled matches in output  |
| `court`             | text   | List matches on this court first       |
| `only_this_court`   | truthy | Do not include matches on other courts |

For instance:

```
$ curl "http://192.0.2.34/matches?court=3&only_this_court=1"
{"config": {"Placeholder_Match": "${time} Uhr : ${FirstOfList:~${A}~${A.name}~} - ${FirstOfList:~${B}~${B.name}~} (${field}) : ${result}"}, "\u00a03": [{"id": 38, "court": "3", "A": {"name":
…
```

The court parameter must match the exact court name used in TournamentSoftware.

> [!NOTE]
> The `config` dictionary has yet to be parametrised and is currently hard-coded.

#### Configuring the Windows firewall

When `squoresrv` is invoked the first time, Windows is expected to raise a hand and ask about how to handle a new program trying to bind a port. This is impressive!

![Screenshot of Windows Firewall](https://github.com/madduck/tptools/blob/main/assets/screenshots/win-firewall.png?raw=true)

Please ensure to allow access for `Python.exe`. Unfortunately, doing so via this dialogue means that all Python scripts can use any port, but it's better than nothing. If you care about security, please make sure that only the actual listening port is open.

#### A note on TP file access — polling, and synchronous access

`squoresrv` was designed to access the TP file asynchronously. In an ideal world, a modification of the TP file would trigger a reload. Then, when a client requests e.g. the list of matches, the data could be served quickly from cache.

Unfortunately, Windows does not provide a sensible means to react to a file system event, like `inotify` on Linux. Therefore, `squoresrv` regularly polls the file to see if it's been modified (relying on the modification time stamp). The frequency defaults to 30 seconds, and can be controlled with the `--frequency` CLI option.

And furthermore, there is [a bug in the Python aioodbc library](https://github.com/aio-libs/aioodbc/issues/463) and database access fails after a handful of changes, therefore making asynchronous access to the database currently impossible.

Therefore, `squoresrv` currently defaults to synchronous access, meaning that *for every HTTP request*, it has to load the TP file, parse the data, and massage it into the Squore format. While this is terribly ugly, it seems that in practical terms, this isn't an issue. Reading and parsing happens in a fraction of a second, and there's hardly ever a situation wherein more than a handful of tablets request the matches feed at the exact same time.

Asynchronous access can be turned on with `--asynchronous`, but here be dragons.

## Contributing

To contribute, please ensure you have the appropriate dependencies installed:

```
$ pip install -e .[dev]
```

and then install the Git pre-commit hooks that ensure that any commits conform with the Flake8 and Black conventions used by this project:

```
$ pre-commit install
```

## Legalese

`tptools` is © 2024–5 martin f. krafft <tptools@pobox.madduck.net>.

It is released under the terms of the MIT Licence.
