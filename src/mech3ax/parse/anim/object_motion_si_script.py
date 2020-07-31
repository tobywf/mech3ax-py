from __future__ import annotations

from struct import Struct
from typing import Type

from mech3ax.serde import Base64

from ..utils import BinReader
from .models import AnimDef, ScriptObject

DUMMY_IMPORT = None


class ObjectMotionSIScript(ScriptObject):
    _NAME: str = "OBJECT_MOTION_SI_SCRIPT"
    _NUMBER: int = 12
    _STRUCT: Struct = Struct("")

    content: Base64

    @classmethod
    def read(
        cls: Type[ObjectMotionSIScript], reader: BinReader, anim_def: AnimDef
    ) -> ObjectMotionSIScript:
        raise NotImplementedError

    @classmethod
    def validate_and_read(
        cls, reader: BinReader, _anim_def: AnimDef, actual_length: int
    ) -> ObjectMotionSIScript:
        return cls(content=Base64(reader.read_bytes(actual_length)))
