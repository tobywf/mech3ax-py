import logging
from datetime import datetime, timezone
from io import BytesIO
from struct import Struct
from typing import BinaryIO, Iterable, Sequence, Tuple

from pydantic import BaseModel

from ..errors import Mech3ParseError, assert_eq
from .utils import UINT32, ascii_zterm

INTERP_HEADER = Struct("<3I")
INTERP_ENTRY = Struct("<120s 2I")
assert INTERP_ENTRY.size == 128, INTERP_ENTRY.size

SIGNATURE = 0x08971119
VERSION = 7

LOG = logging.getLogger(__name__)


class Script(BaseModel):
    name: str
    timestamp: datetime
    lines: Sequence[str]


def _read_script_lines(data: bytes, offset: int) -> Tuple[Sequence[str], int]:
    lines = []
    while True:
        (size,) = UINT32.unpack_from(data, offset)
        offset += UINT32.size

        # end of script
        if size == 0:
            break

        (arg_count,) = UINT32.unpack_from(data, offset)
        offset += UINT32.size

        command = data[offset : offset + size].decode("ascii")
        assert_eq("argument count", arg_count, command.count("\0"), offset)
        assert_eq("command end", "\0", command[-1], offset)
        if " " in command:
            raise Mech3ParseError(
                f"Expected command to not contain spaces (at {offset})"
            )
        offset += size
        lines.append(command.rstrip("\0").replace("\0", " "))

    return lines, offset


def read_interp(data: bytes) -> Iterable[Script]:
    LOG.debug("Reading interpreter data...")
    signature, version, count = INTERP_HEADER.unpack_from(data, 0)
    LOG.debug(
        "Interp signature 0x%08x, version %d, count %d", signature, version, count
    )
    assert_eq("signature", SIGNATURE, signature, 0)
    assert_eq("version", VERSION, version, 4)

    offset = INTERP_HEADER.size
    script_info = []
    for i in range(count):
        LOG.debug("Reading entry %d at %d", i, offset)
        raw_name, last_modified, start = INTERP_ENTRY.unpack_from(data, offset)
        offset += INTERP_ENTRY.size
        name = ascii_zterm(raw_name)
        timestamp = datetime.fromtimestamp(last_modified, timezone.utc)
        script_info.append((name, timestamp, start))

    for name, timestamp, start in script_info:
        LOG.debug(
            "Script '%s', data at %d, last modified '%s'",
            name,
            start,
            timestamp.isoformat(),
        )
        assert_eq("offset", start, offset, name)
        lines, offset = _read_script_lines(data, offset)
        yield Script(name=name, timestamp=timestamp, lines=lines)

    assert_eq("offset", len(data), offset, name)
    LOG.debug("Read interpreter data")


def write_interp(f: BinaryIO, scripts: Iterable[Script]) -> None:
    LOG.debug("Writing interpreter data...")
    encoded = []
    for i, script in enumerate(scripts):
        LOG.debug("Encoding script %d '%s'", i, script.name)
        with BytesIO() as fp:
            for command in script.lines:
                # include trailing null
                size = len(command) + 1
                arg_count = command.count(" ") + 1
                fp.write(UINT32.pack(size))
                fp.write(UINT32.pack(arg_count))
                fp.write(command.replace(" ", "\0").encode("ascii"))
                # include trailing null
                fp.write(b"\0")
            # end of script
            fp.write(UINT32.pack(0))
            encoded.append((script, fp.getvalue()))

    count = len(encoded)
    f.write(INTERP_HEADER.pack(SIGNATURE, VERSION, count))

    offset = INTERP_HEADER.size + INTERP_ENTRY.size * count
    for script, value in encoded:
        LOG.debug(
            "Script '%s', data at %d, last modified '%s'",
            script.name,
            offset,
            script.timestamp.isoformat(),
        )
        raw_name = script.name.encode("ascii")
        last_modified = int(script.timestamp.timestamp())
        f.write(INTERP_ENTRY.pack(raw_name, last_modified, offset))
        offset += len(value)

    for _script, value in encoded:
        f.write(value)
    LOG.debug("Wrote interpreter data")
