import logging
from datetime import datetime, timezone
from io import BytesIO
from struct import Struct
from typing import BinaryIO, Iterable, Sequence

from pydantic import BaseModel

from ..errors import Mech3ParseError, assert_eq
from .utils import UINT32, BinReader, ascii_zterm

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


def _read_script_lines(reader: BinReader) -> Sequence[str]:
    lines = []
    while True:
        size = reader.read_u32()
        # end of script
        if size == 0:
            break

        arg_count = reader.read_u32()
        command = reader.read_bytes(size).decode("ascii")

        assert_eq("argument count", arg_count, command.count("\0"), reader.prev)
        assert_eq("command end", "\0", command[-1], reader.offset - 1)
        if " " in command:
            raise Mech3ParseError(
                f"Expected command to not contain spaces (at {reader.prev})"
            )
        lines.append(command.rstrip("\0").replace("\0", " "))

    return lines


def read_interp(data: bytes) -> Iterable[Script]:
    reader = BinReader(data)
    LOG.debug("Reading interpreter data...")
    signature, version, count = reader.read(INTERP_HEADER)
    LOG.debug(
        "Interp signature 0x%08x, version %d, count %d", signature, version, count
    )
    assert_eq("signature", SIGNATURE, signature, reader.prev + 0)
    assert_eq("version", VERSION, version, reader.prev + 4)

    script_info = []
    for i in range(count):
        LOG.debug("Reading entry %d at %d", i, reader.offset)
        raw_name, last_modified, start = reader.read(INTERP_ENTRY)
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
        assert_eq("offset", start, reader.offset, name)
        lines = _read_script_lines(reader)
        yield Script(name=name, timestamp=timestamp, lines=lines)

    assert_eq("interp end", len(reader), reader.offset, reader.offset)
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
