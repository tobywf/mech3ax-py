from __future__ import annotations

from struct import Struct
from typing import Optional, Tuple

from mech3ax.errors import (
    assert_ascii,
    assert_between,
    assert_eq,
    assert_flag,
    assert_ge,
    assert_gt,
    assert_in,
    assert_lt,
)

from ..int_flag import IntFlag
from ..utils import BinReader, ascii_zterm_padded
from .models import INPUT_NODE, AnimDef, AtNodeShort, ScriptObject

DUMMY_IMPORT = None


class LightFlag(IntFlag):
    Inactive = 0
    # This flag never occurs in animations, but does in GameZ
    TranslationAbs = 1 << 0
    Translation = 1 << 1
    Rotation = 1 << 2
    Range = 1 << 3
    Color = 1 << 4
    Ambient = 1 << 5
    Diffuse = 1 << 6
    Directional = 1 << 7
    Saturated = 1 << 8
    Subdivide = 1 << 9
    Static = 1 << 10


Range = Optional[Tuple[float, float]]
Color = Optional[Tuple[float, float, float]]


class LightState(ScriptObject):
    _NAME: str = "LIGHT_STATE"
    _NUMBER: int = 4
    _STRUCT: Struct = Struct("<32s I 4I 3I i 3f 3f 2f 3f 2f")

    name: str
    active_state: bool
    at_node: Optional[AtNodeShort] = None
    range: Range = None
    color: Color = None
    ambient: Optional[float] = None
    diffuse: Optional[float] = None
    subdivide: Optional[bool] = None
    saturated: Optional[bool] = None
    directional: Optional[bool] = None
    static: Optional[bool] = None

    @classmethod
    def read(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        cls, reader: BinReader, anim_def: AnimDef
    ) -> LightState:
        (
            name_raw,
            light_index,
            flag_raw,
            active_state_raw,
            point_source_raw,
            directional_raw,
            saturated_raw,
            subdivide_raw,
            static_raw,
            node_index,
            tx,
            ty,
            tz,
            rx,
            ry,
            rz,
            range_min,
            range_max,
            color_r,
            color_g,
            color_b,
            ambient_value,
            diffuse_value,
        ) = reader.read(cls._STRUCT)

        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        expected_name = anim_def.get_light(light_index - 1, reader.prev + 32)
        assert_eq("index name", expected_name, name, reader.prev + 32)  # 44

        with assert_flag("flag", flag_raw, reader.prev + 36):
            flag = LightFlag.check(flag_raw)

        # 0 = directed (never set), 1 = point source
        assert_eq("point source", 1, point_source_raw, reader.prev + 44)  # 56

        active_state = flag != LightFlag.Inactive
        if anim_def.anim_name in ("impact_ppc_mech", "exp_flash", "exp_flash_small"):
            # unfortunately, in these few cases, the active state doesn't line up
            assert_in("active state", (0, 1), active_state_raw, reader.prev + 40)  # 52
        else:
            expected = 1 if active_state else 0
            assert_eq("active state", expected, active_state_raw, reader.prev + 40)

        # WARNING: the values are the state, and the flag indicates whether this
        # state should be set or not

        if LightFlag.Directional(flag):
            assert_in("directional", (0, 1), directional_raw, reader.prev + 48)  # 60
            directional = directional_raw == 1
        else:
            assert_eq("directional", 0, directional_raw, reader.prev + 48)
            directional = None

        if LightFlag.Saturated(flag):
            assert_in("saturated", (0, 1), saturated_raw, reader.prev + 52)  # 64
            saturated = saturated_raw == 1
        else:
            assert_eq("saturated", 0, saturated_raw, reader.prev + 52)
            saturated = None

        if LightFlag.Subdivide(flag):
            assert_in("subdivide", (0, 1), subdivide_raw, reader.prev + 56)  # 68
            subdivide = subdivide_raw == 1
        else:
            assert_eq("subdivide", 0, subdivide_raw, reader.prev + 56)
            subdivide = None

        if LightFlag.Static(flag):
            assert_in("static", (0, 1), static_raw, reader.prev + 60)  # 72
            static = static_raw == 1
        else:
            assert_eq("static", 0, static_raw, reader.prev + 60)
            static = None

        if not LightFlag.Translation(flag):
            assert_eq("at node", 0, node_index, reader.prev + 64)
            assert_eq("trans x", 0.0, tx, reader.prev + 68)
            assert_eq("trans y", 0.0, ty, reader.prev + 72)
            assert_eq("trans z", 0.0, tz, reader.prev + 76)
            assert_eq("rotation", False, LightFlag.Rotation(flag), reader.prev + 36)
            assert_eq("rot x", 0.0, rx, reader.prev + 80)
            assert_eq("rot y", 0.0, ry, reader.prev + 84)
            assert_eq("rot z", 0.0, rz, reader.prev + 88)

            at_node = None
        else:
            if node_index == -200:
                node = INPUT_NODE
            else:
                node = anim_def.get_node(node_index - 1, reader.prev + 64)

            # this is never set
            assert_eq("rotation", False, LightFlag.Rotation(flag), reader.prev + 36)
            assert_eq("rot x", 0.0, rx, reader.prev + 80)
            assert_eq("rot y", 0.0, ry, reader.prev + 84)
            assert_eq("rot z", 0.0, rz, reader.prev + 88)
            at_node = AtNodeShort(node=node, tx=tx, ty=ty, tz=tz)

        if LightFlag.Range(flag):
            assert_ge("range min", 0.0, range_min, reader.prev + 92)
            assert_ge("range max", range_min, range_max, reader.prev + 96)
            range_: Range = (range_min, range_max)
        else:
            assert_eq("range min", 0.0, range_min, reader.prev + 92)
            assert_eq("range max", 0.0, range_max, reader.prev + 96)
            range_ = None

        if LightFlag.Color(flag):
            assert_between("red", 0.0, 1.0, color_r, reader.prev + 100)
            assert_between("green", 0.0, 1.0, color_g, reader.prev + 104)
            assert_between("blue", 0.0, 1.0, color_b, reader.prev + 108)
            color: Color = (color_r, color_g, color_b)
        else:
            assert_eq("red", 0.0, color_r, reader.prev + 100)
            assert_eq("green", 0.0, color_g, reader.prev + 104)
            assert_eq("blue", 0.0, color_b, reader.prev + 108)
            color = None

        if LightFlag.Ambient(flag):
            assert_between("ambient", 0.0, 1.0, ambient_value, reader.prev + 112)
            ambient = ambient_value
        else:
            assert_eq("ambient", 0.0, ambient_value, reader.prev + 112)
            ambient = None

        if LightFlag.Diffuse(flag):
            assert_between("diffuse", 0.0, 1.0, diffuse_value, reader.prev + 116)
            diffuse = diffuse_value
        else:
            assert_eq("diffuse", 0.0, diffuse_value, reader.prev + 116)
            diffuse = None

        return cls(
            name=name,
            active_state=active_state,
            directional=directional,
            saturated=saturated,
            subdivide=subdivide,
            static=static,
            at_node=at_node,
            range=range_,
            color=color,
            ambient=ambient,
            diffuse=diffuse,
        )


class LightAnimation(ScriptObject):
    _NAME: str = "LIGHT_ANIMATION"
    _NUMBER: int = 5
    _STRUCT: Struct = Struct("<32s i 4f 2f 6f 3f f")

    name: str
    range: Tuple[float, float] = (0.0, 0.0)
    color: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    run_time: float

    @classmethod
    def read(  # pylint: disable=too-many-locals
        cls, reader: BinReader, anim_def: AnimDef
    ) -> LightAnimation:
        (
            name_raw,
            light_index,
            range_min,
            range_max,
            zero44,
            zero48,
            zero52,
            zero56,
            color_r,
            color_g,
            color_b,
            zero72,
            zero76,
            zero80,
            zero84,
            zero88,
            zero92,
            run_time,
        ) = reader.read(cls._STRUCT)

        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        expected_name = anim_def.get_light(light_index - 1, reader.prev + 32)
        assert_eq("index name", expected_name, name, reader.prev + 32)

        if range_min >= 0.0:
            assert_ge("range max", range_min, range_max, reader.prev + 40)
        else:
            assert_lt("range max", range_min, range_max, reader.prev + 40)

        assert_eq("field 44", 0, zero44, reader.prev + 44)
        assert_eq("field 48", 0, zero48, reader.prev + 48)
        assert_eq("field 52", 0, zero52, reader.prev + 52)
        assert_eq("field 56", 0, zero56, reader.prev + 56)

        assert_between("red", -5.0, 5.0, color_r, reader.prev + 60)
        assert_between("green", -5.0, 5.0, color_g, reader.prev + 64)
        assert_between("blue", -5.0, 5.0, color_b, reader.prev + 68)

        assert_eq("field 72", 0, zero72, reader.prev + 72)
        assert_eq("field 76", 0, zero76, reader.prev + 76)
        assert_eq("field 80", 0, zero80, reader.prev + 80)
        assert_eq("field 84", 0, zero84, reader.prev + 84)
        assert_eq("field 88", 0, zero88, reader.prev + 88)
        assert_eq("field 92", 0, zero92, reader.prev + 92)

        assert_gt("run time", 0.0, run_time, reader.prev + 96)

        return cls(
            name=name,
            range=(range_min, range_max),
            color=(color_r, color_g, color_b),
            run_time=run_time,
        )
