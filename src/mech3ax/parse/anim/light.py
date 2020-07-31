from __future__ import annotations

from struct import Struct
from typing import Optional, Tuple

from mech3ax.errors import (
    assert_ascii,
    assert_between,
    assert_eq,
    assert_ge,
    assert_gt,
    assert_in,
    assert_lt,
)

from ..utils import BinReader, ascii_zterm_padded
from .models import AnimDef, AtNodeLong, ScriptObject

DUMMY_IMPORT = None


class LightState(ScriptObject):
    _NAME: str = "LIGHT_STATE"
    _NUMBER: int = 4
    _STRUCT: Struct = Struct("<32s I 4I 3I i 3f 3f 2f 3f 2f")

    name: str
    active_state: bool
    at_node: Optional[AtNodeLong] = None
    range: Tuple[float, float] = (0.0, 0.0)
    color: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    ambient: float = 0.0
    diffuse: float = 0.0
    subdivide: bool = False
    saturated: bool = False
    directional: bool = False
    static: bool = False
    unk: int

    @classmethod
    def read(  # pylint: disable=too-many-locals
        cls, reader: BinReader, anim_def: AnimDef
    ) -> LightState:
        (
            name_raw,
            index,
            unk036,
            active_state,
            one044,
            directional,
            saturated,
            subdivide,
            static,
            at_index,
            at_tx,
            at_ty,
            at_tz,
            at_rx,
            at_ry,
            at_rz,
            range_min,
            range_max,
            color_r,
            color_g,
            color_b,
            ambient,
            diffuse,
        ) = reader.read(cls._STRUCT)

        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        expected_name = anim_def.get_light(index - 1, reader.prev + 32)
        assert_eq("index name", expected_name, name, reader.prev + 32)
        # unk036
        assert_in("active state", (0, 1), active_state, reader.prev + 40)
        assert_eq("field 044", 1, one044, reader.prev + 44)
        assert_in("directional", (0, 1), directional, reader.prev + 48)
        assert_in("saturated", (0, 1), saturated, reader.prev + 52)
        assert_in("subdivide", (0, 1), subdivide, reader.prev + 56)
        assert_in("static", (0, 1), static, reader.prev + 60)

        at_node = AtNodeLong.from_index(
            anim_def,
            at_index,
            at_tx,
            at_ty,
            at_tz,
            at_rx,
            at_ry,
            at_rz,
            reader.prev + 64,
        )

        assert_ge("range min", 0.0, range_min, reader.prev + 92)
        assert_ge("range max", range_min, range_max, reader.prev + 96)

        assert_between("red", 0.0, 1.0, color_r, reader.prev + 100)
        assert_between("green", 0.0, 1.0, color_g, reader.prev + 104)
        assert_between("blue", 0.0, 1.0, color_b, reader.prev + 108)

        assert_between("ambient", 0.0, 1.0, ambient, reader.prev + 112)
        assert_between("diffuse", 0.0, 1.0, diffuse, reader.prev + 116)

        return cls(
            name=name,
            active_state=active_state == 1,
            at_node=at_node,
            range=(range_min, range_max),
            color=(color_r, color_g, color_b),
            ambient=ambient,
            diffuse=diffuse,
            subdivide=subdivide == 1,
            saturated=saturated == 1,
            directional=directional == 1,
            static=static == 1,
            unk=unk036,
        )

    def __repr__(self) -> str:
        state_name = "ACTIVE" if self.active_state else "INACTIVE"
        return "\n".join(
            [
                f"{self._NAME}(",
                f"  NAME={self.name!r},",
                f"  ACTIVE_STATE={state_name},",
                f"  AT_NODE={self.at_node!r},",
                f"  RANGE={self.range},",
                f"  COLOR={self.color},",
                f"  AMBIENT={self.ambient}, DIFFUSE={self.diffuse},",
                f"  SUBDIVIDE={self.subdivide}, SATURATED={self.saturated},",
                f"  DIRECTIONAL={self.directional}, STATIC={self.static},",
                f"  UNK={self.unk},",
                ")",
            ]
        )


class LightAnimation(ScriptObject):
    _NAME: str = "LIGHT_ANIMATION"
    _NUMBER: int = 5
    _STRUCT: Struct = Struct("<32s i 4f 2f 6f 3f f")

    name: str
    unk: int
    range: Tuple[float, float] = (0.0, 0.0)
    color: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    run_time: float

    @classmethod
    def read(  # pylint: disable=too-many-locals
        cls, reader: BinReader, _anim_def: AnimDef
    ) -> LightAnimation:
        (
            name_raw,
            unk32,
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

        assert_in("field 32", (1, 2, 3, 4), unk32, reader.prev + 32)

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
            unk=unk32,
        )

    def __repr__(self) -> str:
        return "\n".join(
            [
                f"{self._NAME}(",
                f"  NAME={self.name!r},",
                f"  RANGE={self.range},",
                f"  COLOR={self.color},",
                f"  RUN_TIME={self.run_time},",
                f"  UNK={self.unk},",
                ")",
            ]
        )
