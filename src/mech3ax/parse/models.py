# pylint: disable=too-many-locals
from __future__ import annotations

import logging
from struct import Struct
from typing import List, Optional, Tuple

from pydantic import BaseModel

from ..errors import assert_eq, assert_gt, assert_in, assert_lt, assert_ne
from .utils import BinReader, ascii_zterm

VEC_3D = Struct("<3f")
assert VEC_3D.size == 12, VEC_3D.size
Vec3 = Tuple[float, float, float]

VEC_2D = Struct("<2f")
assert VEC_2D.size == 8, VEC_2D.size
Vec2 = Tuple[float, float]

NODE = Struct("<36s 3I 4B 3I 3I 2i 4I 4I 6f 6f 6f 5I")
assert NODE.size == 208, NODE.size

OBJECT3D = Struct("<I f 4f 3f 3f 3f 3f 3f 3f 12I")
assert OBJECT3D.size == 144, OBJECT3D.size

MODEL = Struct("<4I 5I 4I 5I 4I I")
assert MODEL.size == 92, MODEL.size

POLYGON = Struct("<9I")
assert POLYGON.size == 36, POLYGON.size


LOG = logging.getLogger(__name__)


class Polygon(BaseModel):
    vertex_indices: List[int]
    vertex_colors: List[Vec3]
    normal_indices: List[int]
    uv_coords: List[Vec2]
    texture_index: int


class Mesh(BaseModel):
    vertices: List[Vec3]
    normals: List[Vec3]
    polygons: List[Polygon]


class Object3D(BaseModel):
    flag: int
    rot_x: float
    rot_y: float
    rot_z: float
    trans_x: float
    trans_y: float
    trans_z: float


class Node(BaseModel):
    name: str
    bitfield: int
    object3d: Object3D
    mesh: Optional[Mesh] = None
    children: List[Node] = []


Node.update_forward_refs()


def _read_polygons(reader: BinReader, polygon_count: int) -> List[Polygon]:
    LOG.debug("Reading polygons...")

    poly_info = []
    for i in range(polygon_count):
        LOG.debug("Reading polygon info %d at %d", i, reader.offset)
        (
            vertex_info,
            unk04,
            vertex_ptr,
            normal_ptr,
            uv_ptr,
            color_ptr,
            unk_ptr,
            tex_index,
            texture_info,
        ) = reader.read(POLYGON)

        assert_lt("vertex info", 0x3FF, vertex_info, reader.prev + 0)
        assert_in("field 4", (0, 1), unk04, reader.prev + 4)

        # unk_bit = (vertex_info & 0x100) != 0
        vtx_bit = (vertex_info & 0x200) != 0
        verts_in_poly = vertex_info & 0xFF

        assert_gt("verts in poly", 0, verts_in_poly, reader.prev + 0)
        assert_ne("vertex ptr", 0, vertex_ptr, reader.prev + 8)

        has_normals = vtx_bit and (normal_ptr != 0)
        has_uvs = uv_ptr != 0

        assert_ne("color ptr", 0, color_ptr, reader.prev + 20)
        assert_ne("unknown ptr", 0, unk_ptr, reader.prev + 24)
        assert_eq("texture info", 0xFFFFFF00, texture_info, reader.prev + 32)

        poly_info.append((verts_in_poly, has_normals, has_uvs, tex_index))

    polygons: List[Polygon] = []
    for i, (verts_in_poly, has_normals, has_uvs, tex_index) in enumerate(poly_info):
        LOG.debug("Reading polygon data %d at %d", i, reader.offset)
        vertices = [reader.read_u32() for _ in range(verts_in_poly)]

        normals: List[int] = []
        if has_normals:
            normals = [reader.read_u32() for _ in range(verts_in_poly)]

        uv_coords: List[Vec2] = []
        if has_uvs:
            for _ in range(verts_in_poly):
                u, v = reader.read(VEC_2D)
                uv_coords.append((u, 1.0 - v))

        colors = [reader.read(VEC_3D) for _ in range(verts_in_poly)]

        polygon = Polygon(
            vertex_indices=vertices,
            normal_indices=normals,
            uv_coords=uv_coords,
            vertex_colors=colors,
            texture_index=tex_index,
        )
        polygons.append(polygon)

    LOG.debug("Read polygons")
    return polygons


def _read_mesh(reader: BinReader) -> Mesh:
    LOG.debug("Reading mesh at %d...", reader.offset)

    # fmt: off
    (
        file_ptr, zero04, unk08, use_count,
        polygon_count, vertex_count, normal_count, morph_count, light_count,
        zero36, zero40, zero44, zero48,
        polygon_ptr, vertex_ptr, normal_ptr, light_ptr, morph_ptr,
        _unk72, _unk76, _unk80, _unk84,
        zero88,
    ) = reader.read(MODEL)
    # fmt: on

    assert_eq("file ptr", 0, file_ptr, reader.prev + 0)
    assert_eq("field 04", 0, zero04, reader.prev + 4)
    assert_in("field 08", (2, 3), unk08, reader.prev + 8)
    assert_eq("use count", 1, use_count, reader.prev + 12)

    assert_eq("field 36", 0, zero36, reader.prev + 36)
    assert_eq("field 40", 0, zero40, reader.prev + 40)
    assert_eq("field 44", 0, zero44, reader.prev + 44)
    assert_eq("field 48", 0, zero48, reader.prev + 48)

    assert_eq("field 88", 0, zero88, reader.prev + 88)

    if vertex_count == 0:
        assert_eq("vertex ptr", 0, vertex_ptr, reader.prev + 56)
    else:
        assert_ne("vertex ptr", 0, vertex_ptr, reader.prev + 56)

    vertices = [reader.read(VEC_3D) for _ in range(vertex_count)]

    if normal_count == 0:
        assert_eq("normal ptr", 0, normal_ptr, reader.prev + 60)
    else:
        assert_ne("normal ptr", 0, normal_ptr, reader.prev + 60)

    normals = [reader.read(VEC_3D) for _ in range(normal_count)]

    assert_eq("morph count", 0, morph_count, reader.prev + 28)
    assert_eq("morph ptr", 0, morph_ptr, reader.prev + 68)

    assert_eq("light count", 0, light_count, reader.prev + 32)
    assert_eq("light ptr", 0, light_ptr, reader.prev + 64)

    if polygon_count == 0:
        assert_eq("polygon ptr", 0, polygon_ptr, reader.prev + 52)
        polygons: List[Polygon] = []
    else:
        assert_ne("polygon ptr", 0, polygon_ptr, reader.prev + 52)
        polygons = _read_polygons(reader, polygon_count)

    LOG.debug("Read mesh")

    return Mesh(vertices=vertices, normals=normals, polygons=polygons,)


def _read_object3d(reader: BinReader) -> Object3D:
    LOG.debug("Reading Object3D at %d...", reader.offset)

    # fmt: off
    (
        flag, opacity,
        zero008, zero012, zero016, zero020,
        rot_x, rot_y, rot_z,
        scale_x, scale_y, scale_z,
        _unk048, _unk052, _unk056,
        _unk060, _unk064, _unk068,
        _unk072, _unk076, _unk080,
        trans_x, trans_y, trans_z,
        *zeros
    ) = reader.read(OBJECT3D)
    # fmt: on

    assert_in("flag", (32, 40), flag, reader.prev + 0)
    assert_eq("opacity", 0.0, opacity, reader.prev + 4)

    assert_eq("field 08", 0.0, zero008, reader.prev + 8)
    assert_eq("field 12", 0.0, zero012, reader.prev + 12)
    assert_eq("field 16", 0.0, zero016, reader.prev + 16)
    assert_eq("field 20", 0.0, zero020, reader.prev + 20)

    # all values between (a generously rounded) PI
    assert_gt("rot x", -3.1416, rot_x, reader.prev + 24)
    assert_lt("rot x", 3.1416, rot_x, reader.prev + 24)

    assert_gt("rot y", -3.1416, rot_y, reader.prev + 28)
    assert_lt("rot y", 3.1416, rot_y, reader.prev + 28)

    assert_gt("rot z", -3.1416, rot_z, reader.prev + 32)
    assert_lt("rot z", 3.1416, rot_z, reader.prev + 32)

    assert_eq("scale x", 1.0, scale_x, reader.prev + 36)
    assert_eq("scale y", 1.0, scale_y, reader.prev + 40)
    assert_eq("scale z", 1.0, scale_z, reader.prev + 44)

    for i, zero in enumerate(zeros):
        assert_eq(f"field {i:02d}", 0, zero, reader.prev + 96 + 4 * i)

    LOG.debug("Read Object3D")

    return Object3D(
        flag=flag,
        rot_x=rot_x,
        rot_y=rot_y,
        rot_z=rot_z,
        trans_x=trans_x,
        trans_y=trans_y,
        trans_z=trans_z,
    )


def _read_node(reader: BinReader) -> Node:
    LOG.debug("Reading node at %d...", reader.offset)

    is_child = reader.offset != 0
    # fmt: off
    (
        part_name, bitfield036, zero040, one044, flag048, pad049, pad050, pad051,
        node_type, node_ptr, model_ptr, zero064, one068, action_cb_ptr, mone076, mone080,
        parent_count, parent_ptr, child_count, child_ptr,
        zero100, zero104, zero108, zero112,
        *_unk_values,  # 116-184
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
    object3d = _read_object3d(reader)

    # read model data
    if model_ptr == 0:
        mesh: Optional[Mesh] = None
    else:
        mesh = _read_mesh(reader)

    children = [_read_node(reader) for _ in range(child_count)]

    LOG.debug("Read node")

    return Node(
        name=ascii_zterm(part_name),
        bitfield=bitfield_lower,
        object3d=object3d,
        mesh=mesh,
        children=children,
    )


def read_model(data: bytes) -> Node:
    reader = BinReader(data)
    LOG.debug("Reading model...")
    root = _read_node(reader)
    assert_eq("model end", len(data), reader.offset, reader.offset)
    LOG.debug("Read model")
    return root
