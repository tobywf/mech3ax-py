from __future__ import annotations

from struct import Struct
from typing import Tuple

from mech3ax.errors import assert_between, assert_gt

from ..utils import BinReader
from .models import AnimDef, ScriptObject

DUMMY_IMPORT = None


class FrameBufferEffectColorFromTo(ScriptObject):
    _NAME: str = "FBFX_COLOR_FROM_TO"
    _NUMBER: int = 36
    _STRUCT: Struct = Struct("<13f")

    from_color: Tuple[float, float, float, float]
    to_color: Tuple[float, float, float, float]
    delta: Tuple[float, float, float, float]
    run_time: float

    @classmethod
    def read(
        cls, reader: BinReader, _anim_def: AnimDef
    ) -> FrameBufferEffectColorFromTo:
        (
            from_r,
            to_r,
            delta_r,
            from_g,
            to_g,
            delta_g,
            from_b,
            to_b,
            delta_b,
            from_a,
            to_a,
            delta_a,
            run_time,
        ) = reader.read(cls._STRUCT)

        assert_between("from red", 0.0, 1.0, from_r, reader.prev + 0)
        assert_between("to red", 0.0, 1.0, to_r, reader.prev + 4)
        assert_between("from green", 0.0, 1.0, from_g, reader.prev + 12)
        assert_between("to green", 0.0, 1.0, to_g, reader.prev + 16)
        assert_between("from blue", 0.0, 1.0, from_b, reader.prev + 24)
        assert_between("to blue", 0.0, 1.0, to_b, reader.prev + 28)
        assert_between("from alpha", 0.0, 1.0, from_a, reader.prev + 32)
        assert_between("to alpha", 0.0, 1.0, to_a, reader.prev + 36)

        assert_gt("run time", 0.0, run_time, reader.prev + 48)

        return cls(
            from_color=(from_r, from_g, from_b, from_a),
            to_color=(to_r, to_g, to_b, to_a),
            delta=(delta_r, delta_g, delta_b, delta_a),
            run_time=run_time,
        )

    def __repr__(self) -> str:
        return f"{self._NAME}(FROM={self.from_color}, TO={self.to_color}, RUN_TIME={self.run_time})"
