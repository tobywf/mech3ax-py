from __future__ import annotations

from enum import IntEnum
from struct import unpack_from
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

import pefile

from ..errors import Mech3ParseError, assert_eq


class LocaleID(IntEnum):
    English = 1033
    German = 1031
    French = 1036

    def __str__(self) -> str:  # pylint: disable=invalid-str-returned
        return self.name

    @staticmethod
    def from_string(value: str) -> LocaleID:
        try:
            return LocaleID[value]
        except KeyError:
            raise ValueError(value)


# All the English, German, and French locale IDs map to the same CP
CODEPAGE = "cp1252"

RT_MESSAGETABLE: int = pefile.RESOURCE_TYPE["RT_MESSAGETABLE"]


def _traverse_resources(root: Any, path: Sequence[int]) -> Tuple[int, int]:
    entries = root
    for segment in path:
        try:
            entry = next(entry for entry in entries if entry.id == segment)
        except StopIteration:  # pragma: no cover
            raise IndexError(segment) from None
        try:
            directory = entry.directory
        except AttributeError:
            return (entry.data.struct.OffsetToData, entry.data.struct.Size)
        else:
            entries = directory.entries

    readable = "/".join(str(segment) for segment in path)
    raise IndexError(f"{readable} not found")


def _read_messagetable_resource(data: bytes) -> Iterable[Tuple[int, str]]:
    (count,) = unpack_from("<I", data, 0)
    offset = 4

    for _ in range(count):
        low_id, high_id, offset_to_entries = unpack_from("<3I", data, offset)
        offset += 12
        for entry_id in range(low_id, high_id):
            length, flags = unpack_from("<2H", data, offset_to_entries)
            assert_eq("unicode flags", 0x0000, flags, offset_to_entries)
            offset_to_entries += 4
            length -= 4

            text = data[offset_to_entries : offset_to_entries + length]
            offset_to_entries += length
            entry_val = text.decode(CODEPAGE).rstrip("\x00\r\n")
            # entry_id is not contiguous
            yield entry_id, entry_val


def _extract_messagetable(dll: pefile.PE, locale_id: LocaleID) -> Mapping[int, str]:
    mmap = dll.get_memory_mapped_image()
    entries = dll.DIRECTORY_ENTRY_RESOURCE.entries
    offset, size = _traverse_resources(entries, (RT_MESSAGETABLE, 1, locale_id.value))

    data = mmap[offset : offset + size]
    return dict(_read_messagetable_resource(data))


def _extract_zlocids(dll: pefile.PE) -> Iterable[Tuple[str, int]]:
    try:
        data_section = next(
            section for section in dll.sections if section.Name.startswith(b".data\x00")
        )
    except StopIteration:  # pragma: no cover
        raise Mech3ParseError("No .data section found in PE file") from None

    offset = data_section.PointerToRawData
    length = data_section.SizeOfRawData
    data: bytes = dll.__data__[offset : offset + length]

    def _read_msg_name(offset: int) -> str:
        start = offset
        while data[offset] != 0:
            offset += 1

        return data[start:offset].decode("ascii")

    # table of message offsets and message table IDs written backwards, highest address
    # first. skip the CRT initialization section
    offset = 16
    while True:
        # the offset is actually 32 bits, and points to the RAM location, which is the
        # virtual address + DLL base address (0x10000000). however, by splitting this
        # up, the calculation becomes easier, and so does exiting the loop.
        virt_offset, base_offset, entry_id = unpack_from("<2HI", data, offset)
        offset += 8

        # the data isn't meant to be read like this; but this condition triggers
        # if we've read 4 bytes into the string data
        if base_offset != 4096:
            break

        rel_offset = virt_offset - data_section.VirtualAddress
        message_name = _read_msg_name(rel_offset)
        yield message_name, entry_id


def read_messages(pe: pefile.PE, locale_id: LocaleID) -> Mapping[str, Optional[str]]:
    message_table = _extract_messagetable(pe, locale_id)

    messages = {}
    for message_name, entry_id in _extract_zlocids(pe):
        messages[message_name] = message_table.get(entry_id)

    return messages
