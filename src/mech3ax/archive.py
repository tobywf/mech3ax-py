from struct import Struct

from .utils import ascii_zterm

ARCHIVE_FOOTER = Struct("<2I")
ARCHIVE_RECORD = Struct("<2I64s76x")


def extract_archive(data):
    offset = len(data) - ARCHIVE_FOOTER.size
    _, count = ARCHIVE_FOOTER.unpack_from(data, offset)
    for _ in range(count):
        # walk the table backwards
        offset -= ARCHIVE_RECORD.size
        start, length, name = ARCHIVE_RECORD.unpack_from(data, offset)
        name = ascii_zterm(name)
        yield name, data[start : start + length]
