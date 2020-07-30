from __future__ import annotations

from base64 import b64decode, b64encode
from typing import Any, Callable, Generator, Optional, Union

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
