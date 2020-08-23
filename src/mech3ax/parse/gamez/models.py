# pylint: disable=useless-import-alias
from __future__ import annotations

from struct import Struct
from typing import List, Literal, Optional, Tuple, Union

from pydantic import BaseModel

from mech3ax.serde import NodeType as NodeType

from ..anim.light import LightFlag
from ..int_flag import IntFlag
from ..models import (  # pylint: disable=unused-import
    IDENTITY_MATRIX as IDENTITY_MATRIX,
    NODE_INFO as NODE_INFO,
    OBJECT3D as OBJECT3D,
    Matrix as Matrix,
    Mesh as Mesh,
    Object3d as Object3d,
    Vec2 as Vec2,
    Vec3 as Vec3,
)

SINT32 = Struct("<i")

GAMEZ_HEADER = Struct("<9I")
assert GAMEZ_HEADER.size == 36, GAMEZ_HEADER.size

TEXTURE_INFO = Struct("<2I 20s 2I i")
assert TEXTURE_INFO.size == 40, TEXTURE_INFO.size

MATERIAL_HEADER = Struct("<4I")
assert MATERIAL_HEADER.size == 16, MATERIAL_HEADER.size

MATERIAL_INFO = Struct("<2B H 3f I 3f 2I 2h")
assert MATERIAL_INFO.size == 44, MATERIAL_INFO.size

CYCLE_HEADER = Struct("<3I f 3I")
assert CYCLE_HEADER.size == 28, CYCLE_HEADER.size

MESHES_HEADER = Struct("<3I")
assert MESHES_HEADER.size == 12, MESHES_HEADER.size

CAMERA = Struct("<5i 3f 3f 132s 2f 24s 10f I60s I72s I72s I 2f 3i")
assert CAMERA.size == 488, CAMERA.size

WORLD = Struct("<5I 3f 2f 2f f 2f 2f 2f 2I 4I 7f 2f 3I 3f 3I 2I 2I")
assert WORLD.size == 188, WORLD.size

WINDOW = Struct("<4I 212s i4I")
assert WINDOW.size == 248, WINDOW.size

DISPLAY = Struct("<4I 3f")
assert DISPLAY.size == 28, DISPLAY.size

LEVEL_OF_DETAIL = Struct("<I 3f 44s 2f 3I")
assert LEVEL_OF_DETAIL.size == 80, LEVEL_OF_DETAIL.size

# TODO: should only be 208 + write for 200
LIGHT = Struct("<3f 3f 112s 5f 5f I 5f 3I")
assert LIGHT.size == 212, LIGHT.size

PARTITION = Struct("<Ii 12f 2H 3I")
assert PARTITION.size == 72, PARTITION.size


class Display(BaseModel):
    type: Literal["Display"]
    resolution: Tuple[int, int]
    clear_color: Vec3


class Window(BaseModel):
    type: Literal["Window"]
    resolution: Tuple[int, int]


LIGHT_FLAG = (
    LightFlag.Subdivide
    | LightFlag.Saturated
    | LightFlag.Directional
    | LightFlag.Range
    | LightFlag.Translation
    | LightFlag.TranslationAbs
)


class Light(BaseModel):
    type: Literal["Light"]
    direction: Vec3
    diffuse: float
    ambient: float
    color: Vec3
    # The flag is constant, so skip serializing it
    # flag: LightFlag
    range: Vec2
    parent_ptr: int


class Camera(BaseModel):
    type: Literal["Camera"]
    clip: Vec2
    fov: Vec2


class LevelOfDetail(BaseModel):
    type: Literal["LOD"]
    level: bool
    range: Vec2
    unk60: float
    unk76: int


class Partition(BaseModel):
    x: int
    y: int
    nodes: List[int]
    unk: Vec3
    ptr: int


class World(BaseModel):
    type: Literal["World"]

    area: Tuple[float, float, float, float]
    partitions: List[List[Partition]]
    children: List[int]

    area_partition_x_count: int
    area_partition_y_count: int
    fudge_count: bool = False

    area_partition_ptr: int
    virt_partition_ptr: int

    children_ptr: int
    lights_ptr: int


NodeData = Union[Display, Window, Light, Camera, LevelOfDetail, Object3d, World, None]


class NodeFlag(IntFlag):
    # Unk00 = 1 << 0  # 0x00000001, 1
    # Unk01 = 1 << 1  # 0x00000002, 2
    Active = 1 << 2  # 0x00000004, 4
    AltitudeSurface = 1 << 3  # 0x00000008, 8
    IntersectSurface = 1 << 4  # 0x00000010, 16
    IntersectBBox = 1 << 5  # 0x00000020, 32
    # Proximity = 1 << 6  # 0x00000040, 64
    Landmark = 1 << 7  # 0x00000080, 128
    Unk08 = 1 << 8  # 0x00000100, 256
    HasMesh = 1 << 9  # 0x00000200, 512
    Unk10 = 1 << 10  # 0x00000400, 1024
    # Unk11 := Keep node after action callback?
    # Unk11 = 1 << 11  # 0x00000800, 2048
    # Unk12 = 1 << 12  # 0x00001000, 4096
    # Unk13 = 1 << 13  # 0x00002000, 8192
    # Unk14 = 1 << 14  # 0x00004000, 16384
    Unk15 = 1 << 15  # 0x00008000, 32768
    CanModify = 1 << 16  # 0x00010000, 65536
    ClipTo = 1 << 17  # 0x00020000, 131072
    # Unk18 = 1 << 18  # 0x00040000, 262144
    TreeValid = 1 << 19  # 0x00080000, 524288
    # Unk20 = 1 << 20  # 0x00100000, 1048576
    # Unk21 = 1 << 21  # 0x00200000, 2097152
    # Unk22 = 1 << 22  # 0x00400000, 4194304
    # Override = 1 << 23  # 0x00800000, 8388608
    IDZoneCheck = 1 << 24  # 0x01000000, 16777216
    Unk25 = 1 << 25  # 0x02000000, 33554432
    # Unk26 = 1 << 26  # 0x04000000, 67108864
    # Unk27 = 1 << 27  # 0x08000000, 134217728
    Unk28 = 1 << 28  # 0x10000000, 268435456
    # Unk29 = 1 << 29  # 0x20000000, 536870912
    # Unk30 = 1 << 30  # 0x40000000, 1073741824
    # Unk31 = 1 << 31  # 0x80000000, 2147483648


NODE_FLAG_BASE = NodeFlag.Active | NodeFlag.TreeValid | NodeFlag.IDZoneCheck
NODE_FLAG_DEFAULT = (
    NODE_FLAG_BASE | NodeFlag.AltitudeSurface | NodeFlag.IntersectSurface
)


class Node(BaseModel):
    name: str
    node_type: NodeType
    flag: NodeFlag
    zone_id: int
    mesh_index: int
    parent_count: int
    parent_array_ptr: int
    children_count: int
    children_array_ptr: int
    parent: int
    children: List[int]
    data: NodeData
    data_ptr: int
    area_partition_x: int
    area_partition_y: int

    flag_repr: str

    unk044: int
    unk196: int

    block1: Tuple[float, float, float, float, float, float]
    block2: Tuple[float, float, float, float, float, float]
    block3: Tuple[float, float, float, float, float, float]


class Texture(BaseModel):
    name: str
    suffix: str


class MaterialFlag(IntFlag):
    Textured = 1 << 0
    Unknown = 1 << 1
    Cycled = 1 << 2
    Always = 1 << 4
    Free = 1 << 5


class Cycle(BaseModel):
    textures: List[int]
    unk00: bool
    unk04: int
    unk12: float
    info_ptr: int
    data_ptr: int


class Material(BaseModel):
    texture: Optional[int] = None
    color: Optional[Vec3] = None
    cycle: Optional[Cycle] = None

    unk00: int = 255
    unk32: int = 0
    unknown: bool = False
