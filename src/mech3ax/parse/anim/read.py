import logging
from struct import Struct
from typing import List, Tuple

from pydantic import BaseModel

from mech3ax.errors import assert_ascii, assert_eq, assert_gt, assert_ne
from mech3ax.serde import Base64

from ..utils import BinReader, ascii_zterm_partition
from .anim_def import read_anim_def, read_anim_def_zero
from .models import AnimDef, AnimDefPointers

SIGNATURE = 0x08170616
VERSION = 39
GRAVITY = -9.800000190734863

LOG = logging.getLogger(__name__)

ANIM_FILE_HEADER = Struct("<3I")
assert ANIM_FILE_HEADER.size == 12, ANIM_FILE_HEADER.size

ANIM_NAME = Struct("<80s I")
assert ANIM_NAME.size == 84, ANIM_NAME.size

ANIM_INFO = Struct("<2I 2H 4I f 9I")
assert ANIM_INFO.size == 68, ANIM_INFO.size


class AnimName(BaseModel):
    name: str
    pad: Base64
    unk: int


class AnimMetadata(BaseModel):
    class Config:
        json_encoders = {bytes: Base64.to_str}

    anim_ptr: int
    world_ptr: int
    anim_names: List[AnimName]
    anim_def_ptrs: List[AnimDefPointers]


def _read_anim_header(reader: BinReader) -> List[AnimName]:
    (signature, version, count) = reader.read(ANIM_FILE_HEADER)
    LOG.debug(
        "Anim signature 0x%08x, version %d", signature, version,
    )
    assert_eq("signature", SIGNATURE, signature, reader.prev + 0)
    assert_eq("version", VERSION, version, reader.prev + 4)

    LOG.debug("Reading %d anim names at %d", count, reader.offset)
    names = []
    for _ in range(count):
        name_raw, unk = reader.read(ANIM_NAME)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name, pad = ascii_zterm_partition(name_raw)
        names.append(AnimName(name=name, pad=Base64(pad), unk=unk))
    return names


def _read_anim_info(reader: BinReader) -> Tuple[int, int, int]:
    LOG.debug("Reading anim info at %d", reader.offset)
    (
        zero00,
        ptr04,
        zero08,
        count,
        anim_ptr,
        loc_count,
        loc_ptr,
        world_ptr,
        gravity,
        zero32,
        zero36,
        zero40,
        zero44,
        zero48,
        zero52,
        zero56,
        one60,
        zero64,
    ) = reader.read(ANIM_INFO)

    assert_eq("field 00", 0, zero00, reader.prev + 0)
    assert_eq("field 04", 0, ptr04, reader.prev + 4)
    assert_eq("field 08", 0, zero08, reader.prev + 8)

    assert_gt("count", 0, count, reader.prev + 10)

    assert_ne("anim ptr", 0, anim_ptr, reader.prev + 12)
    # the localisation isn't used
    assert_eq("loc count", 0, loc_count, reader.prev + 16)
    assert_eq("loc ptr", 0, loc_ptr, reader.prev + 20)
    assert_ne("world ptr", 0, world_ptr, reader.prev + 24)

    # the gravity is always the same
    assert_eq("gravity", GRAVITY, gravity, reader.prev + 28)

    assert_eq("field 32", 0, zero32, reader.prev + 32)
    assert_eq("field 36", 0, zero36, reader.prev + 36)
    assert_eq("field 40", 0, zero40, reader.prev + 40)
    assert_eq("field 44", 0, zero44, reader.prev + 44)
    assert_eq("field 48", 0, zero48, reader.prev + 48)
    assert_eq("field 52", 0, zero52, reader.prev + 52)
    assert_eq("field 56", 0, zero56, reader.prev + 56)
    assert_eq("field 60", 1, one60, reader.prev + 60)
    # this is probably a float
    assert_eq("field 64", 0, zero64, reader.prev + 64)

    LOG.debug("Anim count is %d", count)

    return (count, anim_ptr, world_ptr)


def _read_anim_defs(
    reader: BinReader, count: int
) -> Tuple[List[AnimDef], List[AnimDefPointers]]:
    LOG.debug("Reading animation definition 0 at %d", reader.offset)
    # the first entry is always zero
    read_anim_def_zero(reader)
    anim_defs = []
    anim_def_ptrs = []
    for i in range(1, count):
        LOG.debug("Reading animation definition %d at %d", i, reader.offset)
        anim_def, anim_def_ptr = read_anim_def(reader)
        anim_defs.append(anim_def)
        anim_def_ptrs.append(anim_def_ptr)

    LOG.debug("Read animation definitions")
    return anim_defs, anim_def_ptrs


def read_anim(data: bytes) -> Tuple[AnimMetadata, List[AnimDef]]:
    reader = BinReader(data)
    LOG.debug("Reading animation data...")

    anim_names = _read_anim_header(reader)
    anim_count, anim_ptr, world_ptr = _read_anim_info(reader)
    anim_defs, anim_def_ptrs = _read_anim_defs(reader, anim_count)

    assert_eq("anim end", len(data), reader.offset, reader.offset)
    LOG.debug("Read animation data")

    anim_md = AnimMetadata(
        anim_names=anim_names,
        anim_ptr=anim_ptr,
        world_ptr=world_ptr,
        anim_def_ptrs=anim_def_ptrs,
    )

    return anim_md, anim_defs
