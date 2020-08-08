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
    at_node: AtNodeShort

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> Sound:
        sound_index, node_index, tx, ty, tz = reader.read(cls._STRUCT)
        name = anim_def.get_sound(sound_index - 1, reader.prev + 0)
        node = anim_def.get_node(node_index - 1, reader.prev + 2)
        at_node = AtNodeShort(node=node, tx=tx, ty=ty, tz=tz)
        return cls(name=name, at_node=at_node)


class SoundNode(ScriptObject):
    _NAME: str = "SOUND_NODE"
    _NUMBER: int = 2
    _STRUCT: Struct = Struct("<32s 3I i 3f")

    name: str
    active_state: bool
    at_node: Optional[AtNodeShort] = None

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> SoundNode:
        (
            name_raw,
            one32,
            inherit_trans,
            active_state,
            node_index,
            tx,
            ty,
            tz,
        ) = reader.read(cls._STRUCT)

        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        # this would cause the sound node to be dynamically allocated
        assert_eq("field 32", 1, one32, reader.prev + 32)  # 44
        assert_in("active state", (0, 1), active_state, reader.prev + 40)  # 52

        # this is actually a bit field.
        # if it's 1, then the translation would be applied directly to the node
        # if it's 2 and AT_NODE is given, then the translation is applied relative
        # to the node
        assert_in("field 36", (0, 2), inherit_trans, reader.prev + 36)  # 48

        if inherit_trans == 0:
            at_node = None
            assert_eq("at node", 0, node_index, reader.prev + 44)
            assert_eq("at tx", 0.0, tx, reader.prev + 48)
            assert_eq("at ty", 0.0, ty, reader.prev + 52)
            assert_eq("at tz", 0.0, tz, reader.prev + 56)
        else:
            node = anim_def.get_node(node_index - 1, reader.prev + 44)
            at_node = AtNodeShort(node=node, tx=tx, ty=ty, tz=tz)

        return cls(name=name, active_state=active_state == 1, at_node=at_node)
