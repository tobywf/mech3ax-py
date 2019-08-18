from struct import Struct

UINT32 = Struct("<I")


def extract_materials(data):
    count, = UINT32.unpack_from(data, 0)
    offset = UINT32.size

    for _ in range(count):
        has_name = data[offset + 2] == 255
        offset += 40
        if has_name:
            length, = UINT32.unpack_from(data, offset)
            offset += UINT32.size
            name = data[offset : offset + length].decode("ascii")
            offset += length
        else:
            name = None
        yield name
