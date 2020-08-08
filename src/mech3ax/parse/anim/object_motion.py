from __future__ import annotations

from math import degrees
from struct import Struct
from typing import List, Literal, Optional, Tuple, Union

from pydantic import BaseModel

from mech3ax.errors import (
    assert_all_zero,
    assert_ascii,
    assert_eq,
    assert_flag,
    assert_gt,
    assert_in,
    assert_lt,
    assert_ne,
)

from ..int_flag import IntFlag
from ..utils import BinReader, ascii_zterm_padded
from .models import AnimDef, ScriptObject

DUMMY_IMPORT = None
DEFAULT_GRAVITY = -9.800000190734863

Vec4 = Tuple[float, float, float, float]
Vec6 = Tuple[float, float, float, float, float, float]
Vec9 = Tuple[float, float, float, float, float, float, float, float, float]

ForwardRotationMode = Union[Literal["TIME"], Literal["DISTANCE"]]
ForwardRotation = Optional[Tuple[ForwardRotationMode, float, float]]

GravityMode = Union[Literal["LOCAL"], Literal["COMPLEX"], Literal["NO_ALTITUDE"]]
Gravity = Optional[Tuple[GravityMode, float]]


class MotionFlag(IntFlag):
    Gravity = 1 << 0
    ImpactForce = 1 << 1
    Translation = 1 << 2
    TranslationMin = 1 << 3
    TranslationMax = 1 << 4
    XYZRotation = 1 << 5
    ForwardRotationDistance = 1 << 6
    ForwardRotationTime = 1 << 7
    Scale = 1 << 8
    RunTime = 1 << 10
    BounceSeq = 1 << 11
    BounceSound = 1 << 12
    GravityComplex = 1 << 13
    GravityNoAltitude = 1 << 14


class ObjectMotion(ScriptObject):
    _NAME: str = "OBJECT_MOTION"
    _NUMBER: int = 10
    _STRUCT: Struct = Struct(
        "<2I 3f 8f 6f 6f 3f 3f 6f 3f 6f 3f 32s 2hf 32s 2hf 32s 2hf f"
    )

    node: str
    gravity: Gravity = None
    impact_force: bool = False
    translation_range_min: Optional[Vec4] = None
    translation_range_max: Optional[Vec4] = None
    translation: Optional[Vec9] = None
    forward_rotation: ForwardRotation = None
    xyz_rotation: Optional[Vec6] = None
    scale: Optional[Vec6] = None
    bounce_sequence: List[str] = []
    bounce_sounds: List[Tuple[str, float]] = []
    run_time: Optional[float] = None

    @classmethod
    def read(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        cls, reader: BinReader, anim_def: AnimDef
    ) -> ObjectMotion:
        (
            flag_raw,  # 000, 012
            node_index,  # 004, 016
            zero008,  # 008, 020
            gravity_value,  # 012, 024
            zero016,  # 016, 028
            trans_range_min_1,  # 020, 032
            trans_range_max_1,  # 024, 036
            trans_range_min_2,  # 028, 040
            trans_range_max_2,  # 032, 044
            trans_range_min_3,  # 036, 048
            trans_range_max_3,  # 040, 052
            trans_range_min_4,  # 044, 056
            trans_range_max_4,  # 048, 060
            translation_1,  # 052, 064
            translation_2,  # 056, 068
            translation_3,  # 060, 072
            translation_4,  # 064, 076
            translation_5,  # 068, 080
            translation_6,  # 072, 084
            # used for translation calculations
            zero076,  # 076, 088
            zero080,  # 080, 092
            zero084,  # 084, 096
            zero088,  # 088, 100
            zero092,  # 092, 104
            zero096,  # 096, 108
            # used for translation calculations
            unk100,  # 100, 112
            unk104,  # 104, 116
            unk108,  # 108, 120
            # FORWARD_ROTATION
            forward_rotation_1,  # 112, 124
            forward_rotation_2,  # 116, 128
            zero120,  # 120, 132
            # XYZ_ROTATION
            xyz_rotation_1,  # 124, 136
            xyz_rotation_2,  # 128, 140
            xyz_rotation_3,  # 132, 144
            xyz_rotation_4,  # 136, 148
            xyz_rotation_5,  # 140, 152
            xyz_rotation_6,  # 144, 156
            # used for xyz rotation calculations
            zero148,  # 148, 160
            zero152,  # 152, 164
            zero156,  # 156, 168
            scale_1,  # 160, 172
            scale_2,  # 164, 176
            scale_3,  # 168, 180
            scale_4,  # 172, 184
            scale_5,  # 176, 188
            scale_6,  # 180, 192
            # used for scale calculations
            zero184,  # 184, 196
            zero188,  # 188, 200
            zero192,  # 192, 204
            bounce_seq0_name_raw,  # 196, 208
            bounce_seq0_sentinel,  # 228, 240
            bounce_snd0_index,  # 230, 242
            bounce_snd0_volume,  # 232, 244
            bounce_seq1_name_raw,  # 236, 248
            bounce_seq1_sentinel,  # 268, 280
            bounce_snd1_index,  # 270, 282
            bounce_snd1_volume,  # 272, 284
            bounce_seq2_name_raw,  # 276, 288
            bounce_seq2_sentinel,  # 308, 320
            bounce_snd2_index,  # 310, 322
            bounce_snd2_volume,  # 312, 324
            run_time,  # 316, 328
        ) = reader.read(cls._STRUCT)

        assert_lt("flag", 0x7FFF, flag_raw, reader.prev + 0)
        with assert_flag("flag", flag_raw, reader.prev + 0):
            flag = MotionFlag.check(flag_raw)

        node = anim_def.get_node(node_index - 1, reader.prev + 4)
        assert_eq("field 008", 0.0, zero008, reader.prev + 8)
        assert_eq("field 016", 0.0, zero016, reader.prev + 16)

        gravity_no_alt = MotionFlag.GravityNoAltitude(flag)
        gravity_complex = MotionFlag.GravityComplex(flag)

        if not MotionFlag.Gravity(flag):
            assert_eq("gravity", 0.0, gravity_value, reader.prev + 12)
            assert_eq("gravity no alt", False, gravity_no_alt, reader.prev + 0)
            assert_eq("gravity complex", False, gravity_complex, reader.prev + 0)
            gravity: Gravity = None
        elif gravity_no_alt:
            assert_eq("gravity complex", False, gravity_complex, reader.prev + 0)
            gravity = ("NO_ALTITUDE", gravity_value)
        elif gravity_complex:
            gravity = ("COMPLEX", gravity_value)
        else:
            gravity = ("LOCAL", gravity_value)

        if MotionFlag.TranslationMin(flag):
            translation_range_min: Optional[Vec4] = (
                trans_range_min_1,
                trans_range_min_2,
                trans_range_min_3,
                trans_range_min_4,
            )
        else:
            assert_eq("trans range min 1", 0.0, trans_range_min_1, reader.prev + 20)
            assert_eq("trans range min 2", 0.0, trans_range_min_2, reader.prev + 28)
            assert_eq("trans range min 3", 0.0, trans_range_min_3, reader.prev + 36)
            assert_eq("trans range min 4", 0.0, trans_range_min_4, reader.prev + 44)
            translation_range_min = None

        if MotionFlag.TranslationMax(flag):
            translation_range_max: Optional[Vec4] = (
                trans_range_max_1,
                trans_range_max_2,
                trans_range_max_3,
                trans_range_max_4,
            )
        else:
            assert_eq("trans range max 1", 0.0, trans_range_max_1, reader.prev + 24)
            assert_eq("trans range max 2", 0.0, trans_range_max_2, reader.prev + 32)
            assert_eq("trans range max 3", 0.0, trans_range_max_3, reader.prev + 40)
            assert_eq("trans range max 4", 0.0, trans_range_max_4, reader.prev + 48)
            translation_range_max = None

        if MotionFlag.Translation(flag):
            translation: Optional[Vec9] = (
                translation_1,
                translation_2,
                translation_3,
                translation_4,
                translation_5,
                translation_6,
                unk100,
                unk104,
                unk108,
            )
        else:
            assert_eq("translation 1", 0.0, translation_1, reader.prev + 52)
            assert_eq("translation 2", 0.0, translation_2, reader.prev + 56)
            assert_eq("translation 3", 0.0, translation_3, reader.prev + 60)
            assert_eq("translation 4", 0.0, translation_4, reader.prev + 64)
            assert_eq("translation 5", 0.0, translation_5, reader.prev + 68)
            assert_eq("translation 6", 0.0, translation_6, reader.prev + 72)
            assert_eq("field 100", 0.0, unk100, reader.prev + 100)
            assert_eq("field 104", 0.0, unk104, reader.prev + 104)
            assert_eq("field 108", 0.0, unk108, reader.prev + 108)
            translation = None

        assert_eq("field 076", 0.0, zero076, reader.prev + 76)
        assert_eq("field 080", 0.0, zero080, reader.prev + 80)
        assert_eq("field 084", 0.0, zero084, reader.prev + 84)
        assert_eq("field 088", 0.0, zero088, reader.prev + 88)
        assert_eq("field 092", 0.0, zero092, reader.prev + 92)
        assert_eq("field 096", 0.0, zero096, reader.prev + 96)

        if MotionFlag.ForwardRotationTime(flag):
            forward_rotation: ForwardRotation = (
                "TIME",
                forward_rotation_1,
                forward_rotation_2,
            )
        elif MotionFlag.ForwardRotationDistance(flag):
            assert_eq("fwd rot 2", 0.0, forward_rotation_2, reader.prev + 116)
            forward_rotation = (
                "DISTANCE",
                forward_rotation_1,
                0.0,
            )
        else:
            assert_eq("fwd rot 1", 0.0, forward_rotation_1, reader.prev + 112)
            assert_eq("fwd rot 2", 0.0, forward_rotation_2, reader.prev + 116)
            forward_rotation = None

        assert_eq("field 120", 0.0, zero120, reader.prev + 120)

        if MotionFlag.XYZRotation(flag):
            xyz_rotation: Optional[Vec6] = (
                xyz_rotation_1,
                xyz_rotation_2,
                xyz_rotation_3,
                xyz_rotation_4,
                xyz_rotation_5,
                xyz_rotation_6,
            )
        else:
            assert_eq("xyz rot 1", 0.0, xyz_rotation_1, reader.prev + 124)
            assert_eq("xyz rot 2", 0.0, xyz_rotation_2, reader.prev + 128)
            assert_eq("xyz rot 3", 0.0, xyz_rotation_3, reader.prev + 132)
            assert_eq("xyz rot 4", 0.0, xyz_rotation_4, reader.prev + 136)
            assert_eq("xyz rot 5", 0.0, xyz_rotation_5, reader.prev + 140)
            assert_eq("xyz rot 6", 0.0, xyz_rotation_6, reader.prev + 144)
            xyz_rotation = None

        assert_eq("field 148", 0.0, zero148, reader.prev + 148)
        assert_eq("field 152", 0.0, zero152, reader.prev + 152)
        assert_eq("field 156", 0.0, zero156, reader.prev + 156)

        if MotionFlag.Scale(flag):
            scale: Optional[Vec6] = (
                scale_1,
                scale_2,
                scale_3,
                scale_4,
                scale_5,
                scale_6,
            )
        else:
            assert_eq("scale 1", 0.0, scale_1, reader.prev + 160)
            assert_eq("scale 2", 0.0, scale_2, reader.prev + 164)
            assert_eq("scale 3", 0.0, scale_3, reader.prev + 168)
            assert_eq("scale 4", 0.0, scale_4, reader.prev + 172)
            assert_eq("scale 5", 0.0, scale_5, reader.prev + 176)
            assert_eq("scale 6", 0.0, scale_6, reader.prev + 180)
            scale = None

        assert_eq("field 184", 0.0, zero184, reader.prev + 184)
        assert_eq("field 188", 0.0, zero188, reader.prev + 188)
        assert_eq("field 192", 0.0, zero192, reader.prev + 192)

        assert_eq("bounce seq 0 sentinel", -1, bounce_seq0_sentinel, reader.prev + 228)
        assert_eq("bounce seq 1 sentinel", -1, bounce_seq1_sentinel, reader.prev + 268)
        assert_eq("bounce seq 2 sentinel", -1, bounce_seq2_sentinel, reader.prev + 308)

        bounce_sequence = []
        if MotionFlag.BounceSeq(flag):
            with assert_ascii(
                "bounce seq 0 name", bounce_seq0_name_raw, reader.prev + 196
            ):
                bounce_seq0_name = ascii_zterm_padded(bounce_seq0_name_raw)

            # should have at least one value
            assert_ne("bounce seq 0 name", "", bounce_seq0_name, reader.prev + 196)
            bounce_sequence.append(bounce_seq0_name)

            with assert_ascii(
                "bounce seq 1 name", bounce_seq1_name_raw, reader.prev + 236
            ):
                bounce_seq1_name = ascii_zterm_padded(bounce_seq1_name_raw)
            if bounce_seq1_name:
                bounce_sequence.append(bounce_seq1_name)

            with assert_ascii(
                "bounce seq 2 name", bounce_seq2_name_raw, reader.prev + 276
            ):
                bounce_seq2_name = ascii_zterm_padded(bounce_seq2_name_raw)
            if bounce_seq2_name:
                bounce_sequence.append(bounce_seq2_name)

        else:
            assert_all_zero(
                "bounce seq 0 name", bounce_seq0_name_raw, reader.prev + 196
            )
            assert_all_zero(
                "bounce seq 1 name", bounce_seq1_name_raw, reader.prev + 236
            )
            assert_all_zero(
                "bounce seq 2 name", bounce_seq2_name_raw, reader.prev + 276
            )

        bounce_sounds = []
        if MotionFlag.BounceSound(flag):

            # should have at least one value
            assert_gt("bounce snd 0 volume", 0.0, bounce_snd0_volume, reader.prev + 232)
            sound = anim_def.get_sound(bounce_snd0_index - 1, reader.prev + 230)
            bounce_sounds.append((sound, bounce_snd0_volume))

            if bounce_snd1_index:
                assert_gt(
                    "bounce snd 1 volume", 0.0, bounce_snd1_volume, reader.prev + 272
                )
                sound = anim_def.get_sound(bounce_snd1_index - 1, reader.prev + 270)
                bounce_sounds.append((sound, bounce_snd1_volume))
            else:
                assert_eq(
                    "bounce snd 1 volume", 0.0, bounce_snd1_volume, reader.prev + 272
                )

            if bounce_snd2_index:
                assert_gt(
                    "bounce snd 2 volume", 0.0, bounce_snd2_volume, reader.prev + 312
                )
                sound = anim_def.get_sound(bounce_snd2_index - 1, reader.prev + 310)
                bounce_sounds.append((sound, bounce_snd2_volume))
            else:
                assert_eq(
                    "bounce snd 2 volume", 0.0, bounce_snd2_volume, reader.prev + 312
                )

        else:
            assert_eq("bounce snd 0 sound", 0, bounce_snd0_index, reader.prev + 230)
            assert_eq("bounce snd 0 volume", 0.0, bounce_snd0_volume, reader.prev + 232)

            assert_eq("bounce snd 1 sound", 0, bounce_snd1_index, reader.prev + 270)
            assert_eq("bounce snd 1 volume", 0.0, bounce_snd1_volume, reader.prev + 272)

            assert_eq("bounce snd 2 sound", 0, bounce_snd2_index, reader.prev + 310)
            assert_eq("bounce snd 2 volume", 0.0, bounce_snd2_volume, reader.prev + 312)

        if MotionFlag.RunTime(flag):
            assert_gt("run time", 0.0, run_time, reader.prev + 316)
        else:
            assert_eq("run time", 0.0, run_time, reader.prev + 316)
            run_time = None

        return cls(
            node=node,
            gravity=gravity,
            impact_force=MotionFlag.ImpactForce(flag),
            translation_range_min=translation_range_min,
            translation_range_max=translation_range_max,
            translation=translation,
            forward_rotation=forward_rotation,
            xyz_rotation=xyz_rotation,
            scale=scale,
            bounce_sequence=bounce_sequence,
            bounce_sounds=bounce_sounds,
            run_time=run_time,
        )

    def __repr__(self) -> str:
        impact = " IMPACT_FORCE," if self.impact_force else ""
        return "\n".join(
            [
                f"{self._NAME}(",
                f"  NAME={self.node!r},{impact}",
                f"  GRAVITY={self.gravity}",
                f"  TRANSLATION_RANGE_MIN={self.translation_range_min},",
                f"  TRANSLATION_RANGE_MAX={self.translation_range_max},",
                f"  TRANSLATION={self.translation}",
                f"  FORWARD_ROTATION={self.forward_rotation},",
                f"  XYZ_ROTATION={self.xyz_rotation},",
                f"  SCALE={self.scale},",
                f"  BOUNCE_SEQUENCE={self.bounce_sequence},",
                f"  BOUNCE_SOUNDS={self.bounce_sounds},",
                f"  RUN_TIME={self.run_time},",
                ")",
            ]
        )


Vec3 = Tuple[float, float, float]


class Vec3FromTo(BaseModel):
    from_: Vec3
    to_: Vec3
    delta: Vec3

    def __repr__(self) -> str:
        return f"(FROM={self.from_}, TO={self.to_})"


class ObjectMotionFromTo(ScriptObject):
    _NAME: str = "OBJECT_MOTION_FROM_TO"
    _NUMBER: int = 11
    _STRUCT: Struct = Struct("<2I 31f")

    node: str
    morph: Optional[Vec3] = None
    translate: Optional[Vec3FromTo] = None
    rotate: Optional[Vec3FromTo] = None
    scale: Optional[Vec3FromTo] = None
    run_time: float = 0.0

    @classmethod
    def read(  # pylint: disable=too-many-locals,too-many-statements
        cls, reader: BinReader, anim_def: AnimDef
    ) -> ObjectMotionFromTo:
        (
            flag_raw,  # 000
            node_index,  # 004
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

        # these only appear in mutually exclusive combinations, but it really is
        # a flag in the game code
        assert_in("flag", (1, 2, 4, 8), flag_raw, reader.prev + 0)
        node = anim_def.get_node(node_index - 1, reader.prev + 4)

        if flag_raw == 8:
            morph: Optional[Vec3] = (morph_from, morph_to, morph_delta)
        else:
            assert_eq("morph from", 0.0, morph_from, reader.prev + 8)
            assert_eq("morph to", 0.0, morph_to, reader.prev + 12)
            assert_eq("morph delta", 0.0, morph_delta, reader.prev + 16)
            morph = None

        if flag_raw == 1:
            translate: Optional[Vec3FromTo] = Vec3FromTo(
                from_=(translate_from_x, translate_from_y, translate_from_z),
                to_=(translate_to_x, translate_to_y, translate_to_z),
                delta=(translate_delta_x, translate_delta_y, translate_delta_z),
            )
        else:
            assert_eq("translate from x", 0.0, translate_from_x, reader.prev + 20)
            assert_eq("translate from y", 0.0, translate_from_y, reader.prev + 24)
            assert_eq("translate from z", 0.0, translate_from_z, reader.prev + 28)
            assert_eq("translate to x", 0.0, translate_to_x, reader.prev + 32)
            assert_eq("translate to y", 0.0, translate_to_y, reader.prev + 36)
            assert_eq("translate to z", 0.0, translate_to_z, reader.prev + 40)
            assert_eq("translate delta x", 0.0, translate_delta_x, reader.prev + 44)
            assert_eq("translate delta y", 0.0, translate_delta_y, reader.prev + 48)
            assert_eq("translate delta z", 0.0, translate_delta_z, reader.prev + 52)
            translate = None

        if flag_raw == 2:
            rotate: Optional[Vec3FromTo] = Vec3FromTo(
                from_=(
                    degrees(rotate_from_x),
                    degrees(rotate_from_y),
                    degrees(rotate_from_z),
                ),
                to_=(degrees(rotate_to_x), degrees(rotate_to_y), degrees(rotate_to_z)),
                delta=(
                    degrees(rotate_delta_x),
                    degrees(rotate_delta_y),
                    degrees(rotate_delta_z),
                ),
            )
        else:
            assert_eq("rotate from x", 0.0, rotate_from_x, reader.prev + 56)
            assert_eq("rotate from y", 0.0, rotate_from_y, reader.prev + 60)
            assert_eq("rotate from z", 0.0, rotate_from_z, reader.prev + 64)
            assert_eq("rotate to x", 0.0, rotate_to_x, reader.prev + 68)
            assert_eq("rotate to y", 0.0, rotate_to_y, reader.prev + 72)
            assert_eq("rotate to z", 0.0, rotate_to_z, reader.prev + 76)
            assert_eq("rotate delta x", 0.0, rotate_delta_x, reader.prev + 80)
            assert_eq("rotate delta y", 0.0, rotate_delta_y, reader.prev + 84)
            assert_eq("rotate delta z", 0.0, rotate_delta_z, reader.prev + 88)
            rotate = None

        if flag_raw == 4:
            scale: Optional[Vec3FromTo] = Vec3FromTo(
                from_=(scale_from_x, scale_from_y, scale_from_z),
                to_=(scale_to_x, scale_to_y, scale_to_z),
                delta=(scale_delta_x, scale_delta_y, scale_delta_z),
            )
        else:
            assert_eq("scale from x", 0.0, scale_from_x, reader.prev + 92)
            assert_eq("scale from y", 0.0, scale_from_y, reader.prev + 96)
            assert_eq("scale from z", 0.0, scale_from_z, reader.prev + 100)
            assert_eq("scale to x", 0.0, scale_to_x, reader.prev + 104)
            assert_eq("scale to y", 0.0, scale_to_y, reader.prev + 108)
            assert_eq("scale to z", 0.0, scale_to_z, reader.prev + 112)
            assert_eq("scale delta x", 0.0, scale_delta_x, reader.prev + 116)
            assert_eq("scale delta y", 0.0, scale_delta_y, reader.prev + 120)
            assert_eq("scale delta z", 0.0, scale_delta_z, reader.prev + 124)
            scale = None

        assert_gt("run time", 0.0, run_time, reader.prev + 128)

        return cls(
            node=node,
            morph=morph,
            translate=translate,
            rotate=rotate,
            scale=scale,
            run_time=run_time,
        )

    def __repr__(self) -> str:
        if self.morph:
            from_, to_, _ = self.morph  # pylint: disable=unpacking-non-sequence
            morph = f"(FROM={from_}, TO={to_})"
        else:
            morph = "None"
        return "\n".join(
            [
                f"{self._NAME}(",
                f"  NAME={self.node!r},",
                f"  MORPH={morph},",
                f"  TRANSLATE={self.translate},",
                f"  ROTATE={self.rotate},",
                f"  SCALE={self.scale},",
                f"  RUN_TIME={self.run_time},",
                ")",
            ]
        )
