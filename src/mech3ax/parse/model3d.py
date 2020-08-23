import logging
from dataclasses import dataclass
from typing import BinaryIO, List, cast

from ..errors import (
    assert_between,
    assert_eq,
    assert_gt,
    assert_in,
    assert_lt,
    assert_ne,
)
from .models import LIGHT, MESH, POLYGON, VEC2, VEC3, Light, Mesh, Polygon, Vec2, Vec3
from .utils import UINT32, BinReader

LOG = logging.getLogger(__name__)


@dataclass
class MeshWrapper:
    mesh: Mesh
    vertex_count: int
    normal_count: int
    morph_count: int
    light_count: int
    polygon_count: int


def _read_vec3s(reader: BinReader, count: int) -> List[Vec3]:
    if not count:
        return []
    return [cast(Vec3, reader.read(VEC3)) for _ in range(count)]


def _read_lights(  # pylint: disable=too-many-locals
    reader: BinReader, count: int
) -> List[Light]:
    lights_and_counts = []
    for _ in range(count):
        (
            unk00,  # 00
            unk04,  # 04
            unk08,  # 08
            extra_count,  # 12
            unk16,  # 16
            unk20,  # 20
            unk24,  # 24
            unk28,  # 28
            unk32,  # 32
            unk36,  # 36
            unk40,  # 40
            ptr,  # 44
            unk48,  # 48
            unk52,  # 52
            unk56,  # 56
            unk60,  # 60
            unk64,  # 64
            unk68,  # 68
            unk72,  # 72
        ) = reader.read(LIGHT)

        light = Light(
            unk00=unk00,
            unk04=unk04,
            unk08=unk08,
            extra=[],
            unk16=unk16,
            unk20=unk20,
            unk24=unk24,
            unk28=unk28,
            unk32=unk32,
            unk36=unk36,
            unk40=unk40,
            ptr=ptr,
            unk48=unk48,
            unk52=unk52,
            unk56=unk56,
            unk60=unk60,
            unk64=unk64,
            unk68=unk68,
            unk72=unk72,
        )
        lights_and_counts.append((light, extra_count))

    lights = []
    for light, extra_count in lights_and_counts:
        light.extra = _read_vec3s(reader, extra_count)
        lights.append(light)

    return lights


def _read_polygons(  # pylint: disable=too-many-locals
    reader: BinReader, count: int
) -> List[Polygon]:
    # too spammy
    # LOG.debug("Reading polygons...")

    poly_info = []
    for _ in range(count):
        # LOG.debug("Reading polygon info %d at %d", i, reader.offset)
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
        assert_between("field 4", 0, 20, unk04, reader.prev + 4)

        unk_bit = (vertex_info & 0x100) != 0
        vtx_bit = (vertex_info & 0x200) != 0
        verts_in_poly = vertex_info & 0xFF

        assert_gt("verts in poly", 0, verts_in_poly, reader.prev + 0)
        assert_ne("vertex ptr", 0, vertex_ptr, reader.prev + 8)

        has_normals = vtx_bit and (normal_ptr != 0)
        has_uvs = uv_ptr != 0

        assert_ne("color ptr", 0, color_ptr, reader.prev + 20)
        assert_ne("unknown ptr", 0, unk_ptr, reader.prev + 24)
        # assert_eq("texture info", 0xFFFF0101, texture_info, reader.prev + 32)

        polygon = Polygon(
            vertex_indices=[],
            normal_indices=[],
            uv_coords=[],
            vertex_colors=[],
            texture_index=texture_index,
            texture_info=texture_info,
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
    # for i, (verts_in_poly, has_normals, has_uvs, polygon) in enumerate(poly_info):
    for verts_in_poly, has_normals, has_uvs, polygon in poly_info:
        # LOG.debug("Reading polygon data %d at %d", i, reader.offset)
        polygon.vertex_indices = [reader.read_u32() for _ in range(verts_in_poly)]

        if has_normals:
            polygon.normal_indices = [reader.read_u32() for _ in range(verts_in_poly)]

        if has_uvs:
            for _ in range(verts_in_poly):
                u, v = cast(Vec2, reader.read(VEC2))
                polygon.uv_coords.append((u, 1.0 - v))

        polygon.vertex_colors = _read_vec3s(reader, verts_in_poly)
        polygons.append(polygon)

    # LOG.debug("Read polygons")
    return polygons


def read_mesh_info(  # pylint: disable=too-many-locals
    reader: BinReader,
) -> MeshWrapper:
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
        unk40,
        unk44,
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

    # TODO
    assert_in("file ptr", (0, 1), file_ptr, reader.prev + 0)
    assert_in("field 04", (0, 1), zero04, reader.prev + 4)
    # assert_le("field 08", 16, unk08, reader.prev + 8)
    assert_gt("has parents", 0, has_parents, reader.prev + 12)

    assert_eq("field 36", 0, zero36, reader.prev + 36)
    # TODO: float? 1014350479 = 0.014999999664723873
    # assert_eq("field 40", 0, zero40, reader.prev + 40)
    # TODO: float? 1032805417 = 0.07000000029802322
    # assert_eq("field 44", 0, zero44, reader.prev + 44)
    assert_eq("field 48", 0, zero48, reader.prev + 48)

    if polygon_count == 0:
        assert_eq("polygon ptr", 0, polygon_ptr, reader.prev + 52)
        # this is a really weird case where the model only has light info
        assert_eq("vertex count", 0, vertex_count, reader.prev + 20)
        assert_eq("normal count", 0, normal_count, reader.prev + 24)
        assert_eq("morph count", 0, morph_count, reader.prev + 28)
        assert_gt("light count", 0, light_count, reader.prev + 32)
    else:
        assert_ne("polygon ptr", 0, polygon_ptr, reader.prev + 52)

    if vertex_count == 0:
        assert_eq("vertex ptr", 0, vertex_ptr, reader.prev + 56)
    else:
        assert_ne("vertex ptr", 0, vertex_ptr, reader.prev + 56)

    if normal_count == 0:
        assert_eq("normal ptr", 0, normal_ptr, reader.prev + 60)
    else:
        assert_ne("normal ptr", 0, normal_ptr, reader.prev + 60)

    if light_count == 0:
        assert_eq("light ptr", 0, light_ptr, reader.prev + 64)
    else:
        assert_ne("light ptr", 0, light_ptr, reader.prev + 64)

    if morph_count == 0:
        assert_eq("morph ptr", 0, morph_ptr, reader.prev + 68)
    else:
        assert_ne("morph ptr", 0, morph_ptr, reader.prev + 68)

    assert_eq("field 88", 0, zero88, reader.prev + 88)

    mesh = Mesh(
        vertices=[],
        normals=[],
        morphs=[],
        lights=[],
        polygons=[],
        polygon_ptr=polygon_ptr,
        vertex_ptr=vertex_ptr,
        normal_ptr=normal_ptr,
        light_ptr=light_ptr,
        morph_ptr=morph_ptr,
        file_ptr=file_ptr,
        zero04=zero04,
        has_parents=has_parents,
        unk08=unk08,
        unk40=unk40,
        unk44=unk44,
        unk72=unk72,
        unk76=unk76,
        unk80=unk80,
        unk84=unk84,
    )

    return MeshWrapper(
        mesh=mesh,
        vertex_count=vertex_count,
        normal_count=normal_count,
        morph_count=morph_count,
        light_count=light_count,
        polygon_count=polygon_count,
    )


def read_mesh_data(reader: BinReader, wrapped_mesh: MeshWrapper) -> Mesh:
    mesh = wrapped_mesh.mesh

    mesh.vertices = _read_vec3s(reader, wrapped_mesh.vertex_count)
    mesh.normals = _read_vec3s(reader, wrapped_mesh.normal_count)
    mesh.morphs = _read_vec3s(reader, wrapped_mesh.morph_count)
    if wrapped_mesh.light_count:
        mesh.lights = _read_lights(reader, wrapped_mesh.light_count)
    if wrapped_mesh.polygon_count:
        mesh.polygons = _read_polygons(reader, wrapped_mesh.polygon_count)

    return mesh


def write_mesh_info(f: BinaryIO, mesh: Mesh) -> None:
    data = MESH.pack(
        mesh.file_ptr,
        mesh.zero04,
        mesh.unk08,
        mesh.has_parents,
        len(mesh.polygons),
        len(mesh.vertices),
        len(mesh.normals),
        len(mesh.morphs),
        len(mesh.lights),
        0,
        mesh.unk40,
        mesh.unk44,
        0,
        mesh.polygon_ptr,
        mesh.vertex_ptr,
        mesh.normal_ptr,
        mesh.light_ptr,
        mesh.morph_ptr,
        mesh.unk72,
        mesh.unk76,
        mesh.unk80,
        mesh.unk84,
        0,
    )
    f.write(data)


def _write_vec3s(f: BinaryIO, vecs: List[Vec3]) -> None:
    if not vecs:
        return

    for vec in vecs:
        f.write(VEC3.pack(*vec))


def _write_lights(f: BinaryIO, lights: List[Light]) -> None:
    for light in lights:
        extra_count = len(light.extra)
        data = LIGHT.pack(
            light.unk00,
            light.unk04,
            light.unk08,
            extra_count,
            light.unk16,
            light.unk20,
            light.unk24,
            light.unk28,
            light.unk32,
            light.unk36,
            light.unk40,
            light.ptr,
            light.unk48,
            light.unk52,
            light.unk56,
            light.unk60,
            light.unk64,
            light.unk68,
            light.unk72,
        )
        f.write(data)

    for light in lights:
        if light.extra:
            _write_vec3s(f, light.extra)


def _write_u32s(f: BinaryIO, arr: List[int]) -> None:
    if not arr:
        return
    for item in arr:
        f.write(UINT32.pack(item))


def _write_polygons(f: BinaryIO, polygons: List[Polygon]) -> None:
    for polygon in polygons:
        vertex_info = len(polygon.vertex_indices) & 0xFF
        if polygon.unk_bit:
            vertex_info |= 0x100
        if polygon.vtx_bit:
            vertex_info |= 0x200

        data = POLYGON.pack(
            vertex_info,
            polygon.unk04,
            polygon.vertex_ptr,
            polygon.normal_ptr,
            polygon.uv_ptr,
            polygon.color_ptr,
            polygon.unk_ptr,
            polygon.texture_index,
            polygon.texture_info,
        )
        f.write(data)

    for polygon in polygons:
        _write_u32s(f, polygon.vertex_indices)
        _write_u32s(f, polygon.normal_indices)

        for u, v in polygon.uv_coords:
            f.write(VEC2.pack(u, 1.0 - v))

        _write_vec3s(f, polygon.vertex_colors)


def write_mesh_data(f: BinaryIO, mesh: Mesh) -> None:
    _write_vec3s(f, mesh.vertices)
    _write_vec3s(f, mesh.normals)
    _write_vec3s(f, mesh.morphs)
    if mesh.lights:
        _write_lights(f, mesh.lights)
    if mesh.polygons:
        _write_polygons(f, mesh.polygons)
