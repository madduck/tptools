# tptools — Tools to export data from TournamentSoftware

`tptools` is a collection of Python tools to facilitate working with [TournamentSoftware](https://www.tournamentsoftware.com/) in the context of squash.

> [!NOTE]
> While TournamentSoftware seems to handle a variety of sports, *`tptools` was developed in the context of squash, and squash only*. Therefore, it is likely highly squash-specific. That said, patches to make it usable across other sports are welcome!

Under the hood, TournamentSoftware is a Microsoft Access "Database" (MDB) stored in a file that has the extension `.TP`, rather than `.mdb`. The mostpart of `tptools` is a collection of classes to make sense of the stored data, and provide usable data structures. These classes are arguably kept simple, and they cover only a small part of the functionality of TournamentSoftware, but they are test-covered, and hopefully make it possible to work with the data in ways better than trying to make sense of the actual data structures stored in the MDB file.

That said, as `tptools` stands on top of the shoulders of giants, and a lot of benefits are implicit because `tptools` uses the following:

* [SQLModel](https://sqlmodel.tiangolo.com/), which means you get [SQLAlchemy](https://sqlalchemy.org/) and [Pydantic](https://pydantic-docs.helpmanual.io/) for free;
* FastAPI, which also uses Pydantic, and gives you access to [Starlette](https://www.starlette.io/);
* [Click](https://click.palletprojects.com), which gives you a smooth user
  interface on the command-line, as well as [click-extra](https://kdeldycke.github.io/click-extra) mainly for configuration file handling. I've spun off [click-async-plugins](https://github.com/madduck/click-async-plugins) from this project, and am using it as a dependency now;
* [Uvicorn](https://www.uvicorn.org/), an ASGI server that can scale — note you should still put it behind a
  reverse proxy, such as NginX or Traefik;
* [HTTPX](https://www.python-httpx.org/), a modern, asynchronous HTTP client library;
* [Watchdog](https://github.com/gorakhargosh/watchdog/), which takes care of
  auto-reloading tournament data as they are changed, even on Windows;

> [!IMPORTANT]
> The TP database is password-protected, and it is up to you to decide whether you want to obtain this password to be able to read the data, and where to get it. **`tptools` does not include this password, nor will we disclose it**, and none of the tools here will work without it.

In addition to simple Python classes, `tptools` provides a command-line utility designed to provide data to other tools, such as [Squore](https://squore.double-yellow.be/) and [tcboard](https://github.com/madduck/tcboard): `tpsrv`, which does a couple of things:

1. it will monitor the tournament file for changes, and reload automatically;

1. it provides HTTP endpoints, currently only for
   [Squore](https://squore.double-yellow.be/) via the `squoresrv` subcommand;

3. it pushes information about the tournament on every change to all URLs provided to the `post` plugin, as well as the console, if the `stdout` plugin is invoked.

See below for details.

[Squore](https://squore.double-yellow.be/) is an amazing app for Android that can be used to score matches. To facilitate its use, Squore can subscribe to a feed of matches for referees to pick from, such that the player data do not have to be entered manually. In fact, Squore, and its awesome upstream, are the main reasons that `tptools` exist.

> [!WARNING]
> Microsoft Access is not a database, and certainly not capable of handling concurrent access. `tpsrv` relies on TournamentSoftware writing out every change to the tournament data to the corresponding database file. This is probably not guaranteed to work, but it seems to be the case. It's entirely possible that on odd-numbered Tuesdays, with a crescent moon and only when it's not raining in the summer months, then changes won't be available to the tools within due time, and there is nothing that can be done given the design choices by TournamentSoftare. You've been warned.

## Preparation

To use `tptools`, you must prepare your Windows machine running TournamentSoftware as follows:

### Installing Python for Windows

`tptools` is written in Python, and thus you need to get Python running on Windows first. We need Python 3.13 or higher. The official installer can be downloaded from [Python.org](https://www.python.org/downloads/windows/) or installed via the Microsoft Store.

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

When `tpsrv` is invoked the first time, Windows may raise a hand and ask about how to handle a new program trying to bind a port. This is impressive security from Microsoft!

![Screenshot of Windows Firewall](https://github.com/madduck/tptools/blob/main/assets/screenshots/win-firewall.png?raw=true)

Please ensure to allow access for `Python.exe`. Unfortunately, doing so via this dialogue means that all Python scripts can use any port, but it's better than nothing. If you care about security, please make sure that only the actual listening port is open.

If you don't get a pop-up, check out the "Windows Defender Firewall" inbound rules under "Advanced Settings". There, you may find that `python.exe` is already allowed for everything. This is impressive security from Microsoft!

And if this is not the case, here is how to poke a hole through the firewall:

```
netsh advfirewall firewall add rule name="Allow tpsrv access" protocol=TCP dir=in localport=8000 action=allow
```

Make sure to amend the port accordingly, if you choose to run `tpsrv` on a
different port.

## Configuration

There is a common configuration file for `tptools` to get default settings from. These settings can then be overridden with command-line options. The configuration file must be in [TOML format](https://en.wikipedia.org/wiki/TOML) and live in `$XDG_CONFIG_DIR/tptools/cfg.toml`, which is `%LOCALAPPDATA%\tptools\cfg.toml` on Windows.

The following is an example of this configuration file:

```
[tpsrv]
port = 8080

[tpsrv.post]
urls = [ "http://tcboard/api/tp" ]

[tpsrv.tp]
tpfile = "%USERPROFILE%\Documents\Tournaments\Demo.tp"
tppasswd = "ThisIsNotTheRealPassword"
```

## Usage of `tpsrv`

At its core, `tpsrv` is an asynchronous web server designed to serve data on
request to apps, such as Squore. The listening socket can be configured using CLI options or the aforementioned configuration file.

It also has the ability to inform remote services, such as [TCBoard](https://github.com/madduck/tcboard), and send the current data there, whenever the data change. Look into the `stdout` and `post` subcommands for these modes.

```
Usage: tpsrv [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

  Serve match and player data via HTTP

Options:
  -C, --config CONFIG_PATH  Location of the configuration file. Supports glob
                            pattern of local path and remote URL.  [default:
                            ~/.config/tptools/cfg.toml]
  -v, --verbose             Increase the default WARNING verbosity by one
                            level for each additional repetition of the
                            option.
  -h, --host IP             Host to listen on (bind to)  [default: 0.0.0.0]
  -p, --port PORT           Port to listen on  [default: 8000; 1024<=x<=65535]
  --help                    Show this message and exit.

Commands:
  debug      Monitor stdin for keypresses to trigger debugging functions
  post       Post raw (TP) JSON data to URLs on change
  sq-stdout  utput data as sent to Squore to stdout whenever the tournament changes
  squoresrv  Mount endpoints to serve data for Squore
  stdout     Output tournament data as JSON to stdout whenever it changes
  tp         Obtain match and player data from a TP file (or SQLite)
  tp-post    Post raw (TP) JSON data to URLs on change
  tp-stdout  Output raw (TP) data as JSON to stdout whenever it changes
```

The actual work is done by components/plugins, listed here as "Commands". Note that these commands can be "chained", i.e. multiple commands provided:

```
> tpsrv tp integration/anon_tournament.sqlite squoresrv stdout post -u http://tcboard/api/tp
```

The `tp` command reads tournament data, normally from TP files, but SQLite is
also supported.
There is [a little script](https://github.com/madduck/tptools/blob/main/util/tp2sqlite.sh) to convert a TP file into a SQLite database, which may be useful for testing (TP files cannot be easily read on non-Windows systems).

The above command reads tournament data from the included SQLite sample database,
and spawns a web server that is configured to serve endpoints for Squore, as
well as print data to `stdout` and POST the entire tournament to the provided
URL whenever the data change.

```
> tpsrv tp --help
Usage: tpsrv tp [OPTIONS] TPFILE

  Obtain match and player data from a TP file (or SQLite)

Options:
  -u, --user UID           User name to access TP file  [default: Admin]
  -p, --password PASSWORD  Password to access TP file
  --no-fire-on-startup     Do not load data ASAP on startup, only on change
  --help                   Show this message and exit.
```

On Linux, `tpsrv tp` uses `inotify` to react to changes (via `watchdog`); On Windows, `tpsrv tp` uses `watchdog` to spawn a background thread to monitor the file.

In an ideal world, access to the TP file would be done asynchronously. However, due to [a bug in aioodbc](https://github.com/aio-libs/aioodbc/issues/463), this does not work reliably. Thus, `tpsrv tp` loads the TP file synchronously on change, which shouldn't be a problem in practice. This may change in the future.

> [!NOTE]
> In the `winscripts` directory, you may find a batch file that starts `tpsrv tp` with a TP file, when you drag-drop the file onto the script. A little tool exists to create a shortcut to this file on the desktop, which you can run from the command prompt: `tpshortcut tpsrv tp`. Now you just need to drag the TP file onto this new shortcut, and the web server will be started (using the configuration file mentioned above for all the other settings).

### Debugging

`tpsrv` comes with a simple plugin to aid with debugging, which can be activated by adding the word `debug` to the command-line invocation. The command takes no arguments, but if it's active, you can hit `?` in the terminal running `tpsrv` to get a list of available key shortcuts:

```
Keys I know about for debugging:
  \n    Outputs a new line
  ^R    Simulate event that TPData was reloaded
  <Esc> Outputs a couple of newlines and the current time
  ^D    Prints debugging information on tasks and ITC
  +     Increase the logging level
  -     Decrease the logging level
  ?     Print this message
```

Note that this plugin currently only works on Linux, since I cannot be bothered
to figure out how Windows terminal works. Please feel free to submit a pull
request if you can make it slurp single characters from the terminal.

### Printing to `stdout` and `POST`ing data

Five commands exist to export data whenever the tournament updates. The commands
printing to `stdout` all output JSON and take a single argument `--indent` if
you want the output pretty-printed. The commands that handle `HTTP POST` take
one or more `--url` arguments and will post the data there.

| Command     | Data exported                                                        |
|-------------|----------------------------------------------------------------------|
| `tp-stdout` | Raw TP data (not really useful, and quite ugly)                      |
| `tp-post`   | Raw TP data (not really useful, and quite ugly)                      |
| `stdout`    | A simple tournament representation (players, draws, courts, matches) |
| `post`      | A simple tournament representation (players, draws, courts, matches) |
| `sq-stdout` | A view of the data sent to Squore (see below)                        |

### The Squore endpoints

```
Usage: tpsrv squoresrv [OPTIONS]

  Mount endpoints to serve data for Squore

Options:
  --api-mount-point MOUNTPOINT  API mount point for Squore endpoints
                                [default: /squore]
  --settings-json PATH          Path of file to serve when Squore requests app
                                settings  [default:
                                ../../ext/Squore.settings.json]
  --config-toml PATH            Path of file to use for Squore tournament &
                                match config  [default:
                                ../../ext/Squore.config.toml]
  --devmap-toml PATH            Path of file to use for device to court
                                mapping  [default: Squore.dev_court_map.toml]
  --help                        Show this message and exit.
```

When the `squoresrv` command is invoked, a couple of endpoints are mounted under
`/squore/v1` (the first part can be modified with `--api-mount-point`). The entire API is documented (thanks to FastAPI) at
`/squore/v1/docs`.

Note that `v1/` is part of the URL in an attempt to provide for future changes to the protocol. Consider this the `tptools` Squore API version.

#### Players

Requesting `GET /squore/v1/players` returns an alphabetically sorted list of all
players in the tournament, one player per line, as per the [Squore](https://squore.double-yellow.be/#ClubSite) specs. The following query string parameters can be passed to influence the result:

| Parameter         | Type    | Effect                                                         | Default |
|-------------------|---------|----------------------------------------------------------------|---------|
| `namejoinstr`     | string  | String to put between first and last name                      | " "     |
| `fnamemaxlen`     | integer | Maximum number of characters to display of the first name      | -1 (∞)  |
| `abbrjoinstr`     | string  | String to put between abbreviated first name and the last name | "."     |
| `teamjoinstr`     | string  | String to put between team players                             | "&"     |
| `merge_identical` | truthy  | Fuse e.g. clubs for teams from the same club                   | True    |
| `lnamefirst`      | truthy  | Whether to put the last name first                             | False   |
| `include_club`    | truthy  | Whether to include the players' clubs                          | False   |
| `include_country` | truthy  | Whether to include the players' countries                      | False   |

For instance:

```
> curl "http://tc/squore/v1/players?fnamemaxlen=2&lnamefirst=1
Alpha, Th.
Beta, Av.
…
```

#### Matches

The `/matches` endpoint can be controlled using query parameter, as
well. All of the above player parameters are usable, and influence the way
player names are rendered. The following match-specific parameters control the
output of matches:

| Parameter           | Type   | Effect                                      | Default    |
|---------------------|--------|---------------------------------------------|------------|
| `include_played`    | truthy | Include completed matches in output         | False      |
| `include_not_ready` | truthy | Include unscheduled matches in output       | False      |
| `court`             | string | List matches on this court first            | None       |
| `only_this_court`   | truthy | Do not include matches on other courts      | False      |
| `no_court_string`   | string | The string to use when no court is assigned | "No court" |
| include_location    | truthy | Whether to include location with court name | False      |

For instance:

```
> curl "http://tc/squore/v1/matches?court=3&only_this_court=1"
{"config": {"Placeholder_Match": "${time} Uhr : ${FirstOfList:~${A}~${A.name}~} - ${FirstOfList:~${B}~${B.name}~} (${field}) : ${result}"}, "\u00a03": [{"id": 38, "court": "3", "A": {"name":
…
```

The `config` dictionary comes directly from a
[TOML](https://en.wikipedia.org/wiki/TOML) file, which can be specified using
the `--config-toml` CLI argument. There is [an
example](https://github.com/madduck/tptools/blob/main/ext/Squore.config.toml) in the repository. This file can be used to influence the match format chosen by Squore for new matches, among other aspects. Also see the `/settings` endpoint below.

The court parameter must match the exact *ID* of the court used in TournamentSoftware. You can use `/courts` to get a list of courts to determine the IDs.

If there is no court parameter specified, the `/matches` endpoint tries to use a "device to court" map specifiable in a TOML file, which is `./Squore.dev_court_map.toml` by default. This file maps Squore device IDs to court IDs, like so:

```
KQBLPS = 6
LHNGLO = 1
PDDH9G = 3
```

Presence of this file will mean that Squore automatically expands the court corresponding to a device when the list of matches is being shown.

#### Feeds

By calling the `/feeds` endpoing, you can retrieve a list of feeds as expected by
Squore. In fact, when you add a feed to Squore, you are offered "tptools" as a
source for feeds:

![Screenshot of tptools as feed source in Squore](https://github.com/madduck/tptools/blob/main/assets/screenshots/squore-feeds.png?raw=true)

It is possible to pass any and all of the players and match parameters listed
above to this endpoint. They will be included in the individual feed URLs that make up the feed.

#### Settings

Finally, due to the amazing work done by Squore's upstream, it is now possible
to serve Squore app settings from `tptools` as well. These are read from a JSON
file that can be specified with `--settings-json`, and there's [an example
included](https://github.com/madduck/tptools/blob/main/ext/Squore.settings.json), as well.

Note that the Squore app, on its first run, will attempt to load these data from `http://squore/settings`. This enables you to configure a redirection, e.g. on a reverse proxy server, such as NginX:

```NginX
server {
  listen 80;
  listen [::]:80;

  server_name squore;

  location /settings {
    return 308 http://tc/squore/v1/settings$is_args$args;
  }
}
```

If the requesting device is found in the "device to court" map (see the
`/matches` endpoint above, `--devmap-toml` CLI argument), then the device will
be automatically have the appropriate court feed pre-selected.

## Contributing

To contribute, please ensure you have the appropriate dependencies installed:

```
> pip install -e .[dev]
```

and then install the Git pre-commit hooks that ensure that any commits conform
with the coding-style used by this project.

```
> pre-commit install
```

All code (except for the `tpsrv` CLI) is 100% test-covered, and all
contributions are expected to keep this up. Use `pytest` to run the test suite.

Note that all code is typed, and typing is part of test-coverage.

## TODO

In addition to various comments including the word "TODO" in the code, there are
a few things left to do:

* Test the CLI
* Test the HTTP API

## Legalese

`tptools` is © 2024–5 martin f. krafft <tptools@pobox.madduck.net>.

It is released under the terms of the MIT Licence.
