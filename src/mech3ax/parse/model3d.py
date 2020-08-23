# pylint: disable=too-many-locals
from __future__ import annotations

import logging
from struct import Struct
from typing import BinaryIO, List, Optional, cast

from pydantic import BaseModel

from ..errors import assert_eq, assert_gt, assert_in, assert_lt, assert_ne
from .models import MESH, OBJECT3D, POLYGON, VEC2, VEC3, Mesh, Polygon, Vec2, Vec3
from .utils import UINT32, BinReader, ascii_zterm_node_name, pack_node_name

NODE = Struct("<36s 3I 4B 3I 3I 2i 4I 4I 6f 6f 6f 5I")
assert NODE.size == 208, NODE.size

LOG = logging.getLogger(__name__)


class Object3D(BaseModel):
    flag: int
    rot_x: float
    rot_y: float
    rot_z: float
    trans_x: float
    trans_y: float
    trans_z: float
    unknown: List[float]


class Node(BaseModel):
    name: str
    bitfield: int
    object3d: Object3D
    mesh: Optional[Mesh] = None
    children: List[Node] = []
    unknown: List[float]
    node_ptr: int = 0
    model_ptr: int = 0
    parent_ptr: int = 0
    child_ptr: int = 0


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
            texture_index,
            texture_info,
        ) = reader.read(POLYGON)

        assert_lt("vertex info", 0x3FF, vertex_info, reader.prev + 0)
        assert_in("field 4", (0, 1), unk04, reader.prev + 4)

        unk_bit = (vertex_info & 0x100) != 0
        vtx_bit = (vertex_info & 0x200) != 0
        verts_in_poly = vertex_info & 0xFF

        assert_gt("verts in poly", 0, verts_in_poly, reader.prev + 0)
        assert_ne("vertex ptr", 0, vertex_ptr, reader.prev + 8)

        has_normals = vtx_bit and (normal_ptr != 0)
        has_uvs = uv_ptr != 0

        assert_ne("color ptr", 0, color_ptr, reader.prev + 20)
        assert_ne("unknown ptr", 0, unk_ptr, reader.prev + 24)
        assert_eq("texture info", 0xFFFFFF00, texture_info, reader.prev + 32)

        polygon = Polygon(
            vertex_indices=[],
            normal_indices=[],
            uv_coords=[],
            vertex_colors=[],
            texture_index=texture_index,
            texture_info=texture_info,
            # flag=unk04 == 1,
            unk04=unk04,
            unk_bit=unk_bit,
            vtx_bit=vtx_bit,
            vertex_ptr=vertex_ptr,
            normal_ptr=normal_ptr,
            uv_ptr=uv_ptr,
            color_ptr=color_ptr,
            unk_ptr=unk_ptr,
        )
        poly_info.append((verts_in_poly, has_normals, has_uvs, polygon))

    polygons: List[Polygon] = []
    for i, (verts_in_poly, has_normals, has_uvs, polygon) in enumerate(poly_info):
        LOG.debug("Reading polygon data %d at %d", i, reader.offset)
        polygon.vertex_indices = [reader.read_u32() for _ in range(verts_in_poly)]

        if has_normals:
            polygon.normal_indices = [reader.read_u32() for _ in range(verts_in_poly)]

        if has_uvs:
            for _ in range(verts_in_poly):
                u, v = cast(Vec2, reader.read(VEC2))
                polygon.uv_coords.append((u, 1.0 - v))

        polygon.vertex_colors = [
            cast(Vec3, reader.read(VEC3)) for _ in range(verts_in_poly)
        ]
        polygons.append(polygon)

    LOG.debug("Read polygons")
    return polygons


def _read_mesh(reader: BinReader) -> Mesh:
    LOG.debug("Reading mesh at %d...", reader.offset)

    (
        file_ptr,  # 00
        zero04,
        unk08,
        has_parents,  # 12
        polygon_count,  # 16
        vertex_count,  # 20
        normal_count,  # 24
        morph_count,  # 28
        light_count,  # 32
        zero36,
        zero40,
        zero44,
        zero48,
        polygon_ptr,  # 52
        vertex_ptr,  # 56
        normal_ptr,  # 60
        light_ptr,  # 64
        morph_ptr,  # 68
        unk72,
        unk76,
        unk80,
        unk84,
        zero88,
    ) = reader.read(MESH)

    assert_eq("file ptr", 0, file_ptr, reader.prev + 0)
    assert_eq("field 04", 0, zero04, reader.prev + 4)
    assert_in("field 08", (2, 3), unk08, reader.prev + 8)
    # TODO: in GameZ, this can be greater than 1
    assert_eq("has parents", 1, has_parents, reader.prev + 12)

    assert_eq("field 36", 0, zero36, reader.prev + 36)
    assert_eq("field 40", 0.0, zero40, reader.prev + 40)
    assert_eq("field 44", 0.0, zero44, reader.prev + 44)
    assert_eq("field 48", 0, zero48, reader.prev + 48)

    # meshes always have vertices and polygons
    assert_gt("polygon count", 0, polygon_count, reader.prev + 16)
    assert_ne("polygon ptr", 0, polygon_ptr, reader.prev + 52)

    assert_gt("vertex count", 0, vertex_count, reader.prev + 20)
    assert_ne("vertex ptr", 0, vertex_ptr, reader.prev + 56)

    if normal_count == 0:
        assert_eq("normal ptr", 0, normal_ptr, reader.prev + 60)
    else:
        assert_ne("normal ptr", 0, normal_ptr, reader.prev + 60)

    assert_eq("light count", 0, light_count, reader.prev + 32)
    assert_eq("light ptr", 0, light_ptr, reader.prev + 64)

    assert_eq("morph count", 0, morph_count, reader.prev + 28)
    assert_eq("morph ptr", 0, morph_ptr, reader.prev + 68)

    assert_eq("field 88", 0, zero88, reader.prev + 88)

    vertices = [cast(Vec3, reader.read(VEC3)) for _ in range(vertex_count)]
    normals = [cast(Vec3, reader.read(VEC3)) for _ in range(normal_count)]
    polygons = _read_polygons(reader, polygon_count)

    LOG.debug("Read mesh")

    return Mesh(
        vertices=vertices,
        normals=normals,
        morphs=[],
        lights=[],
        polygons=polygons,
        polygon_ptr=polygon_ptr,
        vertex_ptr=vertex_ptr,
        normal_ptr=normal_ptr,
        light_ptr=0,
        morph_ptr=0,
        file_ptr=file_ptr,
        zero04=zero04,
        has_parents=has_parents,
        unk08=unk08,
        unk40=zero40,
        unk44=zero44,
        unk72=unk72,
        unk76=unk76,
        unk80=unk80,
        unk84=unk84,
    )


def _read_object3d(reader: BinReader) -> Object3D:
    LOG.debug("Reading Object3D at %d...", reader.offset)

    # fmt: off
    (
        flag, opacity,
        zero008, zero012, zero016, zero020,
        rot_x, rot_y, rot_z,
        scale_x, scale_y, scale_z,
        unk048, unk052, unk056,
        unk060, unk064, unk068,
        unk072, unk076, unk080,
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
        unknown=[
            unk048,
            unk052,
            unk056,
            unk060,
            unk064,
            unk068,
            unk072,
            unk076,
            unk080,
        ],
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
    object3d = _read_object3d(reader)

    # read model data
    if model_ptr == 0:
        mesh: Optional[Mesh] = None
    else:
        mesh = _read_mesh(reader)

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


def _write_polygons(f: BinaryIO, polygons: List[Polygon]) -> None:
    LOG.debug("Writing polygons...")

    for polygon in polygons:
        vertex_info = len(polygon.vertex_indices)
        if polygon.unk_bit:
            vertex_info |= 0x100
        if polygon.vtx_bit:
            vertex_info |= 0x200

        values = POLYGON.pack(
            vertex_info,
            polygon.unk04,
            polygon.vertex_ptr,
            polygon.normal_ptr if polygon.normal_indices else 0,
            polygon.uv_ptr if polygon.uv_coords else 0,
            polygon.color_ptr,
            polygon.unk_ptr,
            polygon.texture_index,
            polygon.texture_info,
        )
        f.write(values)

    for polygon in polygons:
        for vertex in polygon.vertex_indices:
            f.write(UINT32.pack(vertex))
        for normal in polygon.normal_indices:
            f.write(UINT32.pack(normal))
        for u, v in polygon.uv_coords:
            f.write(VEC2.pack(u, 1.0 - v))
        for color in polygon.vertex_colors:
            f.write(VEC3.pack(*color))

    LOG.debug("Wrote polygons")


def _write_mesh(f: BinaryIO, mesh: Mesh) -> None:
    LOG.debug("Writing mesh...")

    polygon_count = len(mesh.polygons)
    vertex_count = len(mesh.vertices)
    normal_count = len(mesh.normals)
    morph_count = len(mesh.morphs)
    light_count = len(mesh.lights)

    values = MESH.pack(
        mesh.file_ptr,
        mesh.zero04,
        mesh.unk08,
        mesh.has_parents,
        polygon_count,
        vertex_count,
        normal_count,
        morph_count,
        light_count,
        0,
        mesh.unk40,
        mesh.unk44,
        0,
        mesh.polygon_ptr if polygon_count else 0,
        mesh.vertex_ptr if vertex_count else 0,
        mesh.normal_ptr if normal_count else 0,
        mesh.light_ptr if light_count else 0,
        mesh.morph_ptr if morph_count else 0,
        mesh.unk72,
        mesh.unk76,
        mesh.unk80,
        mesh.unk84,
        0,
    )
    f.write(values)

    for vertex in mesh.vertices:
        f.write(VEC3.pack(*vertex))

    for normal in mesh.normals:
        f.write(VEC3.pack(*normal))

    for morph in mesh.morphs:
        f.write(VEC3.pack(*morph))

    # TODO: lights

    _write_polygons(f, mesh.polygons)

    LOG.debug("Wrote mesh")


def _write_object3d(f: BinaryIO, object3d: Object3D) -> None:
    LOG.debug("Writing Object3D...")

    # fmt: off
    values = OBJECT3D.pack(
        object3d.flag, 0.0,
        0, 0, 0, 0,
        object3d.rot_x, object3d.rot_y, object3d.rot_z,
        1.0, 1.0, 1.0,
        *object3d.unknown,
        object3d.trans_x, object3d.trans_y, object3d.trans_z,
        0, 0, 0,
        0, 0, 0,
        0, 0, 0,
        0, 0, 0,
    )
    # fmt: on
    f.write(values)

    LOG.debug("Wrote Object3D")


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

    _write_object3d(f, node.object3d)
    if node.mesh:
        _write_mesh(f, node.mesh)

    for child in node.children:
        _write_node(f, child)

    LOG.debug("Wrote node")
