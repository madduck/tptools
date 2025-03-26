import json
import pathlib


PACKAGE = pathlib.Path(__file__).parent.parent.name


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
