from __future__ import annotations

from struct import Struct
from typing import Literal, Tuple

from mech3ax.errors import assert_between, assert_eq, assert_ge

from ..utils import BinReader
from .models import AnimDef, ScriptObject

DUMMY_IMPORT = None
DEFAULT_FOG_NAME = (
    b"default_fog_name\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)


class FogState(ScriptObject):
    _NAME: str = "FOG_STATE"
    _NUMBER: int = 28
    _STRUCT: Struct = Struct("<32s 2I 7f")

    color: Tuple[float, float, float]
    altitude: Tuple[float, float]
    range: Tuple[float, float]
    fog_type: Literal["LINEAR"]

    @classmethod
    def read(cls, reader: BinReader, _anim_def: AnimDef) -> FogState:
        (
            name_raw,
            unknown,
            fog_type,
            color_r,
            color_g,
            color_b,
            altitude_min,
            altitude_max,
            range_min,
            range_max,
        ) = reader.read(cls._STRUCT)
        assert_eq("name", DEFAULT_FOG_NAME, name_raw, reader.prev + 0)
        assert_eq("field 32", 14, unknown, reader.prev + 32)
        # LINEAR = 1
        assert_eq("fog type", 1, fog_type, reader.prev + 36)

        assert_between("red", 0.0, 1.0, color_r, reader.prev + 40)
        assert_between("green", 0.0, 1.0, color_g, reader.prev + 44)
        assert_between("blue", 0.0, 1.0, color_b, reader.prev + 48)

        # altitude is always ordered this way even negative (unlike range)
        assert_ge("altitude max", altitude_min, altitude_max, reader.prev + 56)

        assert_ge("range min", 0.0, range_min, reader.prev + 60)
        assert_ge("range max", range_min, range_max, reader.prev + 64)

        return cls(
            color=(color_r, color_g, color_b),
            altitude=(altitude_min, altitude_max),
            range=(range_min, range_max),
            fog_type="LINEAR",
        )

    def __repr__(self) -> str:
        return f"{self._NAME}(TYPE={self.fog_type}, COLOR={self.color}, ALTITUDE={self.altitude}, RANGE={self.range})"
