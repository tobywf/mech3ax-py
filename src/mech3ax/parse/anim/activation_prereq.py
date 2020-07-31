import logging
from struct import Struct
from typing import Optional, Tuple

from mech3ax.errors import assert_ascii, assert_eq, assert_in, assert_ne

from ..utils import BinReader, ascii_zterm_padded
from .models import ActivationPrereq, PrereqObject

LOG = logging.getLogger(__name__)

ACTIV_PREREQ_HEADER = Struct("<2I")
assert ACTIV_PREREQ_HEADER.size == 8, ACTIV_PREREQ_HEADER.size

ACTIV_PREREQ_ANIM = Struct("<32s 2I")
assert ACTIV_PREREQ_ANIM.size == 40, ACTIV_PREREQ_ANIM.size

ACTIV_PREREQ_OBJ = Struct("<I 32s I")
assert ACTIV_PREREQ_OBJ.size == 40, ACTIV_PREREQ_OBJ.size

OptPrereqObj = Optional[PrereqObject]


def read_activation_prereq_anim(reader: BinReader) -> str:
    name_raw, zero32, zero36 = reader.read(ACTIV_PREREQ_ANIM)
    with assert_ascii("activ prereq name", name_raw, reader.prev + 0):
        name = ascii_zterm_padded(name_raw)
    # field offset from start of record
    assert_eq("activ prereq field 40", 0, zero32, reader.prev + 32)
    assert_eq("activ prereq field 44", 0, zero36, reader.prev + 36)
    return name


def read_activation_prereq_obj(
    reader: BinReader, required: bool, prereq_type: int, prev: OptPrereqObj
) -> Tuple[OptPrereqObj, OptPrereqObj]:
    active, name_raw, ptr = reader.read(ACTIV_PREREQ_OBJ)
    with assert_ascii("activ prereq name", name_raw, reader.prev + 4):
        name = ascii_zterm_padded(name_raw)
    assert_ne("activ prereq ptr", 0, ptr, reader.prev + 36)

    if prereq_type == 3:
        assert_eq("activ prereq active", 0, active, reader.prev + 0)
        # remember the current node as the previous one
        prev = PrereqObject(required=required, active=False, name=name, ptr=ptr)
        return prev, None

    assert_in("activ prereq active", (0, 1), active, reader.prev + 0)
    if prev:
        assert_eq("activ prereq required", prev.required, required, reader.prev + 0)
        parent_name = prev.name
        parent_ptr = prev.ptr
    else:
        parent_name = ""
        parent_ptr = 0

    obj = PrereqObject(
        required=required,
        active=active == 1,
        name=name,
        ptr=ptr,
        parent_name=parent_name,
        parent_ptr=parent_ptr,
    )
    # set the previous node to NULL
    return None, obj


def read_activation_prereq(
    reader: BinReader, count: int, min_to_satisfy: int,
) -> Optional[ActivationPrereq]:
    LOG.debug("Reading activation prerequisites at %d", reader.offset)

    anim_list = []
    obj_list = []
    prev: OptPrereqObj = None
    for _ in range(count):
        optional, prereq_type = reader.read(ACTIV_PREREQ_HEADER)
        # this is actually a byte in the code, but this way we also validate the padding
        assert_in("activ prereq type", (1, 2, 3), prereq_type, reader.prev + 4)
        if prereq_type == 1:
            # ANIMATION_LIST (these are always required)
            assert_eq("activ prereq optional", 0, optional, reader.prev + 0)
            anim_list.append(read_activation_prereq_anim(reader))
        else:
            # OBJECT_INACTIVE_LIST / OBJECT_ACTIVE_LIST
            assert_in("activ prereq optional", (0, 1), optional, reader.prev + 0)
            prev, obj = read_activation_prereq_obj(
                reader, optional == 0, prereq_type, prev
            )
            if obj:
                obj_list.append(obj)

    LOG.debug("Read activation prerequisites")
    return ActivationPrereq(
        min_to_satisfy=min_to_satisfy, anim_list=anim_list, obj_list=obj_list
    )
