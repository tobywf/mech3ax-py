from __future__ import annotations

from struct import unpack
from typing import (
    Any,
    Callable,
    Dict,
    Literal,
    Mapping,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from pydantic import BaseModel, validator

from mech3ax.errors import assert_in

from ..utils import BinReader
from .models import AnimDef, ScriptObject

Discriminator = Union[Literal["bool"], Literal["int"], Literal["float"]]


class Bool(BaseModel):
    value: bool

    @classmethod
    def from_bytes(cls, value: bytes) -> Tuple[Discriminator, Bool]:
        (result,) = unpack("<I", value)
        return "bool", cls(value=cast(bool, result == 0))


class Int(BaseModel):
    value: int

    @classmethod
    def from_bytes(cls, value: bytes) -> Tuple[Discriminator, Int]:
        (result,) = unpack("<I", value)
        return "int", cls(value=cast(int, result))


class Float(BaseModel):
    value: float

    @classmethod
    def from_bytes(cls, value: bytes) -> Tuple[Discriminator, Float]:
        (result,) = unpack("<f", value)
        return "float", cls(value=cast(float, result))


RightHandSide = Union[Bool, Int, Float]
T = TypeVar("T", bound="Comparison")


class Comparison(ScriptObject):
    _NAME: str = ""
    _NUMBER: int = -1

    lhs: str
    discriminator: Discriminator
    rhs: RightHandSide

    @validator("rhs", pre=True)
    @classmethod
    def validate_rhs(cls, value: Any, values: Dict[str, str]) -> BaseModel:
        if isinstance(value, BaseModel):
            return value

        if not isinstance(value, dict):
            raise ValueError("value must be dict")

        discriminator = values["discriminator"]
        if discriminator == "bool":
            return Bool(**value)
        if discriminator == "int":
            return Int(**value)
        if discriminator == "float":
            return Float(**value)
        raise ValueError(f"unknown discriminator {discriminator!r}")

    @classmethod
    def read(cls: Type[T], reader: BinReader, anim_def: AnimDef) -> T:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self._NAME}({self.lhs!r} <= {self.rhs.value!r})"


IF_COND: Mapping[
    int, Tuple[str, Callable[[bytes], Tuple[Discriminator, RightHandSide]]]
] = {
    1: ("RANDOM_WEIGHT", Float.from_bytes),
    2: ("PLAYER_RANGE", Float.from_bytes),
    4: ("ANIMATION_LOD", Int.from_bytes),
    32: ("HW_RENDER", Bool.from_bytes),
    64: ("PLAYER_1ST_PERSON", Bool.from_bytes),
}


def get_comparison(
    condition: int, value: bytes, offset: int
) -> Tuple[str, Discriminator, RightHandSide]:
    assert_in("condition", IF_COND.keys(), condition, offset)
    lhs, function = IF_COND[condition]
    discriminator, rhs = function(value)
    return lhs, discriminator, rhs
