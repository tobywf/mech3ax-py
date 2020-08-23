import logging
from typing import BinaryIO, List, Tuple

from mech3ax.errors import assert_between, assert_eq, assert_le

from ..model3d import read_mesh_data, read_mesh_info, write_mesh_data, write_mesh_info
from ..models import LIGHT, MESH, POLYGON, VEC2, VEC3, Mesh
from ..utils import UINT32, BinReader
from .models import MESHES_HEADER, SINT32

LOG = logging.getLogger(__name__)


def _read_mesh_zero(reader: BinReader, mesh_count: int, array_size: int) -> None:
    LOG.debug("Reading %d zeroed meshes at %d", array_size - mesh_count, reader.offset)
    for i in range(mesh_count, array_size):
        mesh = reader.read(MESH)
        for j, value in enumerate(mesh):
            offset = j * 4
            assert_eq(f"field {offset:02d}", 0, value, reader.prev + offset)

        expected = i + 1
        if expected == array_size:
            expected = -1

        (index,) = reader.read(SINT32)
        assert_eq("index", expected, index, reader.prev)


def read_meshes(
    reader: BinReader, start_offset: int, end_offset: int
) -> Tuple[int, List[Mesh]]:
    array_size, mesh_count, index_max = reader.read(MESHES_HEADER)
    LOG.debug("Reading %d meshes (%d)", mesh_count, array_size)
    assert_le("mesh count", array_size, mesh_count, reader.prev + 4)
    assert_le("mesh index", mesh_count, index_max, reader.prev + 8)

    wrapped_meshes = []
    prev_offset = start_offset
    for i in range(0, mesh_count):
        LOG.debug("Reading mesh %d at %d...", i, reader.offset)
        wrapped_mesh = read_mesh_info(reader)

        mesh_offset = reader.read_u32()
        assert_between("mesh offset", prev_offset, end_offset, mesh_offset, reader.prev)
        wrapped_meshes.append((i, mesh_offset, wrapped_mesh))
        prev_offset = mesh_offset

    _read_mesh_zero(reader, mesh_count, array_size)

    meshes = []
    for i, mesh_offset, wrapped_mesh in wrapped_meshes:
        LOG.debug("Reading polygons for mesh %d at %d...", i, mesh_offset)
        assert_eq("mesh offset", mesh_offset, reader.offset, reader.offset)

        mesh = read_mesh_data(reader, wrapped_mesh)
        meshes.append(mesh)

    LOG.debug("Read meshes")

    return array_size, meshes


def _write_mesh_zero(f: BinaryIO, index: int) -> None:
    data = MESH.pack(
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0
    )
    f.write(data)
    f.write(SINT32.pack(index))


def write_meshes(
    f: BinaryIO, array_size: int, meshes: List[Mesh], mesh_offsets: List[int],
) -> None:
    mesh_count = len(meshes)
    data = MESHES_HEADER.pack(array_size, mesh_count, mesh_count)
    f.write(data)

    for mesh, offset in zip(meshes, mesh_offsets):
        write_mesh_info(f, mesh)
        f.write(UINT32.pack(offset))

    for i in range(mesh_count, array_size):
        index = i + 1
        if index == array_size:
            index = -1
        _write_mesh_zero(f, index)

    for mesh in meshes:
        write_mesh_data(f, mesh)


def size_meshes(
    array_size: int, meshes: List[Mesh], start_offset: int
) -> Tuple[int, List[int]]:
    size = MESHES_HEADER.size + MESH.size * array_size + UINT32.size * array_size

    mesh_offsets = []
    for i, mesh in enumerate(meshes):
        LOG.debug("Writing polygons for mesh %d at %d...", i, size + start_offset)
        mesh_offsets.append(size + start_offset)

        size += (
            VEC3.size * len(mesh.vertices)
            + VEC3.size * len(mesh.normals)
            + VEC3.size * len(mesh.morphs)
        )

        for light in mesh.lights:
            size += LIGHT.size + VEC3.size * len(light.extra)

        for polygon in mesh.polygons:
            size += (
                POLYGON.size
                + UINT32.size * len(polygon.vertex_indices)
                + UINT32.size * len(polygon.normal_indices)
                + VEC2.size * len(polygon.uv_coords)
                + VEC3.size * len(polygon.vertex_colors)
            )

    return size, mesh_offsets
