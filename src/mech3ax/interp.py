from struct import Struct

INTERP_HEADER = Struct("<3I")
INTERP_RECORD = Struct("<120s4xI")
UINT32 = Struct("<I")
SIGNATURE = 0x08971119


def parse_script(data, offset, operations=None):
    script = []
    while True:
        (size,) = UINT32.unpack_from(data, offset)
        offset += UINT32.size

        # end of script
        if size == 0:
            break

        (arg_count,) = UINT32.unpack_from(data, offset)
        offset += UINT32.size

        operation = data[offset : offset + size].decode("ascii")
        offset += size

        if not operation.endswith("\0"):
            raise ValueError(
                f"Expected operation to end with '\\0' (but was {operation!r})"
            )
        args = operation.count("\0")
        if arg_count != args:
            raise ValueError(f"Expected {arg_count} arguments (but was {args})")

        script.append(operation.rstrip("\0"))

        if operation:
            operations.add((operation.split("\0")[0], arg_count - 1))

    return script


def extract_interp(data, operations=None):
    signature, seven, count = INTERP_HEADER.unpack_from(data, 0)
    if signature != SIGNATURE:
        raise ValueError(
            f"Expected {SIGNATURE:08X} signature (but was {signature:08X})"
        )
    if seven != 7:
        raise ValueError(f"Expected header field 2 to be 7 (but was {seven})")

    offset = INTERP_HEADER.size
    for _ in range(count):
        raw_name, script_offset = INTERP_RECORD.unpack_from(data, offset)
        offset += INTERP_RECORD.size
        name = raw_name.rstrip(b"\0").decode("ascii")
        yield name, parse_script(data, script_offset, operations)
