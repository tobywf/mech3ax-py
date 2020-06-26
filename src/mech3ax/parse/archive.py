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
from struct import Struct
from typing import BinaryIO, Iterable, Tuple

from ..errors import Mech3ArchiveError, assert_value
from .utils import ascii_zterm

TOC_FOOTER = Struct("<2I")
TOC_ENTRY = Struct("<2I 64s 76s")

ENTRIES = Iterable[Tuple[str, bytes, bytes]]
VERSION = 1

LOG = logging.getLogger(__name__)


def read_archive(data: bytes) -> ENTRIES:
    LOG.debug("Reading archive data...")
    offset = len(data) - TOC_FOOTER.size
    version, count = TOC_FOOTER.unpack_from(data, offset)
    LOG.debug("Archive version %d, count %d at %d", version, count, offset)
    assert_value("archive version", VERSION, version, offset, Mech3ArchiveError)

    # the engine reads the TOC forward
    offset -= TOC_ENTRY.size * count

    for i in range(count):
        LOG.debug("Reading entry %d at %d", i, offset)
        start, length, raw_name, garbage = TOC_ENTRY.unpack_from(data, offset)
        offset += TOC_ENTRY.size
        name = ascii_zterm(raw_name)
        end = start + length
        LOG.debug("Entry '%s', data from %d to %d", name, start, end)
        yield name, data[start : start + length], garbage

    LOG.debug("Read archive data")


def write_archive(f: BinaryIO, entries: ENTRIES) -> None:
    LOG.debug("Writing archive data...")
    toc = []
    offset = 0
    for name, data, garbage in entries:
        length = len(data)
        LOG.debug("Entry '%s', data from %d to %d", name, offset, offset + length)
        toc.append(TOC_ENTRY.pack(offset, length, name.encode("ascii"), garbage))
        f.write(data)
        offset += length

    for i, entry in enumerate(toc):
        LOG.debug("Writing entry %d at %d", i, offset)
        f.write(entry)
        offset += TOC_ENTRY.size

    count = len(toc)
    LOG.debug("Archive version %d, count %d at %d", VERSION, count, offset)
    f.write(TOC_FOOTER.pack(VERSION, count))
    LOG.debug("Wrote archive data")
