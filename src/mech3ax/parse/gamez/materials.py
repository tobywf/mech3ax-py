from struct import Struct
from typing import BinaryIO, List, Optional, Tuple

from mech3ax.errors import assert_between, assert_eq, assert_flag, assert_in, assert_ne

from ..utils import BinReader
from .models import (
    CYCLE_HEADER,
    MATERIAL_HEADER,
    MATERIAL_INFO,
    Cycle,
    Material,
    MaterialFlag,
    Vec3,
)


def _read_materials(  # pylint: disable=too-many-locals
    reader: BinReader, mat_count: int, texture_count: int
) -> List[Tuple[Material, int]]:
    materials = []
    for i in range(0, mat_count):
        # very similar to materials in the mechlib
        (
            unk00,
            flag_raw,
            rgb,
            red,
            green,
            blue,
            texture,
            unk20,
            unk24,
            unk28,
            unk32,
            cycle_ptr,
            index1,
            index2,
        ) = reader.read(MATERIAL_INFO)

        with assert_flag("flag", flag_raw, reader.prev + 1):
            flag = MaterialFlag.check(flag_raw)

        assert_eq("flag always", True, MaterialFlag.Always(flag), reader.prev + 1)
        assert_eq("flag free", False, MaterialFlag.Free(flag), reader.prev + 1)

        cycled = MaterialFlag.Cycled(flag)

        if MaterialFlag.Textured(flag):
            assert_eq("field 00", 255, unk00, reader.prev + 0)

            # if the material is textured, it should not have an RGB value
            assert_eq("rgb", 0x7FFF, rgb, reader.prev + 2)
            assert_eq("red", 255.0, red, reader.prev + 4)
            assert_eq("green", 255.0, green, reader.prev + 8)
            assert_eq("blue", 255.0, blue, reader.prev + 12)
            color: Optional[Vec3] = None
            # the texture should be in range
            assert_between("texture", 0, texture_count - 1, texture, reader.prev + 16)
        else:
            # value distribution:
            #   24 0
            #    2 51
            #    2 76
            #    2 89
            #    3 102
            #    1 127
            #    1 153
            # 2629 255 (includes textured)
            values_00 = (0, 51, 76, 89, 102, 127, 153, 255)
            assert_in("field 00", values_00, unk00, reader.prev + 0)
            # this is  never true for untextured materials
            assert_eq("flag unk", False, MaterialFlag.Unknown(flag), reader.prev + 1)

            # if the material is not textured, it can't be cycled
            assert_eq("texture cycled", False, cycled, reader.prev + 1)
            # this is calculated from the floating point values, since this short
            # representation depends on the hardware RGB565 or RGB555 support
            assert_eq("rgb", 0x0, rgb, reader.prev + 2)
            color = (red, green, blue)
            assert_eq("texture", 0, texture, reader.prev + 16)
            texture = None

        # not sure what these are?
        assert_eq("field 20", 0.0, unk20, reader.prev + 20)
        assert_eq("field 24", 0.5, unk24, reader.prev + 24)
        assert_eq("field 28", 0.5, unk28, reader.prev + 28)

        # value distribution:
        # 2480 0
        #   12 1
        #    1 4
        #   61 6
        #   17 7
        #    3 8
        #   72 9
        #    4 10
        #   11 12
        #    3 13
        # bit field?
        #  0 0b0000
        #  1 0b0001
        #  4 0b0100
        #  6 0b0110
        #  7 0b0111
        #  8 0b1000
        #  9 0b1001
        # 10 0b1010
        # 12 0b1100
        # 13 0b1101
        assert_in(
            "field 32", (0, 1, 4, 6, 7, 8, 9, 10, 12, 13), unk32, reader.prev + 32
        )

        if cycled:
            assert_ne("cycle pointer", 0, cycle_ptr, reader.prev + 36)
        else:
            assert_eq("cycle pointer", 0, cycle_ptr, reader.prev + 36)

        expected1 = i + 1
        if expected1 >= mat_count:
            expected1 = -1
        assert_eq("index 1", expected1, index1, reader.prev + 40)

        expected2 = i - 1
        if expected2 < 0:
            expected2 = -1
        assert_eq("index 2", expected2, index2, reader.prev + 42)

        material = Material(
            texture=texture,
            color=color,
            unk00=unk00,
            unk32=unk32,
            unknown=MaterialFlag.Unknown(flag),
        )
        materials.append((material, cycle_ptr))
    return materials


def _read_materials_zero(reader: BinReader, mat_count: int, array_size: int) -> None:
    # the rest should be zero
    for i in range(mat_count, array_size):
        (
            unk00,
            flag,
            rgb,
            red,
            green,
            blue,
            texture,
            unk20,
            unk24,
            unk28,
            unk32,
            cycle_ptr,
            index1,
            index2,
        ) = reader.read(MATERIAL_INFO)

        assert_eq("field 00", 0, unk00, reader.prev + 0)
        assert_eq("flag", MaterialFlag.Free, flag, reader.prev + 1)
        assert_eq("rgb", 0x0, rgb, reader.prev + 2)
        assert_eq("red", 0.0, red, reader.prev + 4)
        assert_eq("green", 0.0, green, reader.prev + 8)
        assert_eq("blue", 0.0, blue, reader.prev + 12)
        assert_eq("texture", 0, texture, reader.prev + 16)
        assert_eq("field 20", 0.0, unk20, reader.prev + 20)
        assert_eq("field 24", 0.0, unk24, reader.prev + 24)
        assert_eq("field 28", 0.0, unk28, reader.prev + 28)
        assert_eq("field 32", 0, unk32, reader.prev + 32)
        assert_eq("cycle pointer", 0, cycle_ptr, reader.prev + 36)

        expected1 = i - 1
        if expected1 < mat_count:
            expected1 = -1
        assert_eq("index 1", expected1, index1, reader.prev + 40)

        expected2 = i + 1
        if expected2 >= array_size:
            expected2 = -1
        assert_eq("index 2", expected2, index2, reader.prev + 42)


def read_materials(reader: BinReader, texture_count: int) -> Tuple[int, List[Material]]:
    (array_size, mat_count, index_max, mat_unknown) = reader.read(MATERIAL_HEADER)
    assert_eq("index max", mat_count, index_max, reader.prev + 8)
    assert_eq("field 12", mat_count - 1, mat_unknown, reader.prev + 12)

    materials_and_cycle = _read_materials(reader, mat_count, texture_count)
    _read_materials_zero(reader, mat_count, array_size)

    materials = []
    for material, cycle_info_ptr in materials_and_cycle:
        if cycle_info_ptr:
            (
                unk00,
                unk04,
                zero08,
                unk12,
                cycle_count1,
                cycle_count2,
                data_ptr,
            ) = reader.read(CYCLE_HEADER)

            assert_in("field 00", (0, 1), unk00, reader.prev + 0)
            # field 04
            assert_eq("field 08", 0, zero08, reader.prev + 8)
            assert_between("field 12", 2.0, 16.0, unk12, reader.prev + 12)
            assert_eq("cycle count", cycle_count1, cycle_count2, reader.prev + 20)
            assert_ne("field 24", 0, data_ptr, reader.prev + 24)

            cycle_textures = reader.read(Struct(f"<{cycle_count1}I"))

            for i, cycle_texture in enumerate(cycle_textures):
                # the texture should be in range
                assert_between(
                    "texture", 0, texture_count - 1, cycle_texture, reader.prev + i * 4
                )

            material.cycle = Cycle(
                textures=list(cycle_textures),
                unk00=unk00 == 1,
                unk04=unk04,
                unk12=unk12,
                info_ptr=cycle_info_ptr,
                data_ptr=data_ptr,
            )
        materials.append(material)

    return array_size, materials


def write_materials(  # pylint: disable=too-many-branches
    f: BinaryIO, array_size: int, materials: List[Material]
) -> None:
    mat_count = len(materials)
    data = MATERIAL_HEADER.pack(array_size, mat_count, mat_count, mat_count - 1)
    f.write(data)

    for i, material in enumerate(materials):
        index1 = i + 1
        if index1 >= mat_count:
            index1 = -1

        index2 = i - 1
        if index2 < 0:
            index2 = -1

        flag = MaterialFlag.Always
        if material.unknown:
            flag |= MaterialFlag.Unknown

        if material.texture is not None:
            flag |= MaterialFlag.Textured
            rgb = 0x7FFF
            red = green = blue = 255.0
            texture = material.texture
        elif material.color is not None:
            rgb = 0x0
            red, green, blue = material.color
            texture = 0
        else:
            raise ValueError("neither texture nor color set")

        if material.cycle:
            flag |= MaterialFlag.Cycled
            cycle_ptr = material.cycle.info_ptr
        else:
            cycle_ptr = 0

        data = MATERIAL_INFO.pack(
            material.unk00,
            int(flag),
            rgb,
            red,
            green,
            blue,
            texture,
            0.0,
            0.5,
            0.5,
            material.unk32,
            cycle_ptr,
            index1,
            index2,
        )
        f.write(data)

    for i in range(mat_count, array_size):
        index1 = i - 1
        if index1 < mat_count:
            index1 = -1

        index2 = i + 1
        if index2 >= array_size:
            index2 = -1

        data = MATERIAL_INFO.pack(
            0,
            int(MaterialFlag.Free),
            0x0,
            0.0,
            0.0,
            0.0,
            0,
            0.0,
            0.0,
            0.0,
            0,
            0,
            index1,
            index2,
        )
        f.write(data)

    for material in materials:
        cycle = material.cycle
        if not cycle:
            continue

        cycle_count = len(cycle.textures)
        data = CYCLE_HEADER.pack(
            1 if cycle.unk00 else 0,
            cycle.unk04,
            0,
            cycle.unk12,
            cycle_count,
            cycle_count,
            cycle.data_ptr,
        )
        f.write(data)

        data = Struct(f"<{cycle_count}I").pack(*cycle.textures)
        f.write(data)


def size_materials(array_size: int, materials: List[Material]) -> int:
    size = MATERIAL_HEADER.size + MATERIAL_INFO.size * array_size
    for material in materials:
        if material.cycle:
            size += CYCLE_HEADER.size + len(material.cycle.textures) * 4
    return size
