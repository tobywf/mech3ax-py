import json


def ascii_zterm(raw):
    null_index = raw.find(b"\0")
    if null_index > -1:
        raw = raw[:null_index]
    return raw.decode("ascii")


def json_load(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def json_dump(path, obj, **kwargs):
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, **kwargs)
