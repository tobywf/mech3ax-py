from struct import Struct
from typing import Any, Tuple

UINT32 = Struct("<I")

DEFAULT_NODE_NAME = b"Default_node_name"


def ascii_zterm_padded(buf: bytes) -> str:
    """Return a string from an ASCII-encoded, zero-terminated buffer.

    The first null character is searched for. Data following the terminator
    is verified as further null characters.

    :raises ValueError: If no null character was found in the buffer.
    :raises ValueError: If unexpected characters follow the terminator.
    :raises UnicodeDecodeError: If the string is not ASCII-encoded.
    """
    null_index = buf.find(b"\0")
    if null_index < 0:  # pragma: no cover
        raise ValueError("Null terminator not found")

    if not all(c == 0 for c in buf[null_index:]):  # pragma: no cover
        raise ValueError(f"Data after first null terminator ({buf[null_index:]!r})")
    return buf[:null_index].decode("ascii")


def ascii_zterm_node_name(buf: bytes) -> str:
    """Return a string from an ASCII-encoded, zero-terminated buffer.

    The first null character is searched for. Data following the terminator
    is verified as the default node name followed by null characters.

    :raises ValueError: If no null character was found in the buffer.
    :raises ValueError: If unexpected characters follow the terminator.
    :raises UnicodeDecodeError: If the string is not ASCII-encoded.
    """
    null_index = buf.find(b"\0")
    if null_index < 0:  # pragma: no cover
        raise ValueError("Null terminator not found")

    compare = bytearray(len(buf))
    compare[: len(DEFAULT_NODE_NAME)] = DEFAULT_NODE_NAME
    compare[: null_index + 1] = buf[: null_index + 1]

    if buf != compare:  # pragma: no cover
        raise ValueError(f"Data after first null terminator ({buf[null_index:]!r})")
    return buf[:null_index].decode("ascii")


def ascii_zterm_partition(buf: bytes) -> Tuple[str, bytes]:
    """Return a string and trailing data from an ASCII-encoded, zero-terminated
    buffer.

    The first null character is searched for. Data following the terminator
    is returned.

    :raises ValueError: If no null character was found in the buffer.
    :raises UnicodeDecodeError: If the string is not ASCII-encoded.
    """
    null_index = buf.find(b"\0")
    if null_index < 0:  # pragma: no cover
        raise ValueError("Null terminator not found")
    return buf[:null_index].decode("ascii"), buf[null_index + 1 :]


def pack_node_name(name: str, length: int) -> bytes:
    # assume length > len(DEFAULT_NODE_NAME)
    pack = bytearray(length)
    pack[: len(DEFAULT_NODE_NAME)] = DEFAULT_NODE_NAME
    name_raw = name.encode("ascii")
    offset = len(name_raw)
    pack[:offset] = name_raw
    pack[offset] = 0
    return bytes(pack)


class BinReader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0
        self.prev = 0

    def __len__(self) -> int:
        return len(self.data)

    def read(self, struct: Struct) -> Tuple[Any, ...]:
        values = struct.unpack_from(self.data, self.offset)
        self.prev = self.offset
        self.offset += struct.size
        return values

    def read_u32(self) -> int:
        (value,) = UINT32.unpack_from(self.data, self.offset)
        self.prev = self.offset
        self.offset += UINT32.size
        return value  # type: ignore

    def read_bytes(self, length: int) -> bytes:
        self.prev = self.offset
        self.offset += length
        value = self.data[self.prev : self.offset]
        return value

    def read_string(self) -> str:
        length = self.read_u32()
        return self.read_bytes(length).decode("ascii")
