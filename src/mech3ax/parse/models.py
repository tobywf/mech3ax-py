from __future__ import annotations

from struct import Struct
from typing import List, Tuple

from pydantic import BaseModel

Vec2 = Tuple[float, float]
VEC2 = Struct("<2f")
assert VEC2.size == 8

Vec3 = Tuple[float, float, float]
VEC3 = Struct("<3f")
assert VEC3.size == 12

Vec4 = Tuple[float, float, float, float]
VEC4 = Struct("<4f")
assert VEC4.size == 16, VEC4.size

POLYGON = Struct("<9I")
assert POLYGON.size == 36, POLYGON.size

MESH = Struct("<4I 5I I2fI 5I 4f I")
assert MESH.size == 92, MESH.size

LIGHT = Struct("<3I I 3I 4f I 7f")
assert LIGHT.size == 76

OBJECT3D = Struct("<I f 4f 3f 3f 3f 3f 3f 3f 12I")
assert OBJECT3D.size == 144, OBJECT3D.size


class Light(BaseModel):
    unk00: int
    unk04: int
    unk08: int
    extra: List[Vec3]
    unk16: int
    unk20: int
    unk24: int
    unk28: float
    unk32: float
    unk36: float
    unk40: float
    ptr: int
    unk48: float
    unk52: float
    unk56: float
    unk60: float
    unk64: float
    unk68: float
    unk72: float


class Polygon(BaseModel):
    vertex_indices: List[int]
    vertex_colors: List[Vec3]
    normal_indices: List[int]
    uv_coords: List[Vec2]
    texture_index: int
    texture_info: int = 0xFFFFFF00
    # flag: bool
    unk04: int
    unk_bit: bool
    vtx_bit: bool
    vertex_ptr: int
    normal_ptr: int
    uv_ptr: int
    color_ptr: int
    unk_ptr: int


class Mesh(BaseModel):
    vertices: List[Vec3]
    normals: List[Vec3]
    morphs: List[Vec3]
    lights: List[Light]
    polygons: List[Polygon]
    polygon_ptr: int
    vertex_ptr: int
    normal_ptr: int
    light_ptr: int
    morph_ptr: int
    file_ptr: int
    zero04: int
    has_parents: int
    unk08: int
    unk40: float
    unk44: float
    unk72: float
    unk76: float
    unk80: float
    unk84: float
