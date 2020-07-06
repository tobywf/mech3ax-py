import logging
from struct import Struct
from typing import BinaryIO, Dict, List, Tuple

from pydantic import BaseModel

from ..errors import Mech3ParseError, assert_eq
from .utils import UINT32, BinReader

MOTION = Struct("<I f 2I 2f")
assert MOTION.size == 24, MOTION.size

VECTOR = Struct("<3f")
assert VECTOR.size == 12, VECTOR.size
Vector = Tuple[float, float, float]

QUATERNION = Struct("<4f")
assert QUATERNION.size == 16, QUATERNION.size
Quaternion = Tuple[float, float, float, float]

VERSION = 4

LOG = logging.getLogger(__name__)


class Motion(BaseModel):
    frames: int
    loop_time: float
    parts: Dict[str, List[Tuple[Vector, Quaternion]]]


def read_motion(data: bytes) -> Motion:
    reader = BinReader(data)
    return _read_motion(reader)


def _read_motion(reader: BinReader) -> Motion:
    LOG.debug("Reading motion data...")
    (version, loop_time, frame_count, part_count, minus_one, plus_one,) = reader.read(
        MOTION
    )

    assert_eq("version", VERSION, version, reader.prev + 0)
    assert_eq("field 5", -1.0, minus_one, reader.prev + 16)
    assert_eq("field 6", 1.0, plus_one, reader.prev + 20)

    if loop_time <= 0.0:
        raise Mech3ParseError(
            f"Expected loop time to be greater than 0.0, but was {loop_time} (at {reader.prev + 4})"
        )

    # for some reason, this is off-by-one
    frame_count += 1

    parts = {}
    for _ in range(part_count):
        part_name = reader.read_string()

        flag = reader.read_u32()
        # 8 = translation, 4 = rotation, 2 = scaling (never in motion.zbd)
        assert_eq("flag", 12, flag, reader.prev)

        translations = [reader.read(VECTOR) for _ in range(frame_count)]
        # scaling would be read here (never in motion.zbd)
        rotations = [reader.read(QUATERNION) for _ in range(frame_count)]

        # interleave translation and rotation for easy frame access
        parts[part_name] = list(zip(translations, rotations))

    assert_eq("motion end", len(reader), reader.offset, reader.offset)
    LOG.debug("Read motion data")
    return Motion(frames=frame_count, loop_time=loop_time, parts=parts)


def write_motion(f: BinaryIO, motion: Motion) -> None:
    LOG.debug("Writing motion data...")
    header = MOTION.pack(
        VERSION, motion.loop_time, motion.frames - 1, len(motion.parts), -1.0, 1.0,
    )
    f.write(header)

    for name, values in motion.parts.items():
        length = len(name)
        f.write(UINT32.pack(length))
        f.write(name.encode("ascii"))
        f.write(UINT32.pack(12))

        for translation, _ in values:
            f.write(VECTOR.pack(*translation))
        for _, rotation in values:
            f.write(QUATERNION.pack(*rotation))

    LOG.debug("Wrote motion data")
