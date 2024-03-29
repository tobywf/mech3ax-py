import logging
from struct import Struct
from typing import BinaryIO, Dict, List, Tuple, cast

from pydantic import BaseModel

from ..errors import assert_eq, assert_gt
from .models import VEC3, VEC4, Vec3, Vec4
from .utils import UINT32, BinReader

MOTION = Struct("<I f 2I 2f")
assert MOTION.size == 24, MOTION.size

VERSION = 4

LOG = logging.getLogger(__name__)


class Motion(BaseModel):
    frames: int
    loop_time: float
    parts: Dict[str, List[Tuple[Vec3, Vec4]]]


def read_motion(data: bytes) -> Motion:
    reader = BinReader(data)
    LOG.debug("Reading motion data...")
    (version, loop_time, frame_count, part_count, minus_one, plus_one,) = reader.read(
        MOTION
    )

    assert_eq("version", VERSION, version, reader.prev + 0)
    assert_gt("loop time", 0.0, loop_time, reader.prev + 4)
    assert_eq("field 16", -1.0, minus_one, reader.prev + 16)
    assert_eq("field 20", 1.0, plus_one, reader.prev + 20)

    # for some reason, this is off-by-one
    frame_count += 1

    parts = {}
    for _ in range(part_count):
        part_name = reader.read_string()

        flag = reader.read_u32()
        # 8 = translation, 4 = rotation, 2 = scaling (never in motion.zbd)
        assert_eq("flag", 12, flag, reader.prev)

        translations = [cast(Vec3, reader.read(VEC3)) for _ in range(frame_count)]
        # scaling would be read here (never in motion.zbd)
        rotations = [cast(Vec4, reader.read(VEC4)) for _ in range(frame_count)]

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
            f.write(VEC3.pack(*translation))
        for _, rotation in values:
            f.write(VEC4.pack(*rotation))

    LOG.debug("Wrote motion data")
