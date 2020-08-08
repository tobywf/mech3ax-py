from __future__ import annotations

from struct import Struct

from mech3ax.errors import assert_ascii

from ..utils import BinReader, ascii_zterm_padded
from .models import AnimDef, AtNodeShort, ScriptObject

DUMMY_IMPORT = None


class DetonateWeapon(ScriptObject):
    _NAME: str = "DETONATE_WEAPON"
    _NUMBER: int = 41
    _STRUCT: Struct = Struct("<10s h 3f")

    name: str
    at_node: AtNodeShort

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> DetonateWeapon:
        name_raw, node_index, tx, ty, tz = reader.read(cls._STRUCT)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        node = anim_def.get_node(node_index - 1, reader.prev + 10)
        at_node = AtNodeShort(node=node, tx=tx, ty=ty, tz=tz)
        return cls(name=name, at_node=at_node)

    def __repr__(self) -> str:
        return f"{self._NAME}(WEAPON={self.name!r}, AT_NODE={self.at_node!r})"
