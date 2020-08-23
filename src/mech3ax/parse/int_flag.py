from __future__ import annotations

from enum import IntFlag as BaseIntFlag
from typing import Sequence, Type, TypeVar

_T = TypeVar("_T", bound="IntFlag")


def _no_zero(flag_cls: Type[_T]) -> bool:
    members: Sequence[_T] = list(flag_cls)
    zero_value = next((flag.value for flag in members if flag.value == 0), None)
    return zero_value is None


class IntFlag(BaseIntFlag):
    def __call__(self, value: int) -> bool:
        return value & self == self

    @classmethod
    def check(cls: Type[_T], value: int) -> _T:
        if _no_zero(cls) and value == 0:  # pragma: no cover
            raise ValueError("Zero is invalid")
        mask = 0
        members: Sequence[_T] = list(cls)
        for flag in members:
            if flag(value):
                mask |= flag.value
        if value != mask:  # pragma: no cover
            unknown = value & ~mask
            raise ValueError(
                f"Undefined flag: 0x{value:08X}, known: 0x{mask:08X}, unknown: 0x{unknown:08X}"
            )
        return cls(value)
