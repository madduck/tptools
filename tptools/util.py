import json


def json_dump_with_default(obj, methodname="json", **kwargs):
    def _default(obj):
        if callable(fn := getattr(obj, methodname, None)):
            return fn()

        return json.JSONEncoder().default(obj)

    return json.dumps(obj, default=_default, **kwargs)


