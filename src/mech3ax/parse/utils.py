import json
from pathlib import Path
from struct import Struct
from typing import Any

UINT32 = Struct("<I")


def ascii_zterm(buffer: bytes) -> str:
    """Return a string from an ASCII-encoded, zero-terminated buffer.

    The first null character is searched for. Any data following the terminator
    is discarded.

    :raises ValueError: If no null character was found in the buffer.
    """
    null_index = buffer.find(b"\0")
    if null_index < 0:
        raise ValueError("Null terminator not found")
    return buffer[:null_index].decode("ascii")


def json_load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def json_dump(path: Path, obj: Any, sort_keys: bool = False) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=sort_keys)
