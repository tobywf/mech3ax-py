import logging
from struct import Struct
from typing import BinaryIO, Iterable, Optional, Sequence

from pydantic import BaseModel

from ..errors import Mech3MaterialError, assert_eq, assert_in
from .utils import UINT32, BinReader

LOG = logging.getLogger(__name__)

VERSION = 27
VERSION_DATA = UINT32.pack(VERSION)
FORMAT = 1
FORMAT_DATA = UINT32.pack(FORMAT)

MATERIAL_INFO = Struct("<2BH 3f I 3f 2I")
assert MATERIAL_INFO.size == 40, MATERIAL_INFO.size


def read_version(data: bytes) -> None:
    assert_eq("version end", 4, len(data), 0)
    (version,) = UINT32.unpack(data)
    assert_eq("version", VERSION, version, 0)


def read_format(data: bytes) -> None:
    assert_eq("format end", 4, len(data), 0)
    (fmt,) = UINT32.unpack(data)
    assert_eq("format", FORMAT, fmt, 0)


class Material(BaseModel):
    name: Optional[str]
    flag: int = 17
    unk: int = 0xFF
    rgb: int = 0x7FFF
    red: float = 255.0
    green: float = 255.0
    blue: float = 255.0
    pointer: int = 1


def read_materials(data: bytes) -> Iterable[Material]:
    reader = BinReader(data)
    yield from _read_materials(reader)


def _read_materials(reader: BinReader) -> Iterable[Material]:
    LOG.debug("Reading materials data...")
    count = reader.read_u32()

    for i in range(count):
        LOG.debug("Reading material %d at %d", i, reader.offset)
        (
            unk1,
            flag,
            rgb,
            red,
            green,
            blue,
            pointer,
            unk2,
            unk3,
            unk4,
            unk5,
            cycle,
        ) = reader.read(MATERIAL_INFO)

        assert_in("field 1", (0x00, 0xFF), unk1, reader.prev + 0)
        assert_eq("field 8", 0.0, unk2, reader.prev + 20)
        assert_eq("field 9", 0.5, unk3, reader.prev + 24)
        assert_eq("field 10", 0.5, unk4, reader.prev + 28)
        assert_eq("field 11", 0, unk5, reader.prev + 32)
        assert_eq("field 12", 0, cycle, reader.prev + 36)

        textured = (flag & 1) == 1

        if textured:
            assert_eq("pointer non-zero", True, pointer != 0, reader.prev + 16)
            # this seems to be RGB555, not RGB565?
            assert_eq("rgb", 0x7FFF, rgb, reader.prev + 2)
            assert_eq("red", 255.0, red, reader.prev + 4)
            assert_eq("green", 255.0, green, reader.prev + 8)
            assert_eq("blue", 255.0, blue, reader.prev + 12)
        else:
            assert_eq("pointer", 0, pointer, reader.prev + 16)
            assert_eq("rgb", 0, rgb, reader.prev + 2)

        name: Optional[str] = None
        if textured:
            name = reader.read_string()

        yield Material(
            name=name,
            flag=flag,
            unk=unk1,
            rgb=rgb,
            red=red,
            green=green,
            blue=blue,
            pointer=pointer,
        )

    # make sure all the data is processed
    assert_eq("materials end", len(reader), reader.offset, reader.offset)
    LOG.debug("Read materials data")


def write_materials(f: BinaryIO, materials: Sequence[Material]) -> None:
    LOG.debug("Writing materials data...")
    count = len(materials)
    f.write(UINT32.pack(count))
    for i, material in enumerate(materials):
        LOG.debug("Writing material %d at %d", i, f.tell())
        textured = (material.flag & 1) == 1

        if textured:
            assert_eq(
                "pointer non-zero", True, material.pointer != 0, i, Mech3MaterialError
            )
            assert_eq(
                "name non-empty", True, bool(material.name), i, Mech3MaterialError
            )
        else:
            assert_eq("pointer", 0, material.pointer, i)

        packed = MATERIAL_INFO.pack(
            material.unk,
            material.flag,
            material.rgb,
            material.red,
            material.green,
            material.blue,
            material.pointer,
            0.0,
            0.5,
            0.5,
            0,
            0,
        )
        f.write(packed)
        if material.name:
            length = len(material.name)
            f.write(UINT32.pack(length))
            f.write(material.name.encode("ascii"))

    LOG.debug("Wrote materials data")
