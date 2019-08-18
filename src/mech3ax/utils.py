import json


def ascii_zterm(bytestr):
    null_index = bytestr.find(b"\x00")
    if null_index > -1:
        binary = bytestr[:null_index]
    return binary.decode("ascii")


def json_load(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def json_dump(path, obj, **kwargs):
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, **kwargs)
