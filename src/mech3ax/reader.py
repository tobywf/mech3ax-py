from struct import Struct

from .archive import extract_archive
from .utils import json_dump

UINT32 = Struct("<I")
FLOAT = Struct("<f")


def extract_nodes(zrd):
    offset = 0

    def _read_node(zrd):
        nonlocal offset
        node_type, = UINT32.unpack_from(zrd, offset)
        offset += UINT32.size

        # uint32
        if node_type == 1:
            value, = UINT32.unpack_from(zrd, offset)
            offset += UINT32.size
            return value

        # float
        if node_type == 2:
            value, = FLOAT.unpack_from(zrd, offset)
            offset += FLOAT.size
            return value

        # string
        if node_type == 3:
            count, = UINT32.unpack_from(zrd, offset)
            offset += UINT32.size
            value = zrd[offset : offset + count].decode("ascii")
            offset += count
            return value

        # list
        if node_type == 4:
            count, = UINT32.unpack_from(zrd, offset)
            offset += UINT32.size

            # count is one bigger, because in the code this first item
            # of the list stores the item count
            count -= 1

            if count == 0:
                return None

            # special case to aid readability
            if count == 1:
                return _read_node(zrd)

            values = [_read_node(zrd) for i in range(count)]

            # special munging to turn a list of keys and values into a dict
            is_even = count % 2 == 0
            has_keys = all(isinstance(s, str) for s in values[::2])
            if is_even and has_keys:
                i = iter(values)
                values = dict(zip(i, i))

            return values

        raise ValueError(f"Invalid reader node type {node_type} in zRdrRead()")

    ret = _read_node(zrd)
    # make sure all the data is processed
    assert offset >= len(zrd), f"{offset} >= {len(zrd)}"
    return ret


def extract_reader(reader_path, base_path):
    data = reader_path.read_bytes()

    for name, zrd in extract_archive(data):
        json_path = base_path / name.replace(".zrd", ".json")
        json_dump(json_path, extract_nodes(zrd))
