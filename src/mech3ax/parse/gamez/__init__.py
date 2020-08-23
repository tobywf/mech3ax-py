import logging
from dataclasses import dataclass
from typing import BinaryIO, List

from pydantic import BaseModel

from mech3ax.errors import assert_eq, assert_lt

from ..utils import BinReader
from .materials import read_materials, size_materials, write_materials
from .model3d import read_meshes, size_meshes, write_meshes
from .models import GAMEZ_HEADER, Material, Mesh, Node, NodeType, Texture
from .nodes import read_nodes
from .textures import read_textures, size_textures, write_textures

SIGNATURE = 0x02971222
VERSION = 27

LOG = logging.getLogger(__name__)


class Textures(BaseModel):
    __root__: List[Texture]


class Materials(BaseModel):
    __root__: List[Material]


class Meshes(BaseModel):
    __root__: List[Mesh]


class Nodes(BaseModel):
    class Config:
        json_encoders = {NodeType: NodeType.to_str}

    __root__: List[Node]


class GameZMetadata(BaseModel):
    material_array_size: int
    mesh_array_size: int
    node_array_size: int
    node_data_count: int


@dataclass  # not JSON serializable!
class GameZ:
    textures: Textures
    materials: Materials
    meshes: Meshes
    nodes: Nodes
    metadata: GameZMetadata


def read_gamez(data: bytes) -> GameZ:
    reader = BinReader(data)
    LOG.debug("Reading GameZ data...")
    (
        signature,
        version,
        texture_count,
        texture_offset,
        material_offset,
        mesh_offset,
        node_array_size,
        node_count,
        node_offset,
    ) = reader.read(GAMEZ_HEADER)

    assert_eq("signature", SIGNATURE, signature, reader.prev + 0)
    assert_eq("version", VERSION, version, reader.prev + 4)
    assert_lt("texture count", 4096, texture_count, reader.prev + 8)
    assert_lt("node count", node_array_size, node_count, reader.prev + 28)

    LOG.debug(
        "%d textures at %d, materials at %d, meshes at %d, nodes at %d",
        texture_count,
        texture_offset,
        material_offset,
        mesh_offset,
        node_offset,
    )

    assert_eq("texture offset", texture_offset, reader.offset, reader.offset)
    textures = read_textures(reader, texture_count)
    assert_eq("material offset", material_offset, reader.offset, reader.offset)
    material_array_size, materials = read_materials(reader, texture_count)
    assert_eq("mesh offset", mesh_offset, reader.offset, reader.offset)
    mesh_array_size, meshes = read_meshes(reader, mesh_offset, node_offset - 1)
    assert_eq("nodes offset", node_offset, reader.offset, reader.offset)
    nodes = read_nodes(reader, node_array_size, node_count, len(meshes))

    LOG.debug("Read GameZ data")

    return GameZ(
        textures=Textures(__root__=textures),
        materials=Materials(__root__=materials),
        meshes=Meshes(__root__=meshes),
        nodes=Nodes(__root__=nodes),
        metadata=GameZMetadata(
            material_array_size=material_array_size,
            mesh_array_size=mesh_array_size,
            node_array_size=node_array_size,
            node_data_count=node_count,
        ),
    )


def write_gamez(f: BinaryIO, gamez: GameZ) -> None:
    LOG.debug("Writing GameZ data...")
    texture_count = len(gamez.textures.__root__)
    assert_lt("texture count", 4096, texture_count, 0)

    material_array_size = gamez.metadata.material_array_size
    mesh_array_size = gamez.metadata.mesh_array_size

    texture_offset = GAMEZ_HEADER.size
    material_offset = texture_offset + size_textures(texture_count)
    mesh_offset = material_offset + size_materials(
        material_array_size, gamez.materials.__root__
    )
    meshes_size, mesh_offsets = size_meshes(
        mesh_array_size, gamez.meshes.__root__, mesh_offset
    )
    node_offset = mesh_offset + meshes_size

    LOG.debug(
        "%d textures at %d, materials at %d, meshes at %d, nodes at %d",
        texture_count,
        texture_offset,
        material_offset,
        mesh_offset,
        node_offset,
    )
    data = GAMEZ_HEADER.pack(
        SIGNATURE,
        VERSION,
        texture_count,
        texture_offset,
        material_offset,
        mesh_offset,
        gamez.metadata.node_array_size,
        gamez.metadata.node_data_count,
        node_offset,
    )
    f.write(data)
    write_textures(f, gamez.textures.__root__)
    write_materials(f, material_array_size, gamez.materials.__root__)
    write_meshes(f, mesh_array_size, gamez.meshes.__root__, mesh_offsets)

    LOG.debug("Wrote GameZ data")
