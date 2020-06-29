import logging
from enum import IntEnum
from struct import Struct
from typing import Any, BinaryIO, Sequence

from ..errors import Mech3ParseError, assert_eq
from .utils import UINT32

FLOAT = Struct("<f")

LOG = logging.getLogger(__name__)


class NodeType(IntEnum):
    Int = 1
    Float = 2
    Str = 3
    List = 4


def read_reader(data: bytes) -> Any:
    LOG.debug("Reading reader data...")
    offset = 0

    def _read_node() -> Any:
        nonlocal offset
        start = offset
        (node_type,) = UINT32.unpack_from(data, offset)
        offset += UINT32.size

        # this is too spammy, but useful for manual debug
        # LOG.debug("Node type %s at %s", node_type, start)

        if node_type == NodeType.Int:
            (value,) = UINT32.unpack_from(data, offset)
            offset += UINT32.size
            return value

        if node_type == NodeType.Float:
            (value,) = FLOAT.unpack_from(data, offset)
            offset += FLOAT.size
            return value

        if node_type == NodeType.Str:
            (count,) = UINT32.unpack_from(data, offset)
            offset += UINT32.size
            value = data[offset : offset + count].decode("ascii")
            offset += count
            return value

        if node_type == NodeType.List:
            (count,) = UINT32.unpack_from(data, offset)
            offset += UINT32.size

            # count is one bigger, because the engine stores the count as an
            # integer node as the first item of the list
            count -= 1

            if count == 0:
                return None

            values = [_read_node() for _ in range(count)]

            # lists cannot be turned into dictionaries, since there can be
            # duplicate keys

            return values

        raise Mech3ParseError(
            f"Expected node type to be 1-4, but was {node_type} (at {start})"
        )

    root = _read_node()
    # make sure all the data is processed
    assert_eq("reader end", len(data), offset, offset)
    LOG.debug("Read reader data")
    return root


def write_reader(f: BinaryIO, root: Any) -> int:
    LOG.debug("Writing reader data...")
    offset = 0

    def _write_bytes(node: bytes) -> None:
        nonlocal offset

        f.write(UINT32.pack(NodeType.Str))
        offset += UINT32.size

        count = len(node)
        f.write(UINT32.pack(count))
        offset += UINT32.size

        f.write(node)
        offset += count

    def _write_list(node: Sequence[Any]) -> None:
        nonlocal offset

        f.write(UINT32.pack(NodeType.List))
        offset += UINT32.size

        # count is one bigger, because the engine stores the count as an
        # integer node as the first item of the list
        count = len(node) + 1

        f.write(UINT32.pack(count))
        offset += UINT32.size

        for item in node:
            _write_node(item)

    def _write_node(node: Any) -> None:
        nonlocal offset

        # this is too spammy, but useful for manual debug
        # LOG.debug("Node %r at %s", node, offset)

        if isinstance(node, int):
            f.write(UINT32.pack(NodeType.Int))
            offset += UINT32.size
            f.write(UINT32.pack(node))
            offset += UINT32.size
        elif isinstance(node, float):
            f.write(UINT32.pack(NodeType.Float))
            offset += UINT32.size
            f.write(FLOAT.pack(node))
            offset += FLOAT.size
        elif isinstance(node, str):
            node = node.encode("ascii")
            _write_bytes(node)
        elif isinstance(node, bytes):
            _write_bytes(node)
        elif isinstance(node, list):
            _write_list(node)
        elif node is None:
            _write_list([])
        else:
            raise Mech3ParseError(
                f"Expected node type to be compatible, but was {type(node)} (at {offset})"
            )

    _write_node(root)

    LOG.debug("Wrote reader data")
    return offset
