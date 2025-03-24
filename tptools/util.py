import json
import platformdirs
import os.path
import pathlib


PACKAGE = "tptools"


def json_dump_with_default(obj, methodname="json", **kwargs):
    def _default(obj):
        if callable(fn := getattr(obj, methodname, None)):
            return fn()

        return json.JSONEncoder().default(obj)

    return json.dumps(obj, default=_default, **kwargs)


def is_truish(value):
    if not value:
        return False

    if value is True:
        return True

    try:
        for letter in ("y", "j", "t"):
            if value.lower().startswith(letter):
                return True

    except AttributeError:
        pass

    try:
        if int(value):
            return True

    except ValueError:
        pass

    return False


def get_config_file_path(*, package=PACKAGE, filename="cfg.toml"):
    cfgdir = platformdirs.user_config_path(PACKAGE)

    localappdata = pathlib.Path(os.path.expandvars(r"%LOCALAPPDATA%"))
    userprofile = pathlib.Path(os.path.expandvars(r"%USERPROFILE%"))
    if cfgdir.is_relative_to(localappdata):
        cfgdir = r"%LOCALAPPDATA%" / cfgdir.relative_to(localappdata).parent

    if cfgdir.is_relative_to(userprofile):
        cfgdir = r"%USERPROFILE%" / cfgdir.relative_to(userprofile).parent

    elif cfgdir.is_relative_to(xdgdir := platformdirs.user_config_path()):
        cfgdir = r"$XDG_CONFIG_DIR" / cfgdir.relative_to(xdgdir)

    elif cfgdir.is_relative_to(homedir := pathlib.Path.home()):
        cfgdir = "~" / cfgdir.relative_to(homedir)

    return cfgdir / filename
