from __future__ import annotations

import logging
from struct import Struct
from typing import BinaryIO, Iterable, List, Optional, Sequence

from pydantic import BaseModel

from ..errors import Mech3MaterialError, assert_eq, assert_in, assert_ne
from .gamez.node_data_read import read_node_data_object3d
from .gamez.node_data_write import write_node_data_object3d
from .model3d import read_mesh_data, read_mesh_info, write_mesh_data, write_mesh_info
from .models import Mesh, Object3d
from .utils import UINT32, BinReader, ascii_zterm_node_name, pack_node_name

LOG = logging.getLogger(__name__)

VERSION = 27
VERSION_DATA = UINT32.pack(VERSION)
FORMAT = 1
FORMAT_DATA = UINT32.pack(FORMAT)

MATERIAL_INFO = Struct("<2BH 3f I 3f 2I")
assert MATERIAL_INFO.size == 40, MATERIAL_INFO.size

NODE = Struct("<36s 3I 4B 3I 3I 2i 4I 4I 6f 6f 6f 5I")
assert NODE.size == 208, NODE.size


class Node(BaseModel):
    name: str
    bitfield: int
    object3d: Object3d
    mesh: Optional[Mesh] = None
    children: List[Node] = []
    unknown: List[float]
    node_ptr: int = 0
    model_ptr: int = 0
    parent_ptr: int = 0
    child_ptr: int = 0


Node.update_forward_refs()


def read_version(data: bytes) -> None:
    assert_eq("version end", 4, len(data), 0)
    (version,) = UINT32.unpack(data)
    assert_eq("version", VERSION, version, 0)


def read_format(data: bytes) -> None:
    assert_eq("format end", 4, len(data), 0)
    (fmt,) = UINT32.unpack(data)
    assert_eq("format", FORMAT, fmt, 0)


class Material(BaseModel):
    name: Optional[str]
    flag: int = 17
    unk: int = 0xFF
    rgb: int = 0x7FFF
    red: float = 255.0
    green: float = 255.0
    blue: float = 255.0
    pointer: int = 1


def read_materials(data: bytes) -> Iterable[Material]:
    reader = BinReader(data)
    LOG.debug("Reading materials data...")
    count = reader.read_u32()

    for i in range(count):
        LOG.debug("Reading material %d at %d", i, reader.offset)
        (
            unk00,
            flag,
            rgb,
            red,
            green,
            blue,
            pointer,
            unk20,
            unk24,
            unk28,
            unk32,
            cycle_ptr,
        ) = reader.read(MATERIAL_INFO)

        assert_in("field 00", (0x00, 0xFF), unk00, reader.prev + 0)
        assert_eq("field 20", 0.0, unk20, reader.prev + 20)
        assert_eq("field 24", 0.5, unk24, reader.prev + 24)
        assert_eq("field 28", 0.5, unk28, reader.prev + 28)
        assert_eq("field 32", 0, unk32, reader.prev + 32)
        assert_eq("cycle pointer", 0, cycle_ptr, reader.prev + 36)

        textured = (flag & 1) == 1

        if textured:
            # TODO: in GameZ, unk00 has to be 0xFF if textured
            assert_ne("pointer", 0, pointer, reader.prev + 16)
            assert_eq("rgb", 0x7FFF, rgb, reader.prev + 2)
            assert_eq("red", 255.0, red, reader.prev + 4)
            assert_eq("green", 255.0, green, reader.prev + 8)
            assert_eq("blue", 255.0, blue, reader.prev + 12)
        else:
            assert_eq("pointer", 0, pointer, reader.prev + 16)
            assert_eq("rgb", 0, rgb, reader.prev + 2)

        name: Optional[str] = None
        if textured:
            name = reader.read_string()

        yield Material(
            name=name,
            flag=flag,
            unk=unk00,
            rgb=rgb,
            red=red,
            green=green,
            blue=blue,
            pointer=pointer,
        )

    # make sure all the data is processed
    assert_eq("materials end", len(reader), reader.offset, reader.offset)
    LOG.debug("Read materials data")


def write_materials(f: BinaryIO, materials: Sequence[Material]) -> None:
    LOG.debug("Writing materials data...")
    count = len(materials)
    f.write(UINT32.pack(count))
    for i, material in enumerate(materials):
        LOG.debug("Writing material %d at %d", i, f.tell())
        textured = (material.flag & 1) == 1

        if textured:
            assert_ne("pointer", 0, material.pointer, i, Mech3MaterialError)
            assert_eq("name", True, bool(material.name), i, Mech3MaterialError)
        else:
            assert_eq("pointer", 0, material.pointer, i)

        packed = MATERIAL_INFO.pack(
            material.unk,
            material.flag,
            material.rgb,
            material.red,
            material.green,
            material.blue,
            material.pointer,
            0.0,
            0.5,
            0.5,
            0,
            0,
        )
        f.write(packed)
        if material.name:
            length = len(material.name)
            f.write(UINT32.pack(length))
            f.write(material.name.encode("ascii"))

    LOG.debug("Wrote materials data")


def _read_node(reader: BinReader) -> Node:  # pylint: disable=too-many-locals
    LOG.debug("Reading node at %d...", reader.offset)

    is_child = reader.offset != 0
    # fmt: off
    (
        part_name, bitfield036, zero040, one044, flag048, pad049, pad050, pad051,
        node_type, node_ptr, model_ptr, zero064, one068, action_cb_ptr, mone076, mone080,
        parent_count, parent_ptr, child_count, child_ptr,
        zero100, zero104, zero108, zero112,
        *unknown,  # 116-184
        zero188, zero192, unk196, zero200, zero204,
    ) = reader.read(NODE)
    # fmt: on

    bitfield_upper = bitfield036 & 0xFFFFF800
    assert_eq("bitfield upper", 0x3080000, bitfield_upper, reader.prev + 36)
    bitfield_lower = bitfield036 & 0x7FF

    assert_eq("field 040", 0, zero040, reader.prev + 40)
    assert_eq("field 044", 1, one044, reader.prev + 44)

    assert_eq("flag", 0xFF, flag048, reader.prev + 48)
    assert_eq("pad 049", 0, pad049, reader.prev + 49)
    assert_eq("pad 050", 0, pad050, reader.prev + 50)
    assert_eq("pad 051", 0, pad051, reader.prev + 51)

    assert_eq("node type", 5, node_type, reader.prev + 52)
    assert_ne("node ptr", 0, node_ptr, reader.prev + 56)

    assert_eq("field 064", 0, zero064, reader.prev + 64)
    assert_eq("field 068", 1, one068, reader.prev + 68)
    assert_eq("action cb ptr", 0, action_cb_ptr, reader.prev + 72)
    assert_eq("field 076", -1, mone076, reader.prev + 76)
    assert_eq("field 080", -1, mone080, reader.prev + 80)

    if is_child:
        assert_eq("parent count", 1, parent_count, reader.prev + 84)
        assert_ne("parent ptr", 0, parent_ptr, reader.prev + 88)
    else:
        assert_eq("parent count", 0, parent_count, reader.prev + 84)
        assert_eq("parent ptr", 0, parent_ptr, reader.prev + 88)

    if child_count == 0:  # 92
        assert_eq("child ptr", 0, child_ptr, reader.prev + 96)
    else:
        assert_ne("child ptr", 0, child_ptr, reader.prev + 96)

    assert_eq("field 100", 0, zero100, reader.prev + 100)
    assert_eq("field 104", 0, zero104, reader.prev + 104)
    assert_eq("field 108", 0, zero108, reader.prev + 108)
    assert_eq("field 112", 0, zero112, reader.prev + 112)

    assert_eq("field 188", 0, zero188, reader.prev + 188)
    assert_eq("field 192", 0, zero192, reader.prev + 192)
    assert_eq("field 196", 160, unk196, reader.prev + 196)
    assert_eq("field 200", 0, zero200, reader.prev + 200)
    assert_eq("field 204", 0, zero204, reader.prev + 204)

    # read object3d data if node_type == 5 (it always is)
    LOG.debug("Reading object 3D at %d...", reader.offset)
    object3d = read_node_data_object3d(reader)

    # read model data
    if model_ptr == 0:
        mesh: Optional[Mesh] = None
    else:
        LOG.debug("Reading mesh at %d...", reader.offset)
        wrapped_mesh = read_mesh_info(reader)
        mesh = read_mesh_data(reader, wrapped_mesh)
        LOG.debug("Read mesh")

    children = [_read_node(reader) for _ in range(child_count)]

    LOG.debug("Read node")

    return Node(
        name=ascii_zterm_node_name(part_name),
        bitfield=bitfield_lower,
        object3d=object3d,
        mesh=mesh,
        children=children,
        unknown=unknown,
        node_ptr=node_ptr,
        model_ptr=model_ptr,
        parent_ptr=parent_ptr,
        child_ptr=child_ptr,
    )


def read_model(data: bytes) -> Node:
    reader = BinReader(data)
    LOG.debug("Reading model...")
    root = _read_node(reader)
    assert_eq("model end", len(data), reader.offset, reader.offset)
    LOG.debug("Read model")
    return root


def write_model(f: BinaryIO, root: Node) -> None:
    LOG.debug("Writing model...")
    _write_node(f, root, is_child=False)
    LOG.debug("Wrote model")


def _write_node(f: BinaryIO, node: Node, is_child: bool = True) -> None:
    LOG.debug("Writing node...")

    # fmt: off
    values = NODE.pack(
        pack_node_name(node.name, 36),
        node.bitfield | 0x3080000,
        0, 1, 0xFF, 0, 0, 0,
        5, node.node_ptr,
        node.model_ptr if node.mesh else 0,
        0, 1, 0, -1, -1,
        1 if is_child else 0,
        node.parent_ptr if is_child else 0,
        len(node.children),
        node.child_ptr if node.children else 0,
        0, 0, 0, 0,
        *node.unknown,
        0, 0, 160, 0, 0,
    )
    # fmt: on
    f.write(values)

    LOG.debug("Writing Object3d...")
    write_node_data_object3d(f, node.object3d)
    LOG.debug("Wrote Object3d")

    if node.mesh:
        LOG.debug("Writing mesh...")
        write_mesh_info(f, node.mesh)
        write_mesh_data(f, node.mesh)
        LOG.debug("Wrote mesh")

    for child in node.children:
        _write_node(f, child)

    LOG.debug("Wrote node")
