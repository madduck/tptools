# tptools — Tools to export data from TournamentSoftware

`tptools` is a collection of Python tools to facilitate working with [TournamentSoftware](https://www.tournamentsoftware.com/).

> [!NOTE]
> While TournamentSoftware seems to handle a variety of sports, *`tptools` was developed in the context of squash, and squash only*. Therefore, it is likely highly squash-specific. That said, patches to make it usable across other sports are welcome!

Under the hood, TournamentSoftware is a Microsoft Access Database (MDB) stored in a file that has the extension `.TP`, rather than `.mdb`. The mostpart of `tptools` is a collection of classes to make sense of the stored data, and provide usable data structures. These classes are arguably kept simple, and they cover only a small part of the functionality of TournamentSoftware, but they are test-covered, and hopefully make it possible to work with the data in ways better than trying to make sense of the actual data structures stored in the MDB file.

> [!IMPORTANT]
> The TP database is password-protected, and it is up to you to decide whether you want to obtain this password to be able to read the data, and where to get it. **`tptools` does not include this password, nor will we disclose it**, and none of the tools here will work without it.

In addition to simple Python classes, `tptools` comprises a number of
command-line utilities (using these classes) that are mainly designed to
provide the data to other tools:

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

[to be continued]

## Contributing

To contribute, please ensure you have the appropriate dependencies installed:

```
$ pip install -e .[dev]
```

and then install the Git pre-commit hooks that ensure that any commits conform
with the Flake8 and Black conventions used by this project:

```
$ pre-commit install
```

## Legalese

`pngx` is © 2025 martin f. krafft <pngx@pobox.madduck.net>.

It is released under the terms of the MIT Licence.
