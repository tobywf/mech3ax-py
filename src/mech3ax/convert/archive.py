from __future__ import annotations

from base64 import b64decode, b64encode
from pathlib import Path
from typing import Any, Callable, Generator, List, Optional, Set, Union, cast

from pydantic import BaseModel

from ..parse.archive import ArchiveEntry, Filetime

MANIFEST = "manifest.json"
CallableGenerator = Generator[Callable[..., Any], None, None]


class Base64(bytes):
    @classmethod
    def __get_validators__(cls) -> CallableGenerator:
        yield cls.validate

    @classmethod
    def validate(cls, value: Union[str, bytes, None]) -> Optional[bytes]:
        if value is None:
            return None
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            return b64decode(value)
        raise TypeError("bytes or string required")

    @staticmethod
    def to_str(value: bytes) -> str:
        return b64encode(value).decode("ascii")


class ArchiveInfo(BaseModel):
    name: str
    rename: str
    start: int
    flag: int = 0
    comment_bytes: Optional[Base64] = None
    comment_ascii: Optional[str] = None
    write_time: Filetime

    @classmethod
    def from_entry(cls, entry: ArchiveEntry, rename: str) -> ArchiveInfo:
        comment_bytes: Optional[bytes] = None
        comment_ascii: Optional[str] = None
        try:
            # don't use ascii_zterm, this can contain garbage after zeros
            comment_ascii = entry.comment.rstrip(b"\0").decode("ascii")
        except UnicodeDecodeError:
            comment_bytes = entry.comment
        return cls(
            name=entry.name,
            rename=rename,
            start=entry.start,
            flag=entry.flag,
            comment_bytes=comment_bytes,
            comment_ascii=comment_ascii,
            write_time=entry.write_time,
        )

    def to_entry(self, data: bytes) -> ArchiveEntry:
        # this can be an empty string (mechlib)
        if self.comment_ascii is not None:
            comment = self.comment_ascii.encode("ascii")
        else:
            comment = cast(bytes, self.comment_bytes)
        return ArchiveEntry(
            name=self.name,
            start=self.start,
            data=data,
            flag=self.flag,
            comment=comment,
            write_time=self.write_time,
        )


class ArchiveManifest(BaseModel):
    class Config:
        json_encoders = {bytes: Base64.to_str}

    __root__: List[ArchiveInfo]


class Renamer:
    """Rename duplicates"""

    def __init__(self) -> None:
        self._names: Set[str] = set()

    def __call__(self, name: str) -> str:
        basename = Path(name)
        i = 1
        while name in self._names:
            name = f"{basename.stem}_{i}{basename.suffix}"
            i += 1

        self._names.add(name)
        return name
