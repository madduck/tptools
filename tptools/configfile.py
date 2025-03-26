import tomllib
import os.path
import pathlib
import platformdirs

from tptools.util import PACKAGE


def get_config_file_path(*, package=PACKAGE, filename="cfg.toml"):
    cfgdir = platformdirs.user_config_path(PACKAGE)

    localappdata = pathlib.Path(os.path.expandvars(r"%LOCALAPPDATA%"))
    userprofile = pathlib.Path(os.path.expandvars(r"%USERPROFILE%"))
    if cfgdir.is_relative_to(localappdata):
        cfgdir = r"%LOCALAPPDATA%" / cfgdir.relative_to(localappdata).parent

    if cfgdir.is_relative_to(userprofile):
        cfgdir = r"%USERPROFILE%" / cfgdir.relative_to(userprofile).parent

    elif cfgdir.is_relative_to(homedir := pathlib.Path.home()):
        cfgdir = "~" / cfgdir.relative_to(homedir)

    return cfgdir / filename


class ConfigFile:

    def __init__(self, path):
        self._data = {}
        self._path = pathlib.Path(os.path.expandvars(path)).expanduser()
        self._load_file(self._path)

    def _load_file(self, path):
        if path:
            with open(path, "rb") as f:
                self._data = tomllib.load(f)

    def get(self, key, default=None):
        rv = self._data
        try:
            keys = key.split(".")
            for k in keys[:-1]:
                rv = rv[k]

            return rv.get(keys[-1], default)

        except KeyError:
            return default

    def set(self, key, value):
        self._data[key] = value
