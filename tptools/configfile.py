import tomllib
import os.path
import pathlib


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
            raise KeyError(key)

    def set(self, key, value):
        self._data[key] = value
