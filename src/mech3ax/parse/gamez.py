from __future__ import annotations

import logging
from enum import IntFlag
from struct import Struct
from typing import List, Optional, Tuple

from pydantic import BaseModel

from ..errors import Mech3ParseError, assert_eq, assert_in, assert_ne
from .utils import BinReader, ascii_zterm

SIGNATURE = 0x02971222
VERSION = 27

LOG = logging.getLogger(__name__)

GAMEZ_HEADER = Struct("<9I")
assert GAMEZ_HEADER.size == 36, GAMEZ_HEADER.size

TEXTURE_INFO = Struct("<2I 20s 3I")
assert TEXTURE_INFO.size == 40, TEXTURE_INFO.size

MATERIAL_HEADER = Struct("<4I")
assert MATERIAL_HEADER.size == 16, MATERIAL_HEADER.size

MATERIAL_INFO = Struct("<2BH 3f I 3f 2I 2H")
assert MATERIAL_INFO.size == 44, MATERIAL_INFO.size

CYCLE_HEADER = Struct("<7I")
assert CYCLE_HEADER.size == 28, CYCLE_HEADER.size


class MaterialFlag(IntFlag):
    Textured = 1
    Unknown = 2
    Cycled = 4
    Something = 16
    Free = 32  # ?

    def __call__(self, value: int) -> bool:
        return value & self == self

    @classmethod
    def check(cls, value: int) -> MaterialFlag:
        if value == 0:
            raise ValueError(f"Undefined flag: {value}")
        mask = 0
        for flag in cls.__members__.values():
            if (value & flag.value) == flag.value:
                mask |= flag.value
        if value != mask:
            raise ValueError(f"Undefined flag: {value}")
        return cls(value)


class Material(BaseModel):
    flag: MaterialFlag
    texture: int
    red: float
    green: float
    blue: float
    unk1: int
    unk5: int
    cycle_ptr: int = 0
    cycle: Optional[List[int]] = None
    cycle_unk2: int = 0


class GameZ(BaseModel):
    textures: List[str]
    material_array_size: int
    materials: List[Material]


def _read_textures(reader: BinReader, count: int) -> List[str]:
    textures = []
    for _ in range(count):
        prev_ptr, unknown, name, used, index, next_ptr = reader.read(TEXTURE_INFO)
        # a pointer to the previous texture in the global array
        assert_eq("prev ptr", 0, prev_ptr, reader.prev + 0)
        # a non-zero value here causes additional dynamic code to be called
        assert_eq("field 2", 0, unknown, reader.prev + 4)
        # 2 if the texture is used, 0 if the texture is unused
        # 1 or 3 if the texture is being processed (deallocated?)
        assert_eq("used", 2, used, reader.prev + 28)
        # stores the texture's index in the global texture array
        assert_eq("index", 0, index, reader.prev + 32)
        # a pointer to the next texture in the global array
        assert_eq("next ptr", 0xFFFFFFFF, next_ptr, reader.prev + 36)
        textures.append(ascii_zterm(name))
    return textures


def _read_materials_set(  # pylint: disable=too-many-locals
    reader: BinReader, mat_count: int, texture_count: int
) -> List[Material]:
    materials = []
    for i in range(0, mat_count):
        # very similar to materials in the mechlib
        (
            unk1,
            flag,
            rgb,
            red,
            green,
            blue,
            texture,
            unk2,
            unk3,
            unk4,
            unk5,
            cycle_ptr,
            index1,
            index2,
        ) = reader.read(MATERIAL_INFO)

        try:
            flag = MaterialFlag.check(flag)
        except ValueError:
            raise Mech3ParseError(
                f"Expected valid flag, but was {flag:02X} (at {reader.prev + 1})"
            )
        assert_eq("free", False, MaterialFlag.Free(flag), reader.prev + 1)

        if MaterialFlag.Textured(flag):
            # if the material is textured, it should not have an RGB value
            assert_eq("rgb", 0x7FFF, rgb, reader.prev + 2)
            assert_eq("red", 255.0, red, reader.prev + 4)
            assert_eq("green", 255.0, green, reader.prev + 8)
            assert_eq("blue", 255.0, blue, reader.prev + 12)
            # the texture should be in range
            in_range = texture < texture_count
            assert_eq("texture in range", True, in_range, reader.prev + 16)
        else:
            # if the material is not textured, it can't be cycled
            assert_eq(
                "texture cycled", False, MaterialFlag.Cycled(flag), reader.prev + 1
            )
            assert_eq("texture", 0, texture, reader.prev + 16)
            # i don't know why this is always zero?
            assert_eq("rgb", 0x0, rgb, reader.prev + 2)

        # not sure what these are?
        assert_eq("field 8", 0.0, unk2, reader.prev + 20)
        assert_eq("field 9", 0.5, unk3, reader.prev + 24)
        assert_eq("field 10", 0.5, unk4, reader.prev + 28)

        if MaterialFlag.Cycled(flag):
            assert_ne("cycle pointer", 0, cycle_ptr, reader.prev + 36)
        else:
            assert_eq("cycle pointer", 0, cycle_ptr, reader.prev + 36)

        expected1 = i + 1
        if expected1 >= mat_count:
            expected1 = 0xFFFF
        assert_eq("index 1", expected1, index1, reader.prev + 40)

        expected2 = i - 1
        if expected2 < 0:
            expected2 = 0xFFFF
        assert_eq("index 2", expected2, index2, reader.prev + 42)

        material = Material(
            flag=flag,
            texture=texture,
            red=red,
            green=green,
            blue=blue,
            unk1=unk1,
            unk5=unk5,
            cycle_ptr=cycle_ptr,
        )
        materials.append(material)
    return materials


def _read_materials_unset(reader: BinReader, mat_count: int, array_size: int) -> None:
    # the rest should be zero
    for i in range(mat_count, array_size):
        (
            unk1,
            flag,
            rgb,
            red,
            green,
            blue,
            texture,
            unk2,
            unk3,
            unk4,
            unk5,
            cycle_ptr,
            index1,
            index2,
        ) = reader.read(MATERIAL_INFO)

        assert_eq("field 1", 0, unk1, reader.prev + 0)
        assert_eq("flag", MaterialFlag.Free, flag, reader.prev + 1)
        assert_eq("rgb", 0x0, rgb, reader.prev + 2)
        assert_eq("red", 0.0, red, reader.prev + 4)
        assert_eq("green", 0.0, green, reader.prev + 8)
        assert_eq("blue", 0.0, blue, reader.prev + 12)
        assert_eq("texture", 0, texture, reader.prev + 16)
        assert_eq("field 8", 0.0, unk2, reader.prev + 20)
        assert_eq("field 9", 0.0, unk3, reader.prev + 24)
        assert_eq("field 10", 0.0, unk4, reader.prev + 28)
        assert_eq("field 11", 0, unk5, reader.prev + 32)
        assert_eq("cycle pointer", 0, cycle_ptr, reader.prev + 36)

        expected1 = i - 1
        if expected1 < mat_count:
            expected1 = 0xFFFF
        assert_eq("index 1", expected1, index1, reader.prev + 40)

        expected2 = i + 1
        if expected2 >= array_size:
            expected2 = 0xFFFF
        assert_eq("index 2", expected2, index2, reader.prev + 42)


def _read_materials(
    reader: BinReader, texture_count: int
) -> Tuple[int, List[Material]]:
    (array_size, mat_count, index_max, mat_unknown) = reader.read(MATERIAL_HEADER)
    assert_eq("index max", mat_count, index_max, reader.prev + 8)
    assert_eq("field 4", mat_count - 1, mat_unknown, reader.prev + 12)

    materials = _read_materials_set(reader, mat_count, texture_count)
    _read_materials_unset(reader, mat_count, array_size)

    tex_range = range(texture_count)
    for material in materials:
        if MaterialFlag.Cycled(material.flag):
            (unk1, unk2, unk3, unk4, cycle_count, unk6, unk7) = reader.read(
                CYCLE_HEADER
            )

            assert_in("field 1", (0, 1), unk1, reader.prev + 0)
            # field 2
            assert_eq("field 3", 0, unk3, reader.prev + 8)
            assert_ne("field 4", 0, unk4, reader.prev + 12)
            assert_eq("field 6", cycle_count, unk6, reader.prev + 20)
            assert_ne("field 7", 0, unk7, reader.prev + 24)

            cycle_textures = reader.read(Struct(f"<{cycle_count}I"))

            for i, cycle_texture in enumerate(cycle_textures):
                # the texture should be in range
                assert_in("texture", tex_range, cycle_texture, reader.prev + i * 4)

            material.cycle = list(cycle_textures)
            material.cycle_unk2 = unk2

    return array_size, materials


def read_gamez(data: bytes) -> GameZ:
    reader = BinReader(data)
    (
        signature,
        version,
        texture_count,
        texture_offset,
        material_offset,
        model3d_offset,
        _node_array_size,
        _node_data_count,
        _node_data_offset,
    ) = reader.read(GAMEZ_HEADER)

    assert_eq("signature", SIGNATURE, signature, reader.prev + 0)
    assert_eq("version", VERSION, version, reader.prev + 4)

    if texture_count > 4096:
        raise Mech3ParseError(
            f"Expected texture count to be less than 4096, but was {texture_count!r} (at {reader.prev + 9})"
        )

    assert_eq("texture offset", texture_offset, reader.offset, reader.offset)
    textures = _read_textures(reader, texture_count)
    assert_eq("material offset", material_offset, reader.offset, reader.offset)
    material_array_size, materials = _read_materials(reader, texture_count)
    assert_eq("model3d offset", model3d_offset, reader.offset, reader.offset)

    return GameZ(
        textures=textures, material_array_size=material_array_size, materials=materials,
    )
