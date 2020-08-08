from __future__ import annotations

from struct import Struct

from mech3ax.errors import assert_ascii, assert_eq

from ..utils import BinReader, ascii_zterm_padded
from .models import AnimDef, ScriptObject

DUMMY_IMPORT = None


class CallSequence(ScriptObject):
    _NAME: str = "CALL_SEQUENCE"
    _NUMBER: int = 22
    _STRUCT: Struct = Struct("<32s i")

    name: str

    @classmethod
    def read(cls, reader: BinReader, _anim_def: AnimDef) -> CallSequence:
        name_raw, sentinel = reader.read(cls._STRUCT)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        assert_eq("sentinel", -1, sentinel, reader.prev + 32)
        return cls(name=name)


class StopSequence(ScriptObject):
    _NAME: str = "STOP_SEQUENCE"
    _NUMBER: int = 23
    _STRUCT: Struct = Struct("<32s i")

    name: str

    @classmethod
    def read(cls, reader: BinReader, _anim_def: AnimDef) -> StopSequence:
        name_raw, sentinel = reader.read(cls._STRUCT)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        assert_eq("sentinel", -1, sentinel, reader.prev + 32)
        return cls(name=name)
