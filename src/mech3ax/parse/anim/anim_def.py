import logging
from io import StringIO
from struct import Struct
from typing import List, Optional

from mech3ax.errors import (
    assert_all_zero,
    assert_ascii,
    assert_eq,
    assert_flag,
    assert_ge,
    assert_gt,
    assert_in,
    assert_ne,
)
from mech3ax.serde import Base64

from ..int_flag import IntFlag
from ..utils import (
    BinReader,
    ascii_zterm_node_name,
    ascii_zterm_padded,
    ascii_zterm_partition,
)
from .activation_prereq import read_activation_prereq
from .models import (
    ANIM_ACTIVATION,
    AnimDef,
    NamePtrFlag,
    NameRaw,
    SeqActivation,
    SeqDef,
)
from .script import _parse_script

LOG = logging.getLogger(__name__)

ANIM_DEF = Struct("<32s 32s I 32s I 44s I 4B 6f 4I I 4I 40s II 12B 10I")
assert ANIM_DEF.size == 316, ANIM_DEF.size

STATIC_SOUND = Struct("<32s I")
assert STATIC_SOUND.size == 36, STATIC_SOUND.size

READER_LOOKUP = Struct("<32s 3I")
assert READER_LOOKUP.size == 44, READER_LOOKUP.size

NODE = Struct("<32s 2I")
assert NODE.size == 40, NODE.size

SEQDEF_INFO = Struct("<32s I 20s 2I")
assert SEQDEF_INFO.size == 64, SEQDEF_INFO.size

RESET_STATE = Struct("<56s 2I")
assert RESET_STATE.size == 64, RESET_STATE.size

ANIM_REF = Struct("<64s 2I")
assert ANIM_REF.size == 72, ANIM_REF.size

# OBJECT = Struct("<32s 2I 4I 32s 2I")
OBJECT = Struct("<32s I 60s")
assert OBJECT.size == 96, OBJECT.size


def _read_nodes(reader: BinReader, count: int, f: StringIO) -> List[NamePtrFlag]:
    # the first entry is always zero
    name_raw, zero, ptr = reader.read(NODE)
    assert_all_zero("name", name_raw, reader.prev + 0)
    assert_eq("field 32", 0, zero, reader.prev + 32)
    assert_eq("field 36", 0, ptr, reader.prev + 36)

    nodes = []
    for _ in range(1, count):
        name_raw, zero, ptr = reader.read(NODE)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_node_name(name_raw)
        assert_eq("field 32", 0, zero, reader.prev + 32)
        assert_ne("field 36", 0, ptr, reader.prev + 36)
        print("NODE", name, file=f, sep="\t")
        nodes.append(NamePtrFlag(name=name, ptr=ptr))

    return nodes


def _read_lights(reader: BinReader, count: int, f: StringIO) -> List[NamePtrFlag]:
    # the first entry is always zero
    name_raw, flag, ptr, zero = reader.read(READER_LOOKUP)
    assert_all_zero("name", name_raw, reader.prev + 0)
    assert_eq("field 32", 0, flag, reader.prev + 32)
    assert_eq("field 36", 0, ptr, reader.prev + 36)
    assert_eq("field 40", 0, zero, reader.prev + 40)

    lights = []
    for _ in range(1, count):
        name_raw, flag, ptr, zero = reader.read(READER_LOOKUP)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_node_name(name_raw)
        assert_eq("field 32", 0, flag, reader.prev + 32)
        assert_ne("field 36", 0, ptr, reader.prev + 36)
        # if this were non-zero, it would cause the light to be removed instead
        # of added (???)
        assert_eq("field 40", 0, zero, reader.prev + 40)
        print("LIGHT", name, file=f, sep="\t")
        lights.append(NamePtrFlag(name=name, ptr=ptr))

    return lights


def _read_puffers(reader: BinReader, count: int, f: StringIO) -> List[NamePtrFlag]:
    # the first entry is always zero
    name_raw, flag, ptr, zero = reader.read(READER_LOOKUP)
    assert_all_zero("name", name_raw, reader.prev + 0)
    assert_eq("field 32", 0, flag, reader.prev + 32)
    assert_eq("field 36", 0, ptr, reader.prev + 36)
    assert_eq("field 40", 0, zero, reader.prev + 40)

    puffers = []
    for _ in range(1, count):
        name_raw, flag, ptr, zero = reader.read(READER_LOOKUP)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)
        assert_eq("field 32", 0, (flag & 0x00FFFFFF), reader.prev + 32)
        # TODO: what does this flag mean?
        # this is something the code does, but i'm not sure why
        # some of these values make decent floating point numbers
        flag = flag >> 24
        assert_ne("field 36", 0, ptr, reader.prev + 36)
        assert_eq("field 40", 0, zero, reader.prev + 40)
        print("PUFFER", name, hex(flag), file=f, sep="\t")
        puffers.append(NamePtrFlag(name=name, ptr=ptr, flag=flag))

    return puffers


def _read_dynamic_sounds(
    reader: BinReader, count: int, f: StringIO
) -> List[NamePtrFlag]:
    # the first entry is always zero
    name_raw, flag, ptr, zero = reader.read(READER_LOOKUP)
    assert_all_zero("name", name_raw, reader.prev + 0)
    assert_eq("field 32", 0, flag, reader.prev + 32)
    assert_eq("field 36", 0, ptr, reader.prev + 36)
    assert_eq("field 40", 0, zero, reader.prev + 40)

    sounds = []
    for _ in range(1, count):
        name_raw, flag, ptr, zero = reader.read(READER_LOOKUP)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_node_name(name_raw)
        assert_eq("field 32", 0, flag, reader.prev + 32)
        assert_ne("field 36", 0, ptr, reader.prev + 36)
        assert_eq("field 40", 0, zero, reader.prev + 40)
        print("DYNSND", name, file=f, sep="\t")
        sounds.append(NamePtrFlag(name=name, ptr=ptr))

    return sounds


def _read_static_sounds(reader: BinReader, count: int, f: StringIO) -> List[NameRaw]:
    # the first entry is always zero
    name_raw, ptr = reader.read(STATIC_SOUND)
    assert_all_zero("name", name_raw, reader.prev + 0)
    assert_eq("field 32", 0, ptr, reader.prev + 32)

    sounds = []
    for _ in range(1, count):
        name_raw, ptr = reader.read(STATIC_SOUND)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name, pad = ascii_zterm_partition(name_raw)
        assert_eq("field 32", 0, ptr, reader.prev + 32)
        print("STCSND", name, file=f, sep="\t")
        sounds.append(NameRaw(name=name, pad=Base64(pad)))

    return sounds


def _read_sequence_definitions(
    reader: BinReader, anim_def: AnimDef, count: int, f: StringIO
) -> List[SeqDef]:
    sequences = []
    for _ in range(count):
        name_raw, flag, zero, seqdef_ptr, seqdef_len = reader.read(SEQDEF_INFO)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        assert_in("activation", (0x0, 0x303), flag, reader.prev + 32)
        activation: SeqActivation = "ON_CALL" if flag == 0x303 else "NONE"
        assert_all_zero("field 36", zero, reader.prev + 36)
        assert_gt("seqdef length", 0, seqdef_len, reader.prev + 56)
        assert_ne("seqdef ptr", 0, seqdef_ptr, reader.prev + 60)

        print(f"SEQUENCE_DEFINITION(NAME={name!r}, ACTIVATION={activation})", file=f)
        script = _parse_script(reader, anim_def, seqdef_len, f)
        sequences.append(SeqDef(ptr=seqdef_ptr, activation=activation, script=script))

    return sequences


def _read_reset_state(  # pylint: disable=too-many-arguments
    reader: BinReader,
    anim_def: AnimDef,
    length: int,
    ptr: int,
    offset: int,
    f: StringIO,
) -> Optional[SeqDef]:
    reset_raw, reset_ptr, reset_len = reader.read(RESET_STATE)
    with assert_ascii("reset end", reset_raw, reader.prev + 0):
        reset_end = ascii_zterm_padded(reset_raw)

    # this is always "RESET_SEQUENCE"
    assert_eq("reset end", "RESET_SEQUENCE", reset_end, reader.prev + 0)
    assert_eq("reset ptr", ptr, reset_ptr, reader.prev + 56)
    assert_eq("reset len", length, reset_len, reader.prev + 60)

    if not length:
        assert_eq("reset ptr", 0, ptr, offset)
        return None

    assert_ne("reset ptr", 0, ptr, offset)
    print("RESET_STATE", file=f)
    script = _parse_script(reader, anim_def, length, f)
    return SeqDef(ptr=ptr, script=script)


def _read_anim_refs(reader: BinReader, count: int, f: StringIO) -> List[NameRaw]:
    # the first entry... is not zero! as this is not a node list
    # there's one anim ref per CALL_ANIMATION, and there may be duplicates to
    # the same anim since multiple calls might need to be ordered
    anim_refs = []
    for _ in range(count):
        name_raw, zero64, zero68 = reader.read(ANIM_REF)
        # a bunch of these values are properly zero-terminated at 32 and beyond,
        # but not all... i suspect a lack of memset
        with assert_ascii("name", name_raw, reader.prev + 0):
            name, pad = ascii_zterm_partition(name_raw)

        assert_eq("field 64", 0, zero64, reader.prev + 64)
        assert_eq("field 68", 0, zero68, reader.prev + 68)

        print("ANIMREF", name, file=f, sep="\t")
        anim_refs.append(NameRaw(name=name, pad=Base64(pad.rstrip(b"\0"))))

    return anim_refs


def _read_objects(reader: BinReader, count: int, f: StringIO) -> List[NameRaw]:
    # the first entry is always zero
    data = reader.read_bytes(OBJECT.size)
    assert_all_zero("object", data, reader.prev)

    objects = []
    for _ in range(1, count):
        (name_raw, zero32, bin_dump) = reader.read(OBJECT)

        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_node_name(name_raw)

        assert_eq("field 32", 0, zero32, reader.prev + 32)

        print("OBJECT", name, file=f, sep="\t")

        # TODO: this is cheating, but i have no idea how to interpret this data
        # sometimes it's sensible, e.g. floats. other times, it seems like random
        # garbage.
        objects.append(NameRaw(name=name, pad=Base64(bin_dump.rstrip(b"\0"))))

    return objects


class AnimDefFlag(IntFlag):
    ExecutionByRange = 1 << 1
    ExecutionByZone = 1 << 3
    HasCallback = 1 << 4
    ResetUnk = 1 << 5
    NetworkLogSet = 1 << 10
    NetworkLogOn = 1 << 11
    SaveLogSet = 1 << 12
    SaveLogOn = 1 << 13
    AutoResetNodeStates = 1 << 16
    ProximityDamage = 1 << 20


def read_anim_def(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    reader: BinReader, f: StringIO
) -> AnimDef:
    (
        anim_name_raw,
        name_raw,
        base_node_ptr,  # 064
        anim_root_raw,
        anim_root_ptr,
        zero104,  # 44 zero bytes
        flag_raw,  # 148
        zero152,
        activation_value,
        action_prio,
        byte155,
        exec_by_range_min,
        exec_by_range_max,
        reset_time,
        zero168,
        max_health,
        cur_health,
        zero180,
        zero184,
        zero188,
        zero192,
        seq_defs_ptr,  # 196
        int200,
        int204,
        int208,
        int212,
        zero216,  # 40 zero bytes
        reset_state_ptr,  # 256
        reset_state_length,  # 260
        seq_def_count,  # 264
        object_count,  # 265
        node_count,  # 266
        light_count,  # 267
        puffer_count,  # 268
        dynamic_sound_count,  # 269
        static_sound_count,  # 270
        unknown_count,  # 271
        activ_prereq_count,  # 272
        activ_prereq_min_to_satisfy,  # 273
        anim_ref_count,  # 274
        zero275,
        objects_ptr,  # 276
        nodes_ptr,  # 280
        lights_ptr,  # 284
        puffers_ptr,  # 288
        dynamic_sounds_ptr,  # 292
        static_sounds_ptr,  # 296
        unknown_ptr,  # 300
        activ_prereqs_ptr,  # 304
        anim_refs_ptr,  # 308
        zero312,
    ) = reader.read(ANIM_DEF)

    # save this so we can output accurate offsets after doing further reads
    data_offset = reader.prev

    with assert_ascii("anim name", anim_name_raw, reader.prev + 0):
        anim_name, _anim_name_pad = ascii_zterm_partition(anim_name_raw)

    with assert_ascii("name", name_raw, reader.prev + 32):
        name = ascii_zterm_padded(name_raw)

    assert_ne("base node ptr", 0, base_node_ptr, data_offset + 64)

    with assert_ascii("anim root", anim_root_raw, reader.prev + 68):
        anim_root, _anim_root_pad = ascii_zterm_partition(anim_root_raw)

    if name != anim_root:
        assert_ne("anim root ptr", base_node_ptr, anim_root_ptr, data_offset + 100)
    else:
        assert_eq("anim root ptr", base_node_ptr, anim_root_ptr, data_offset + 100)

    assert_all_zero("field 104", zero104, data_offset + 104)

    with assert_flag("flag", flag_raw, data_offset + 148):
        flag = AnimDefFlag.check(flag_raw)

    network_log: Optional[bool] = None
    if AnimDefFlag.NetworkLogSet(flag):
        network_log = AnimDefFlag.NetworkLogOn(flag)

    save_log: Optional[bool] = None
    if AnimDefFlag.SaveLogSet(flag):
        save_log = AnimDefFlag.SaveLogOn(flag)

    assert_eq("field 152", 0, zero152, data_offset + 152)
    assert_in("field 153", (0, 1, 2, 3, 4), activation_value, data_offset + 153)
    assert_eq("field 154", 4, action_prio, data_offset + 154)
    assert_eq("field 155", 2, byte155, data_offset + 155)

    exec_by_zone = AnimDefFlag.ExecutionByZone(flag)
    if not AnimDefFlag.ExecutionByRange(flag):
        assert_eq("exec by range min", 0.0, exec_by_range_min, data_offset + 156)
        assert_eq("exec by range max", 0.0, exec_by_range_max, data_offset + 156)
        exec_by_range = None
    else:
        assert_eq("exec by zone", False, exec_by_zone, data_offset + 148)
        assert_ge("exec by range min", 0.0, exec_by_range_min, data_offset + 156)
        assert_ge(
            "exec by range max", exec_by_range_max, exec_by_range_max, data_offset + 156
        )
        exec_by_range = (exec_by_range_min, exec_by_range_max)

    if not AnimDefFlag.ResetUnk(flag):
        assert_eq("reset time", -1.0, reset_time, data_offset + 164)
        reset_time = None

    assert_eq("field 168", 0.0, zero168, data_offset + 168)
    assert_ge("health", 0.0, max_health, data_offset + 172)
    assert_eq("health", max_health, cur_health, data_offset + 176)
    assert_eq("field 180", 0, zero180, data_offset + 180)
    assert_eq("field 184", 0, zero184, data_offset + 184)
    assert_eq("field 188", 0, zero188, data_offset + 188)
    assert_eq("field 192", 0, zero192, data_offset + 192)

    # WTF???
    assert_eq("field 200", 0x45534552, int200, data_offset + 200)
    assert_eq("field 204", 0x45535F54, int204, data_offset + 204)
    assert_eq("field 208", 0x4E455551, int208, data_offset + 208)
    assert_eq("field 212", 0x00004543, int212, data_offset + 212)

    assert_all_zero("field 216", zero216, data_offset + 216)

    assert_eq("field 275", 0, zero275, data_offset + 275)
    assert_eq("field 312", 0, zero312, data_offset + 312)

    print("HEADER", file=f)
    print("NAME", repr(name), file=f)
    print("ANIMATION_NAME", repr(anim_name), file=f)
    print("ANIMATION_ROOT_NAME", repr(anim_root), file=f)

    activation = ANIM_ACTIVATION[activation_value]

    print("FLAG", repr(flag), file=f)

    print(
        "ACT",
        activation,
        "RST",
        reset_time,
        "HLT",
        max_health,
        "EXE",
        exec_by_range,
        "NLOG",
        network_log,
        "SLOG",
        save_log,
        file=f,
    )

    print("---", file=f)

    if object_count:
        assert_ne("object ptr", 0, objects_ptr, data_offset + 276)
        objects = _read_objects(reader, object_count, f)
    else:
        assert_eq("object ptr", 0, objects_ptr, data_offset + 276)
        objects = []

    if node_count:
        assert_ne("node ptr", 0, nodes_ptr, data_offset + 280)
        nodes = _read_nodes(reader, node_count, f)
    else:
        assert_eq("node ptr", 0, nodes_ptr, data_offset + 280)
        nodes = []

    if light_count:
        assert_ne("light ptr", 0, lights_ptr, data_offset + 284)
        lights = _read_lights(reader, light_count, f)
    else:
        assert_eq("light ptr", 0, lights_ptr, data_offset + 284)
        lights = []

    if puffer_count:
        assert_ne("puffer ptr", 0, puffers_ptr, data_offset + 288)
        puffers = _read_puffers(reader, puffer_count, f)
    else:
        assert_eq("puffer ptr", 0, puffers_ptr, data_offset + 288)
        puffers = []

    if dynamic_sound_count:
        assert_ne("dynamic sound ptr", 0, dynamic_sounds_ptr, data_offset + 292)
        dynamic_sounds = _read_dynamic_sounds(reader, dynamic_sound_count, f)
    else:
        assert_eq("dynamic sound ptr", 0, dynamic_sounds_ptr, data_offset + 292)
        dynamic_sounds = []

    if static_sound_count:
        assert_ne("static sound ptr", 0, static_sounds_ptr, data_offset + 296)
        static_sounds = _read_static_sounds(reader, static_sound_count, f)
    else:
        assert_eq("static sound ptr", 0, static_sounds_ptr, data_offset + 296)
        static_sounds = []

    # this isn't set in any file i have (it is read like the static sound data)
    assert_eq("unknown count", 0, unknown_count, data_offset + 271)
    assert_eq("unknown ptr", 0, unknown_ptr, data_offset + 300)

    if activ_prereq_count:
        assert_ne("activ prereq ptr", 0, activ_prereqs_ptr, data_offset + 304)
        assert_in(
            "activ prereq min",
            (0, 1, 2),
            activ_prereq_min_to_satisfy,
            data_offset + 273,
        )
        activ_prereq = read_activation_prereq(
            reader, activ_prereq_count, activ_prereq_min_to_satisfy,
        )
    else:
        assert_eq("activ prereq ptr", 0, activ_prereqs_ptr, data_offset + 304)
        assert_eq("activ prereq min", 0, activ_prereq_min_to_satisfy, data_offset + 273)
        activ_prereq = None

    if anim_ref_count:
        assert_ne("anim ref ptr", 0, anim_refs_ptr, data_offset + 308)
        anim_refs = _read_anim_refs(reader, anim_ref_count, f)
    else:
        assert_eq("anim ref ptr", 0, anim_refs_ptr, data_offset + 308)
        anim_refs = []

    anim_def = AnimDef(
        name=name,
        anim_name=anim_name,
        anim_root=anim_root,
        # ---
        auto_reset_node_states=AnimDefFlag.AutoResetNodeStates(flag),
        activation=activation,
        execution_by_range=exec_by_range,
        execution_by_zone=exec_by_zone,
        network_log=network_log,
        save_log=save_log,
        has_callback=AnimDefFlag.HasCallback(flag),
        callback_count=0,
        reset_time=reset_time,
        health=max_health,
        proximity_damage=AnimDefFlag.ProximityDamage(flag),
        # ---
        objects=objects,
        nodes=nodes,
        lights=lights,
        puffers=puffers,
        dynamic_sounds=dynamic_sounds,
        static_sounds=static_sounds,
        activation_prereq=activ_prereq,
        anim_refs=anim_refs,
        # skip reset_sequence and sequences, as they need to look up other items
        # ---
        objects_ptr=objects_ptr,
        nodes_ptr=nodes_ptr,
        lights_ptr=lights_ptr,
        puffers_ptr=puffers_ptr,
        dynamic_sounds_ptr=dynamic_sounds_ptr,
        static_sounds_ptr=static_sounds_ptr,
        activ_prereqs_ptr=activ_prereqs_ptr,
        anim_refs_ptr=anim_refs_ptr,
        reset_state_ptr=reset_state_ptr,
        seq_defs_ptr=seq_defs_ptr,
    )

    print("---", file=f)

    # unconditional read
    anim_def.reset_sequence = _read_reset_state(
        reader, anim_def, reset_state_length, reset_state_ptr, data_offset + 256, f
    )

    if seq_def_count:
        assert_ne("seq ptr", 0, seq_defs_ptr, data_offset + 196)
        anim_def.sequences = _read_sequence_definitions(
            reader, anim_def, seq_def_count, f
        )
    else:
        assert_eq("seq ptr", 0, seq_defs_ptr, data_offset + 196)

    # the Callback script object checks if callbacks are allowed, but i also
    # want to catch the case where the flag might've been set, but no callbacks
    # were in the scripts
    if anim_def.has_callback:
        assert_gt("callbacks", 0, anim_def.callback_count, data_offset + 148)

    # don't need this value any more
    anim_def.callback_count = 0

    return anim_def


def read_anim_def_zero(reader: BinReader) -> None:
    # the first entry is always zero
    data = bytearray(reader.read_bytes(ANIM_DEF.size))
    # except for this one byte?
    assert_eq("anim def header byte 153", 3, data[153], reader.prev + 153)
    data[153] = 0
    assert_all_zero("anim def header", data, reader.prev)
    bdata = reader.read_bytes(RESET_STATE.size)
    assert_all_zero("anim def reset", bdata, reader.prev)
