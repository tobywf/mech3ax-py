from __future__ import annotations

from base64 import b64decode, b64encode
from enum import Enum
from typing import Any, Callable, Dict, Generator, Optional, Union

CallableGenerator = Generator[Callable[..., Any], None, None]


class Base64(bytes):
    @classmethod
    def __get_validators__(cls) -> CallableGenerator:
        yield cls.validate

    @classmethod
    def validate(cls, value: Union[str, bytes]) -> bytes:
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            return b64decode(value)
        raise TypeError("bytes or string required")  # pragma: no cover

    @staticmethod
    def to_str(value: bytes) -> str:
        return b64encode(value).decode("ascii")

    @classmethod
    def from_optional(cls, value: Optional[bytes]) -> Optional[Base64]:
        if value is None:
            return None

        return Base64(value)


class NodeType(Enum):
    Empty = 0
    Camera = 1
    World = 2
    Window = 3
    Display = 4
    Object3D = 5
    LOD = 6
    Light = 9
    # Not seen in GameZ files
    # Sequence = 7
    # Animate = 8
    # Sound = 10
    # Switch = 11

    @classmethod
    def __get_validators__(cls) -> CallableGenerator:
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, str]) -> None:
        field_schema.update(type="str")  # pragma: no cover

    @classmethod
    def validate(cls, value: Union[str, NodeType]) -> NodeType:
        if isinstance(value, NodeType):
            return value
        if isinstance(value, str):
            try:
                return NodeType.__members__[value]
            except KeyError as e:  # pragma: no cover
                raise ValueError(f"{value!r} is not a valid NodeType") from e
        raise TypeError("string or NodeType required")  # pragma: no cover

    @staticmethod
    def to_str(value: NodeType) -> str:
        return value.name
