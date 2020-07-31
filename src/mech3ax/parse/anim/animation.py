from __future__ import annotations

from struct import Struct
from typing import Optional

from mech3ax.errors import assert_ascii, assert_eq

from ..utils import BinReader, ascii_zterm_padded
from .models import AnimDef, AtNodeLong, ScriptObject

DUMMY_IMPORT = None


class CallAnimation(ScriptObject):
    _NAME: str = "CALL_ANIMATION"
    _NUMBER: int = 24
    _STRUCT: Struct = Struct("<32s H I H i 3f 3f")

    name: str

    unk1: int
    unk2: int
    unk3: int

    at_node: Optional[AtNodeLong] = None

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> CallAnimation:
        (
            name_raw,
            unk1,
            unk2,
            unk3,
            at_index,
            at_tx,
            at_ty,
            at_tz,
            at_rx,
            at_ry,
            at_rz,
        ) = reader.read(cls._STRUCT)

        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        # assert_eq("field 32", 0, unk1, reader.prev + 32)
        # assert_eq("field 34", 0, unk2, reader.prev + 32)
        # assert_eq("field 38", 0xFFFF, unk3, reader.prev + 38)

        at_node = AtNodeLong.from_index(
            anim_def,
            at_index,
            at_tx,
            at_ty,
            at_tz,
            at_rx,
            at_ry,
            at_rz,
            reader.prev + 40,
        )
        return cls(name=name, at_node=at_node, unk1=unk1, unk2=unk2, unk3=unk3)

    def __repr__(self) -> str:
        return (
            f"{self._NAME}(NAME={self.name!r}, AT_NODE={self.at_node!r})\n"
            f"{self.unk1}, {self.unk2}, {self.unk3}"
        )


class StopAnimation(ScriptObject):
    _NAME: str = "STOP_ANIMATION"
    _NUMBER: int = 25
    _STRUCT: Struct = Struct("<32s i")

    name: str

    @classmethod
    def read(cls, reader: BinReader, _anim_def: AnimDef) -> StopAnimation:
        name_raw, sentinel = reader.read(cls._STRUCT)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        assert_eq("sentinel", 0, sentinel, reader.prev + 32)
        return cls(name=name)

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.name!r})"


class ResetAnimation(ScriptObject):
    _NAME: str = "RESET_ANIMATION"
    _NUMBER: int = 26
    _STRUCT: Struct = Struct("<32s i")

    name: str

    @classmethod
    def read(cls, reader: BinReader, _anim_def: AnimDef) -> ResetAnimation:
        name_raw, sentinel = reader.read(cls._STRUCT)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        assert_eq("sentinel", 0, sentinel, reader.prev + 0)
        return cls(name=name)

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.name!r})"


class InvalidateAnimation(ScriptObject):
    _NAME: str = "INVALIDATE_ANIMATION"
    _NUMBER: int = 27
    _STRUCT: Struct = Struct("<32s i")

    name: str

    @classmethod
    def read(cls, reader: BinReader, _anim_def: AnimDef) -> InvalidateAnimation:
        name_raw, sentinel = reader.read(cls._STRUCT)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        assert_eq("sentinel", 0, sentinel, reader.prev + 0)
        return cls(name=name)

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.name!r})"
