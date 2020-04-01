from struct import unpack_from

import pefile

from .utils import json_dump

DEFAULT_ENGLISH_LOCALE_ID = 1033
DEFAULT_GERMAN_LOCALE_ID = 1031
DEFAULT_FRENCH_LOCALE_ID = 1036

# All the English, German, and French locale IDs map to the same CP
CODEPAGE = "cp1252"

RT_MESSAGETABLE = pefile.RESOURCE_TYPE["RT_MESSAGETABLE"]


def _traverse_resources(entries):
    items = {}
    for entry in entries:
        try:
            directory = entry.directory
        except AttributeError:
            offset = entry.data.struct.OffsetToData
            size = entry.data.struct.Size
            items[entry.id] = offset, size
        else:
            items[entry.id] = _traverse_resources(directory.entries)
    return items


def _read_messagetable_resource(data):
    (count,) = unpack_from("<I", data, 0)
    offset = 4

    for _ in range(count):
        low_id, high_id, offset_to_entries = unpack_from("<3I", data, offset)
        offset += 12
        for entry_id in range(low_id, high_id):
            length, flags = unpack_from("<2H", data, offset_to_entries)
            # no unicode flags
            assert flags == 0x0000, flags
            offset_to_entries += 4
            length -= 4
            text = data[offset_to_entries : offset_to_entries + length]
            offset_to_entries += length
            text = text.decode(CODEPAGE).rstrip("\x00\r\n")
            # entry_id is not contiguous
            yield entry_id, text


def _extract_messagetable(pe, locale_id):
    mmap = pe.get_memory_mapped_image()
    entries = pe.DIRECTORY_ENTRY_RESOURCE.entries  # pylint: disable=no-member
    root = _traverse_resources(entries)

    offset, size = root[RT_MESSAGETABLE][1][locale_id]
    data = mmap[offset : offset + size]
    return dict(_read_messagetable_resource(data))


def _extract_zlocids(pe):
    try:
        data_section = next(
            section for section in pe.sections if section.Name.startswith(b".data\x00")
        )
    except StopIteration:
        raise ValueError("No .data section found in PE file")

    data = pe.__data__[
        data_section.PointerToRawData : data_section.PointerToRawData
        + data_section.SizeOfRawData
    ]

    def _read_msg_name(offset):
        start = offset
        while data[offset] != 0:
            offset += 1

        return data[start:offset].decode("ascii")

    # table of message offsets and message table ids
    # written backwards, highest address first
    # first few elements may therefore be zeroed out
    offset = 0
    while True:
        virt_offset, unk, entry_id = unpack_from("<2HI", data, offset)
        offset += 8

        if unk == 0:
            continue

        # this seems to be the end condition
        if unk > 4096:
            break

        rel_offset = virt_offset - data_section.VirtualAddress
        message_name = _read_msg_name(rel_offset)
        yield message_name, entry_id


def extract_messages(dll_path, json_path, locale_id=DEFAULT_ENGLISH_LOCALE_ID):
    pe = pefile.PE(str(dll_path.resolve(strict=True)))

    message_table = _extract_messagetable(pe, locale_id)

    messages = {}
    for message_name, entry_id in _extract_zlocids(pe):
        messages[message_name] = message_table.get(entry_id)

    json_dump(json_path, messages, sort_keys=True)
