from __future__ import annotations

from itertools import chain
from math import cos, sin, sqrt
from struct import Struct
from typing import List, Optional, Tuple, Type, cast

from mech3ax.errors import assert_between, assert_eq, assert_ge

from ..utils import BinReader
from .models import AnimDef, MotionFrame, Quaternion, ScriptObject, Vector

DUMMY_IMPORT = None

SI_SCRIPT_FRAME = Struct("<I 2f")
assert SI_SCRIPT_FRAME.size == 12, SI_SCRIPT_FRAME.size
SI_SCRIPT_DATA = Struct("<19f")
assert SI_SCRIPT_DATA.size == 76, SI_SCRIPT_DATA.size
Values = Tuple[
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
]


def parse_vec_data(values: Values, current_time: float) -> Vector:
    x = values[4] * current_time + values[0]
    y = values[5] * current_time + values[1]
    z = values[6] * current_time + values[2]
    return (x, y, z)

    # TODO: I don't know under which condition this calculation is used
    # x = ((values[10] * current_time + values[9]) * current_time + values[8]) * current_time + values[7]
    # y = ((values[14] * current_time + values[13]) * current_time + values[12]) * current_time + values[11]
    # z = ((values[18] * current_time + values[17]) * current_time + values[16]) * current_time + values[15]
    # return (x, y, z)


def euler_axis_to_quat(x: float, y: float, z: float) -> Quaternion:
    magnitude = sqrt(x * x + y * y + z * z)
    if magnitude == 0.0:
        return (1.0, 0.0, 0.0, 0.0)

    angle_sin = sin(magnitude)
    angle_cos = cos(magnitude)

    angle_sin /= magnitude
    return (angle_cos, x * angle_sin, y * angle_sin, z * angle_sin)


def quat_rotate(
    quat: Quaternion, w2: float, x2: float, y2: float, z2: float
) -> Quaternion:
    # pylint: disable=invalid-name
    w1, x1, y1, z1 = quat

    w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    x = y1 * z2 + w1 * x2 + x1 * w2 - z1 * y2
    y = z1 * x2 + w1 * y2 + y1 * w2 - x1 * z2
    z = x1 * y2 + w1 * z2 + z1 * w2 - y1 * x2

    return (w, x, y, z)


def parse_quat_data(values: Values, current_time: float) -> Quaternion:
    x, y, z = parse_vec_data((0.0, 0.0, 0.0) + values[3:], current_time)
    quat = euler_axis_to_quat(x, y, z)
    return quat_rotate(quat, values[0], values[1], values[2], values[3])


class ObjectMotionSIScript(ScriptObject):
    _NAME: str = "OBJECT_MOTION_SI_SCRIPT"
    _NUMBER: int = 12
    _STRUCT: Struct = Struct("<2i 2f 2i")

    index: int
    frames: List[MotionFrame]

    @classmethod
    def read(
        cls: Type[ObjectMotionSIScript], reader: BinReader, anim_def: AnimDef
    ) -> ObjectMotionSIScript:
        raise NotImplementedError

    @classmethod
    def validate_length(cls, reader: BinReader, actual_length: int) -> None:
        raise NotImplementedError

    @classmethod
    def validate_and_read(
        cls, reader: BinReader, _anim_def: AnimDef, actual_length: int
    ) -> ObjectMotionSIScript:
        abs_end = reader.offset + actual_length
        (index, count, zero08, zero12, zero16, zero20,) = reader.read(cls._STRUCT)

        assert_between("index", 0, 20, index, reader.prev + 0)  # 12
        assert_eq("field 08", 0.0, zero08, reader.prev + 8)  # 20
        assert_eq("field 12", 0.0, zero12, reader.prev + 12)  # 24
        assert_eq("field 16", 0, zero16, reader.prev + 16)  # 28
        assert_eq("field 20", 0, zero20, reader.prev + 20)  # 32

        frames = []
        for i in range(count):
            flag, start_time, end_time = reader.read(SI_SCRIPT_FRAME)
            assert_between(f"motion {i} flag", 1, 7, flag, reader.prev + 0)
            assert_ge(f"motion {i} start", 0.0, start_time, reader.prev + 4)
            if end_time != 0.0:
                assert_ge(f"motion {i} end", start_time, end_time, reader.prev + 8)

            if (flag & 1) == 0:
                translate: Optional[Vector] = None
            else:
                values = cast(Values, reader.read(SI_SCRIPT_DATA))
                translate = parse_vec_data(values, start_time)

            if (flag & 2) == 0:
                rotate: Optional[Quaternion] = None
            else:
                values = cast(Values, reader.read(SI_SCRIPT_DATA))
                rotate = parse_quat_data(values, start_time)

            if (flag & 4) == 0:
                scale: Optional[Vector] = None
            else:
                values = cast(Values, reader.read(SI_SCRIPT_DATA))
                scale = parse_vec_data(values, start_time)

            frame = MotionFrame(
                start=start_time,
                end=end_time,
                translate=translate,
                rotate=rotate,
                scale=scale,
            )
            frames.append(frame)

        assert_eq("motion script end", abs_end, reader.offset, reader.offset)
        return cls(index=index, frames=frames)

    def __repr__(self) -> str:
        return "\n".join(
            chain(
                [f"{self._NAME}(INDEX={self.index}, COUNT={len(self.frames)})"],
                (
                    (
                        f"- FRAME={i}, START={frame.start:.5f}, END={frame.end:.5f}, "
                        f"TRANSLATE={frame.translate}, ROTATE={frame.rotate}, SCALE={frame.scale}"
                    )
                    for i, frame in enumerate(self.frames)
                ),
            )
        )
