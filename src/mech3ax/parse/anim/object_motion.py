from __future__ import annotations

from math import degrees
from struct import Struct
from typing import List, Tuple

from mech3ax.errors import assert_ascii, assert_eq, assert_ge, assert_gt, assert_in

from ..utils import BinReader, ascii_zterm_padded
from .models import AnimDef, ScriptObject

DUMMY_IMPORT = None
DEFAULT_GRAVITY = -9.800000190734863


class ObjectMotion(ScriptObject):
    _NAME: str = "OBJECT_MOTION"
    _NUMBER: int = 10
    _STRUCT: Struct = Struct(
        "<2I 3f 8f 4f 10fI 2f f 6f 3f 6f 3f 32s 2hf 32s 2hf 32s 2hf f"
    )

    node: str
    gravity: float = DEFAULT_GRAVITY
    translation_range_min: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    translation_range_max: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    translation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    forward_rotation: Tuple[float, float] = (0.0, 0.0)

    xyz_rotation: Tuple[float, float, float, float, float, float] = (
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    )

    scale: Tuple[float, float, float, float, float, float] = (
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    )

    bounce_sequence: List[str] = []
    bounce_sounds: List[Tuple[str, float]] = []
    run_time: float = 0.0

    unk: List[float] = []

    @classmethod
    def read(  # pylint: disable=too-many-locals,too-many-statements
        cls, reader: BinReader, anim_def: AnimDef
    ) -> ObjectMotion:
        (
            unk000,
            index,
            unk008,
            gravity,  # 012
            unk016,
            translation_range_min_1,  # 020
            translation_range_max_1,  # 024
            translation_range_min_2,  # 028
            translation_range_max_2,  # 032
            translation_range_min_3,  # 036
            translation_range_max_3,  # 040
            translation_range_min_4,  # 044
            translation_range_max_4,  # 048
            translation_x,  # 052
            translation_y,  # 056
            translation_z,  # 060
            translation_w,  # 064
            unk068,
            unk072,
            unk076,
            unk080,
            unk084,
            unk088,
            unk092,
            unk096,
            unk100,
            unk104,
            unk108,
            # FORWARD_ROTATION in radians. TIME?
            forward_rotation_0,
            forward_rotation_1,
            unk120,
            # XYZ_ROTATION in radians
            xyz_rotation_0,  # 124
            xyz_rotation_1,  # 128
            xyz_rotation_2,  # 132
            xyz_rotation_3,  # 136
            xyz_rotation_4,  # 140
            xyz_rotation_5,  # 144
            unk148,
            unk152,
            unk156,
            scale_0,  # 160
            scale_1,  # 164
            scale_2,  # 168
            scale_3,  # 172
            scale_4,  # 176
            scale_5,  # 180
            unk184,
            unk188,
            unk192,
            bounce_seq0_name_raw,  # 196
            bounce_seq0_sentinel,  # 228
            bounce_seq0_sound,  # 230
            bounce_seq0_volume,  # 232
            bounce_seq1_name_raw,  # 236
            bounce_seq1_sentinel,  # 268
            bounce_seq1_sound,  # 270
            bounce_seq1_volume,  # 272
            bounce_seq2_name_raw,  # 276
            bounce_seq2_sentinel,  # 308
            bounce_seq2_sound,  # 310
            bounce_seq2_volume,  # 312
            run_time,  # 316
        ) = reader.read(cls._STRUCT)

        node = anim_def.get_node(index - 1, reader.prev + 4)

        # 020, 028, 036, 044
        translation_range_min = (
            translation_range_min_1,
            translation_range_min_2,
            translation_range_min_3,
            translation_range_min_4,
        )

        # 024, 032, 040, 048
        translation_range_max = (
            translation_range_max_1,
            translation_range_max_2,
            translation_range_max_3,
            translation_range_max_4,
        )

        # 052, 056, 060, 064
        translation = (
            translation_x,
            translation_y,
            translation_z,
            translation_w,
        )

        # 124, 128, 132, 136, 140, 144
        xyz_rotation = (
            xyz_rotation_0,
            xyz_rotation_1,
            xyz_rotation_2,
            xyz_rotation_3,
            xyz_rotation_4,
            xyz_rotation_5,
        )

        # 160, 164, 168, 172, 176, 180
        scale = (
            scale_0,
            scale_1,
            scale_2,
            scale_3,
            scale_4,
            scale_5,
        )

        bounce_sequence = []
        bounce_sounds = []

        assert_eq("bounce seq 0 sentinel", -1, bounce_seq0_sentinel, reader.prev + 228)
        with assert_ascii("bounce seq 0 name", bounce_seq0_name_raw, reader.prev + 196):
            bounce_seq0_name = ascii_zterm_padded(bounce_seq0_name_raw)
        if bounce_seq0_name:
            bounce_sequence.append(bounce_seq0_name)

        if bounce_seq0_sound:
            assert_gt("bounce seq 0 volume", 0.0, bounce_seq0_volume, reader.prev + 232)
            sound = anim_def.get_sound(bounce_seq0_sound - 1, reader.prev + 230)
            bounce_sounds.append((sound, bounce_seq0_volume))
        else:
            assert_eq("bounce seq 0 sound", 0, bounce_seq0_sound, reader.prev + 230)
            assert_eq("bounce seq 0 volume", 0.0, bounce_seq0_volume, reader.prev + 232)

        assert_eq("bounce seq 1 sentinel", -1, bounce_seq1_sentinel, reader.prev + 268)
        with assert_ascii("bounce seq 1 name", bounce_seq1_name_raw, reader.prev + 236):
            bounce_seq1_name = ascii_zterm_padded(bounce_seq1_name_raw)
        if bounce_seq1_name:
            bounce_sequence.append(bounce_seq1_name)

        if bounce_seq1_sound:
            assert_gt("bounce seq 1 volume", 0.0, bounce_seq1_volume, reader.prev + 272)
            sound = anim_def.get_sound(bounce_seq1_sound - 1, reader.prev + 270)
            bounce_sounds.append((sound, bounce_seq1_volume))
        else:
            assert_eq("bounce seq 1 sound", 0, bounce_seq1_sound, reader.prev + 270)
            assert_eq("bounce seq 1 volume", 0.0, bounce_seq1_volume, reader.prev + 272)

        assert_eq("bounce seq 2 sentinel", -1, bounce_seq2_sentinel, reader.prev + 308)
        with assert_ascii("bounce seq 2 name", bounce_seq2_name_raw, reader.prev + 276):
            bounce_seq2_name = ascii_zterm_padded(bounce_seq2_name_raw)
        if bounce_seq2_name:
            bounce_sequence.append(bounce_seq2_name)

        if bounce_seq2_sound:
            assert_gt("bounce seq 2 volume", 0.0, bounce_seq2_volume, reader.prev + 312)
            sound = anim_def.get_sound(bounce_seq2_sound - 1, reader.prev + 310)
            bounce_sounds.append((sound, bounce_seq2_volume))
        else:
            assert_eq("bounce seq 2 sound", 0, bounce_seq2_sound, reader.prev + 310)
            assert_eq("bounce seq 2 volume", 0.0, bounce_seq2_volume, reader.prev + 312)

        assert_ge("run time", 0.0, run_time, reader.prev + 316)

        assert_eq("field 008", 0.0, unk008, reader.prev + 8)
        assert_eq("field 016", 0.0, unk016, reader.prev + 16)

        # assert_eq("field 068", 0.0, unk068, reader.prev + 68)  # -3.0
        # assert_eq("field 072", 0.0, unk072, reader.prev + 72)  # -3.0

        assert_eq("field 076", 0.0, unk076, reader.prev + 76)
        assert_eq("field 080", 0.0, unk080, reader.prev + 80)
        assert_eq("field 084", 0.0, unk084, reader.prev + 84)
        assert_eq("field 088", 0.0, unk088, reader.prev + 88)
        assert_eq("field 092", 0.0, unk092, reader.prev + 92)
        assert_eq("field 096", 0.0, unk096, reader.prev + 96)

        # assert_eq("field 100", 0.0, unk100, reader.prev + 100)  # -0.17023208737373352
        # assert_eq("field 104", 0.0, unk104, reader.prev + 104)  # -1.0
        # assert_eq("field 108", 0, unk108, reader.prev + 108) 3212836864

        forward_rotation = (
            degrees(forward_rotation_0),
            degrees(forward_rotation_1),
        )

        assert_eq("field 120", 0.0, unk120, reader.prev + 120)

        assert_eq("field 148", 0.0, unk148, reader.prev + 148)
        assert_eq("field 152", 0.0, unk152, reader.prev + 152)
        assert_eq("field 156", 0.0, unk156, reader.prev + 156)

        assert_eq("field 184", 0.0, unk184, reader.prev + 184)
        assert_eq("field 188", 0.0, unk188, reader.prev + 188)
        assert_eq("field 192", 0.0, unk192, reader.prev + 192)

        unk = [
            unk000,
            unk068,
            unk072,
            unk100,
            unk104,
            unk108,
        ]

        return cls(
            node=node,
            gravity=gravity,
            translation_range_min=translation_range_min,
            translation_range_max=translation_range_max,
            translation=translation,
            forward_rotation=forward_rotation,
            xyz_rotation=xyz_rotation,
            scale=scale,
            bounce_sequence=bounce_sequence,
            bounce_sounds=bounce_sounds,
            run_time=run_time,
            unk=unk,
        )

    def __repr__(self) -> str:
        return "\n".join(
            [
                f"{self._NAME}(",
                f"  NAME={self.node!r},",
                f"  GRAVITY={self.gravity},",
                f"  TRANSLATION_RANGE_MIN={self.translation_range_min},",
                f"  TRANSLATION_RANGE_MAX={self.translation_range_max},",
                f"  TRANSLATION={self.translation},",
                f"  FORWARD_ROTATION={self.forward_rotation},",
                f"  XYZ_ROTATION={self.xyz_rotation},",
                f"  SCALE={self.scale},",
                f"  BOUNCE_SEQUENCE={self.bounce_sequence},",
                f"  BOUNCE_SOUNDS={self.bounce_sounds},",
                f"  RUN_TIME={self.run_time},",
                f"  UNK={self.unk},",
                ")",
            ]
        )


class ObjectMotionFromTo(ScriptObject):
    _NAME: str = "OBJECT_MOTION_FROM_TO"
    _NUMBER: int = 11
    _STRUCT: Struct = Struct("<2I 31f")

    node: str
    type: int

    morph_from: float = 0.0
    morph_to: float = 0.0
    morph_delta: float = 0.0

    translate_from: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    translate_to: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    translate_delta: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    rotate_from: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotate_to: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotate_delta: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    scale_from: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale_to: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale_delta: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    run_time: float = 0.0

    @classmethod
    def read(  # pylint: disable=too-many-locals
        cls, reader: BinReader, anim_def: AnimDef
    ) -> ObjectMotionFromTo:
        (
            motion_type,  # 000
            index,  # 004
            morph_from,  # 008
            morph_to,  # 012
            morph_delta,  # 016
            translate_from_x,  # 020
            translate_from_y,  # 024
            translate_from_z,  # 028
            translate_to_x,  # 032
            translate_to_y,  # 036
            translate_to_z,  # 040
            translate_delta_x,  # 044
            translate_delta_y,  # 048
            translate_delta_z,  # 052
            rotate_from_x,  # 056
            rotate_from_y,  # 060
            rotate_from_z,  # 064
            rotate_to_x,  # 068
            rotate_to_y,  # 072
            rotate_to_z,  # 076
            rotate_delta_x,  # 080
            rotate_delta_y,  # 084
            rotate_delta_z,  # 088
            scale_from_x,  # 092
            scale_from_y,  # 096
            scale_from_z,  # 100
            scale_to_x,  # 104
            scale_to_y,  # 108
            scale_to_z,  # 112
            scale_delta_x,  # 116
            scale_delta_y,  # 120
            scale_delta_z,  # 124
            run_time,  # 128
        ) = reader.read(cls._STRUCT)

        assert_in("type", (1, 2, 4, 8), motion_type, reader.prev + 0)
        node = anim_def.get_node(index - 1, reader.prev + 4)

        if motion_type != 8:
            assert_eq("morph from", 0.0, morph_from, reader.prev + 8)
            assert_eq("morph to", 0.0, morph_to, reader.prev + 12)
            assert_eq("morph delta", 0.0, morph_delta, reader.prev + 16)

        if motion_type != 1:
            assert_eq("translate from x", 0.0, translate_from_x, reader.prev + 20)
            assert_eq("translate from y", 0.0, translate_from_y, reader.prev + 24)
            assert_eq("translate from z", 0.0, translate_from_z, reader.prev + 28)
            assert_eq("translate to x", 0.0, translate_to_x, reader.prev + 32)
            assert_eq("translate to y", 0.0, translate_to_y, reader.prev + 36)
            assert_eq("translate to z", 0.0, translate_to_z, reader.prev + 40)
            assert_eq("translate delta x", 0.0, translate_delta_x, reader.prev + 44)
            assert_eq("translate delta y", 0.0, translate_delta_y, reader.prev + 48)
            assert_eq("translate delta z", 0.0, translate_delta_z, reader.prev + 52)

        if motion_type != 2:
            assert_eq("rotate from x", 0.0, rotate_from_x, reader.prev + 56)
            assert_eq("rotate from y", 0.0, rotate_from_y, reader.prev + 60)
            assert_eq("rotate from z", 0.0, rotate_from_z, reader.prev + 64)
            assert_eq("rotate to x", 0.0, rotate_to_x, reader.prev + 68)
            assert_eq("rotate to y", 0.0, rotate_to_y, reader.prev + 72)
            assert_eq("rotate to z", 0.0, rotate_to_z, reader.prev + 76)
            assert_eq("rotate delta x", 0.0, rotate_delta_x, reader.prev + 80)
            assert_eq("rotate delta y", 0.0, rotate_delta_y, reader.prev + 84)
            assert_eq("rotate delta z", 0.0, rotate_delta_z, reader.prev + 88)

        if motion_type != 4:
            assert_eq("scale from x", 0.0, scale_from_x, reader.prev + 92)
            assert_eq("scale from y", 0.0, scale_from_y, reader.prev + 96)
            assert_eq("scale from z", 0.0, scale_from_z, reader.prev + 100)
            assert_eq("scale to x", 0.0, scale_to_x, reader.prev + 104)
            assert_eq("scale to y", 0.0, scale_to_y, reader.prev + 108)
            assert_eq("scale to z", 0.0, scale_to_z, reader.prev + 112)
            assert_eq("scale delta x", 0.0, scale_delta_x, reader.prev + 116)
            assert_eq("scale delta y", 0.0, scale_delta_y, reader.prev + 120)
            assert_eq("scale delta z", 0.0, scale_delta_z, reader.prev + 124)

        assert_gt("run time", 0.0, run_time, reader.prev + 128)

        translate_from = (translate_from_x, translate_from_y, translate_from_z)
        translate_to = (translate_to_x, translate_to_y, translate_to_z)
        translate_delta = (translate_delta_x, translate_delta_y, translate_delta_z)

        rotate_from = (
            degrees(rotate_from_x),
            degrees(rotate_from_y),
            degrees(rotate_from_z),
        )
        rotate_to = (degrees(rotate_to_x), degrees(rotate_to_y), degrees(rotate_to_z))
        rotate_delta = (
            degrees(rotate_delta_x),
            degrees(rotate_delta_y),
            degrees(rotate_delta_z),
        )

        scale_from = (scale_from_x, scale_from_y, scale_from_z)
        scale_to = (scale_to_x, scale_to_y, scale_to_z)
        scale_delta = (scale_delta_x, scale_delta_y, scale_delta_z)

        return cls(
            node=node,
            type=motion_type,
            morph_from=morph_from,
            morph_to=morph_to,
            morph_delta=morph_delta,
            translate_from=translate_from,
            translate_to=translate_to,
            translate_delta=translate_delta,
            rotate_from=rotate_from,
            rotate_to=rotate_to,
            rotate_delta=rotate_delta,
            scale_from=scale_from,
            scale_to=scale_to,
            scale_delta=scale_delta,
            run_time=run_time,
        )

    def __repr__(self) -> str:
        return "\n".join(
            [
                f"{self._NAME}(",
                f"  NAME={self.node!r}, TYPE={self.type},",
                f"  MORPH_FROM={self.morph_from},",
                f"  MORPH_TO={self.morph_to},",
                f"  TRANSLATE_FROM={self.translate_from},",
                f"  TRANSLATE_TO={self.translate_to},",
                f"  ROTATE_FROM={self.rotate_from},",
                f"  ROTATE_TO={self.rotate_to},",
                f"  SCALE_FROM={self.scale_from},",
                f"  SCALE_TO={self.scale_to},",
                f"  RUN_TIME={self.run_time},",
                ")",
            ]
        )
