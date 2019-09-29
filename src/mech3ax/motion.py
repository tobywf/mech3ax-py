from collections import defaultdict
from struct import Struct, unpack_from

from .archive import extract_archive
from .utils import json_dump, json_load

MOTION_HEADER = Struct("<If2I2f")


def parse_motion(motion):  # pylint: disable=too-many-locals
    four, unk, frame_count, part_count, minus_one, plus_one = MOTION_HEADER.unpack_from(
        motion, 0
    )
    assert four == 4
    assert minus_one == -1.0
    assert plus_one == 1.0
    assert unk > 0.0

    offset = MOTION_HEADER.size
    frame_count += 1

    parts = {"frame_count": frame_count}
    for _ in range(part_count):
        name_size, = unpack_from("<I", motion, offset)
        offset += 4
        part_name = motion[offset : offset + name_size].decode("ascii")
        offset += name_size
        twelve, = unpack_from("<I", motion, offset)
        assert twelve == 12
        offset += 4
        # location
        location_count = frame_count * 3
        location_data = unpack_from(f"<{location_count}f", motion, offset)
        location_values = [
            location_data[i : i + 3] for i in range(0, location_count, 3)
        ]
        offset += location_count * 4
        # rotation (quaternion)
        rotation_count = frame_count * 4
        rotation_data = unpack_from(f"<{rotation_count}f", motion, offset)
        rotation_values = [
            rotation_data[i : i + 4] for i in range(0, rotation_count, 4)
        ]
        offset += rotation_count * 4
        # interleave location and rotation for easy frame access
        parts[part_name] = list(zip(location_values, rotation_values))
    return parts


def extract_motions(data):
    for name, motion in extract_archive(data):
        yield name, parse_motion(motion)


def add_motions_to_models(motion_path, mechlib_path):
    with motion_path.open("rb") as f:
        data = f.read()

    mech_motion = defaultdict(dict)
    other_motion = {}

    for name, motion_values in extract_motions(data):
        if "_" in name:
            mech_name, _, motion_name = name.partition("_")
            mech_motion[mech_name][motion_name] = motion_values
        else:
            other_motion[name] = motion_values

    for mech_name, motions in mech_motion.items():
        mech_path = mechlib_path / f"mech_{mech_name}.json"
        model = json_load(mech_path)
        model["animations"] = motions
        json_dump(mech_path, model)

    motion_path = mechlib_path / "motions.json"
    json_dump(motion_path, other_motion)
