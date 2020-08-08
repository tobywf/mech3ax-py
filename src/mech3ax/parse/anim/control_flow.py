from __future__ import annotations

from struct import Struct

from mech3ax.errors import assert_eq

from ..utils import BinReader
from .comparison import Comparison, get_comparison
from .models import AnimDef, ScriptObject

DUMMY_IMPORT = None


class Loop(ScriptObject):
    _NAME: str = "LOOP"
    _NUMBER: int = 30
    _STRUCT: Struct = Struct("<I hH")

    loop_count: int = -1

    @classmethod
    def read(cls, reader: BinReader, _anim_def: AnimDef) -> Loop:
        start, loop_count, pad = reader.read(cls._STRUCT)
        assert_eq("field 0", 1, start, reader.prev + 0)
        assert_eq("field 6", 0, pad, reader.prev + 6)
        return cls(loop_count=loop_count)


class If(Comparison):
    _NAME: str = "IF"
    _NUMBER: int = 31
    _STRUCT: Struct = Struct("<2I 4s")

    @classmethod
    def read(cls, reader: BinReader, _anim_def: AnimDef) -> If:
        condition, zero, value = reader.read(cls._STRUCT)
        assert_eq("field 4", 0, zero, reader.prev + 4)
        lhs, discriminator, rhs = get_comparison(condition, value, reader.prev + 0)
        return cls(lhs=lhs, discriminator=discriminator, rhs=rhs)


class Elif(Comparison):
    _NAME: str = "ELSEIF"
    _NUMBER: int = 33
    _STRUCT: Struct = Struct("<2I 4s")

    @classmethod
    def read(cls, reader: BinReader, _anim_def: AnimDef) -> Elif:
        condition, zero, value = reader.read(cls._STRUCT)
        assert_eq("field 4", 0, zero, reader.prev + 4)
        lhs, discriminator, rhs = get_comparison(condition, value, reader.prev + 0)
        return cls(lhs=lhs, discriminator=discriminator, rhs=rhs)


class Else(ScriptObject):
    _NAME: str = "ELSE"
    _NUMBER: int = 32
    _STRUCT: Struct = Struct("")

    @classmethod
    def read(cls, _reader: BinReader, _anim_def: AnimDef) -> Else:
        return cls()


class Endif(ScriptObject):
    _NAME: str = "ENDIF"
    _NUMBER: int = 34
    _STRUCT: Struct = Struct("")

    @classmethod
    def read(cls, _reader: BinReader, _anim_def: AnimDef) -> Endif:
        return cls()


class Callback(ScriptObject):
    _NAME: str = "CALLBACK"
    _NUMBER: int = 35
    _STRUCT: Struct = Struct("I")

    value: int

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> Callback:
        assert_eq("has callback", True, anim_def.has_callback, reader.offset)
        anim_def.callback_count += 1
        (value,) = reader.read(cls._STRUCT)
        return cls(value=value)
