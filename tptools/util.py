import json
import pathlib


PACKAGE = pathlib.Path(__file__).parent.parent.name


def is_truish(value: Any) -> bool:
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
