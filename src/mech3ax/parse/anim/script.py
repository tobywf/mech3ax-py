from __future__ import annotations

import logging
from io import StringIO
from struct import Struct
from typing import List

from mech3ax.errors import assert_eq, assert_in

# these imports are needed, because otherwise the classes wouldn't get picked up
from ..utils import BinReader
from .animation import DUMMY_IMPORT as _ANIMATION_DI  # pylint: disable=unused-import
from .control_flow import DUMMY_IMPORT as _CONTROL_FLOW_DI
from .detonate_weapon import DUMMY_IMPORT as _DETONATE_WEAPON_DI
from .fog import DUMMY_IMPORT as _FOG_DI
from .frame_buffer_effects import DUMMY_IMPORT as _FBX_DI
from .light import DUMMY_IMPORT as _LIGHT_DI
from .models import OBJECT_REGISTRY_NUM, AnimDef, ScriptItem, StartOffset
from .object_motion import DUMMY_IMPORT as _OBJECT_MOTION_DI
from .object_motion_si_script import DUMMY_IMPORT as _OBJECT_MOTION_SI_DI
from .object_state import DUMMY_IMPORT as _OBJECT_STATE_DI
from .puffer import DUMMY_IMPORT as _PUFFER_DI
from .sequence import DUMMY_IMPORT as _SEQUENCE_DI
from .sound import DUMMY_IMPORT as _SOUND_DI

LOG = logging.getLogger(__name__)

SCRIPT_HEADER = Struct("<2B H I f")
assert SCRIPT_HEADER.size == 12, SCRIPT_HEADER.size


def _parse_script(
    reader: BinReader, anim_def: AnimDef, rel_end: int, f: StringIO
) -> List[ScriptItem]:
    LOG.debug("Reading script with length %d at %d", rel_end, reader.offset)

    abs_end = rel_end + reader.offset
    script = []

    while reader.offset < abs_end:
        stype, start_offset, pad, size, start_time = reader.read(SCRIPT_HEADER)
        assert_in("type", OBJECT_REGISTRY_NUM.keys(), stype, reader.prev + 0)
        assert_in("start offset", (1, 2, 3), start_offset, reader.prev + 1)
        assert_eq("field 02", 0, pad, reader.prev + 2)

        start_offset = StartOffset(start_offset)
        if start_time == 0.0:
            assert_eq(
                "start offset", StartOffset.Animation, start_offset, reader.prev + 1
            )
            start_offset = StartOffset.Unset

        actual_length = size - SCRIPT_HEADER.size
        base_model = OBJECT_REGISTRY_NUM[stype]

        obj = base_model.validate_and_read(reader, anim_def, actual_length)
        if start_offset != StartOffset.Unset:
            print(repr(obj), start_offset, start_time, file=f)
        else:
            print(repr(obj), file=f)

        item = ScriptItem(
            name=base_model._NAME,  # pylint: disable=protected-access
            item=obj,
            start_offset=start_offset,
            start_time=start_time,
        )
        script.append(item)

    assert_eq("script end", abs_end, reader.offset, reader.offset)
    LOG.debug("Read script")
    return script
