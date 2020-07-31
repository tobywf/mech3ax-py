from __future__ import annotations

from struct import Struct
from typing import Optional

from mech3ax.errors import assert_ascii, assert_eq, assert_in

from ..utils import BinReader, ascii_zterm_padded
from .models import AnimDef, AtNodeShort, ScriptObject

DUMMY_IMPORT = None


class Sound(ScriptObject):
    _NAME: str = "SOUND"
    _NUMBER: int = 1
    _STRUCT: Struct = Struct("<Hh 3f")

    name: str
    at_node: Optional[AtNodeShort] = None

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> Sound:
        index, at_index, at_tx, at_ty, at_tz = reader.read(cls._STRUCT)
        name = anim_def.get_sound(index - 1, reader.prev + 0)
        at_node = AtNodeShort.from_index(
            anim_def, at_index, at_tx, at_ty, at_tz, reader.prev + 2
        )
        return cls(name=name, at_node=at_node)

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.name!r}, AT_NODE={self.at_node!r})"


class SoundNode(ScriptObject):
    _NAME: str = "SOUND_NODE"
    _NUMBER: int = 2
    _STRUCT: Struct = Struct("<32s 3I i 3f")

    name: str
    active_state: bool
    at_node: Optional[AtNodeShort] = None
    unk: int

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> SoundNode:
        (
            name_raw,
            one32,
            unk,
            active_state,
            at_index,
            at_tx,
            at_ty,
            at_tz,
        ) = reader.read(cls._STRUCT)

        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        assert_eq("field 32", 1, one32, reader.prev + 32)
        assert_in("field 36", (0, 2), unk, reader.prev + 36)
        assert_in("active state", (0, 1), active_state, reader.prev + 40)

        at_node = AtNodeShort.from_index(
            anim_def, at_index, at_tx, at_ty, at_tz, reader.prev + 44
        )
        return cls(name=name, active_state=active_state == 1, at_node=at_node, unk=unk)

    def __repr__(self) -> str:
        state_name = "ACTIVE" if self.active_state else "INACTIVE"
        return f"{self._NAME}(NAME={self.name!r}, ACTIVE_STATE={state_name}, AT_NODE={self.at_node!r}, UNK={self.unk})"
