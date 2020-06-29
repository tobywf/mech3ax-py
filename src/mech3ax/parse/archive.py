"""Read and write ZArchive-based files.

A binary accurate output is produced by default. But this required reading and
writing the useless values in the table of contents ("garbage"). ZArchives don't
use these, and they are uninitialized memory written out, so usually safe to
discard. If they aren't required, ``b""`` may be supplied instead.

Additionally, duplicate names may be present in a ZArchive. If code reading and
writing archives wants to be binary accurate, then entries must be written in a
duplicate-compatible manner.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from struct import Struct
from typing import BinaryIO, Iterable, Union

from ..errors import Mech3ArchiveError, assert_eq
from .utils import ascii_zterm

TOC_FOOTER = Struct("<2I")
TOC_ENTRY = Struct("<2I 64s I 64s Q")
assert TOC_ENTRY.size == 148, TOC_ENTRY.size

# WARNING: the order is important, so Pydantic doesn't convert int -> datetime
Filetime = Union[int, datetime]
VERSION = 1
WINDOWS_EPOCH = datetime(1601, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)

LOG = logging.getLogger(__name__)


@dataclass
class ArchiveEntry:
    name: str
    start: int
    data: bytes
    flag: int
    comment: bytes
    write_time: Filetime


def filetime_to_datetime(filetime: int) -> Filetime:
    if filetime == 0:
        return WINDOWS_EPOCH

    micro, nano100 = divmod(filetime, 10)

    if nano100 != 0:
        # python cannot store anything less than microseconds. but if this is
        # set, it's likely garbage data (mechlib)
        return filetime

    delta = timedelta(microseconds=micro)
    return WINDOWS_EPOCH + delta


def datetime_to_filetime(timestamp: Filetime) -> int:
    if isinstance(timestamp, int):
        return timestamp

    if timestamp == WINDOWS_EPOCH:
        return 0

    delta = timestamp - WINDOWS_EPOCH
    return (delta // timedelta.resolution) * 10


def read_archive(data: bytes) -> Iterable[ArchiveEntry]:
    LOG.debug("Reading archive data...")
    offset = len(data) - TOC_FOOTER.size
    version, count = TOC_FOOTER.unpack_from(data, offset)
    LOG.debug("Archive version %d, count %d at %d", version, count, offset)
    assert_eq("archive version", VERSION, version, offset, Mech3ArchiveError)

    # the engine reads the TOC forward
    offset -= TOC_ENTRY.size * count

    for i in range(count):
        LOG.debug("Reading entry %d at %d", i, offset)
        start, length, raw_name, flag, comment, filetime = TOC_ENTRY.unpack_from(
            data, offset
        )
        offset += TOC_ENTRY.size
        write_time = filetime_to_datetime(filetime)
        name = ascii_zterm(raw_name)
        end = start + length
        LOG.debug("Entry '%s', data from %d to %d", name, start, end)
        yield ArchiveEntry(name, start, data[start:end], flag, comment, write_time)

    LOG.debug("Read archive data")


def write_archive(f: BinaryIO, entries: Iterable[ArchiveEntry]) -> None:
    LOG.debug("Writing archive data...")
    toc = []
    offset = 0
    for entry in entries:
        length = len(entry.data)
        LOG.debug("Entry '%s', data from %d to %d", entry.name, offset, offset + length)
        filetime = datetime_to_filetime(entry.write_time)
        entry_packed = TOC_ENTRY.pack(
            offset,
            length,
            entry.name.encode("ascii"),
            entry.flag,
            entry.comment,
            filetime,
        )
        toc.append(entry_packed)
        f.write(entry.data)
        offset += length

    for i, entry_packed in enumerate(toc):
        LOG.debug("Writing entry %d at %d", i, offset)
        f.write(entry_packed)
        offset += TOC_ENTRY.size

    count = len(toc)
    LOG.debug("Archive version %d, count %d at %d", VERSION, count, offset)
    f.write(TOC_FOOTER.pack(VERSION, count))
    LOG.debug("Wrote archive data")
