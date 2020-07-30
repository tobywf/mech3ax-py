from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Set, cast

from pydantic import BaseModel

from ..parse.archive import ArchiveEntry, Filetime
from ..serde import Base64

MANIFEST = "manifest.json"


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
            comment_bytes=Base64.from_optional(comment_bytes),
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
