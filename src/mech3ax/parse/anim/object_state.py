from __future__ import annotations

from math import degrees, pi
from struct import Struct
from typing import Literal, Optional, Tuple, Union

from mech3ax.errors import (
    assert_ascii,
    assert_between,
    assert_eq,
    assert_flag,
    assert_gt,
    assert_in,
    assert_lt,
)

from ..int_flag import IntFlag
from ..utils import BinReader, ascii_zterm_padded
from .models import INPUT_NODE, AnimDef, ScriptObject

DUMMY_IMPORT = None
PI2 = pi * 2


class ObjectActiveState(ScriptObject):
    _NAME: str = "OBJECT_ACTIVE_STATE"
    _NUMBER: int = 6
    _STRUCT: Struct = Struct("<2I")

    node: str
    state: bool

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> ObjectActiveState:
        state, node_index = reader.read(cls._STRUCT)
        assert_in("state", (0, 1), state, reader.prev + 0)
        node = anim_def.get_node(node_index - 1, reader.prev + 4)
        return cls(node=node, state=state == 1)

    def __repr__(self) -> str:
        state_name = "ACTIVE" if self.state else "INACTIVE"
        return f"{self._NAME}(NAME={self.node!r}, STATE={state_name})"


class ObjectTranslateState(ScriptObject):
    _NAME: str = "OBJECT_TRANSLATE_STATE"
    _NUMBER: int = 7
    _STRUCT: Struct = Struct("<i 3f i")

    node: str
    state: Tuple[float, float, float]

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> ObjectTranslateState:
        at_node_matrix, tx, ty, tz, node_index = reader.read(cls._STRUCT)
        assert_eq("field 00", 0, at_node_matrix, reader.prev + 0)
        if node_index < 1:
            assert_lt("node index", -13107190, node_index, reader.prev + 16)
            node = "INPUT_NODE"
        else:
            node = anim_def.get_node(node_index - 1, reader.prev + 16)
        return cls(node=node, state=(tx, ty, tz))

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.node!r}, STATE={self.state})"


class ObjectScaleState(ScriptObject):
    _NAME: str = "OBJECT_SCALE_STATE"
    _NUMBER: int = 8
    _STRUCT: Struct = Struct("<3f I")

    node: str
    state: Tuple[float, float, float]

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> ObjectScaleState:
        sx, sy, sz, node_index = reader.read(cls._STRUCT)
        node = anim_def.get_node(node_index - 1, reader.prev + 12)
        return cls(node=node, state=(sx, sy, sz))

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.node!r}, STATE={self.state})"


RotationMode = Union[
    Literal["ABSOLUTE"], Literal["AT_NODE_XYZ"], Literal["AT_NODE_MATRIX"]
]


class ObjectRotateState(ScriptObject):
    _NAME: str = "OBJECT_ROTATE_STATE"
    _NUMBER: int = 9
    _STRUCT: Struct = Struct("<i 3f 2h")

    node: str
    mode: RotationMode = "ABSOLUTE"
    state: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> ObjectRotateState:
        flag, rx, ry, rz, node_index, at_index = reader.read(cls._STRUCT)

        # FLAG (mutually exclusive)
        # if this is a camera:
        # 0 -> absolute rotation
        # 1 -> relative rotation
        # if this is a 3d object:
        # 0 -> absolute rotation
        # 1 -> relative rotation
        # 2 -> AT_NODE_XYZ
        # 4 -> AT_NODE_MATRIX
        assert_in("flag", (0, 2, 4), flag, reader.prev + 0)
        node = anim_def.get_node(node_index - 1, reader.prev + 16)

        if flag == 0:
            assert_between("rot x", -PI2, PI2, rx, reader.prev + 4)
            assert_between("rot y", -PI2, PI2, ry, reader.prev + 8)
            assert_between("rot z", -PI2, PI2, rz, reader.prev + 12)
            state = (degrees(rx), degrees(ry), degrees(rz))
            assert_eq("at node", 0, at_index, reader.prev + 18)
            mode: RotationMode = "ABSOLUTE"
        else:
            assert_eq("rot x", 0.0, rx, reader.prev + 4)
            assert_eq("rot y", 0.0, ry, reader.prev + 8)
            assert_eq("rot z", 0.0, rz, reader.prev + 12)
            state = (0.0, 0.0, 0.0)
            assert_eq("at node", -200, at_index, reader.prev + 18)
            if flag == 2:
                mode = "AT_NODE_XYZ"
            else:
                mode = "AT_NODE_MATRIX"

        return cls(node=node, mode=mode, state=state)

    def __repr__(self) -> str:
        if self.mode == "ABSOLUTE":
            return f"{self._NAME}(NAME={self.node!r}, STATE={self.state})"
        if self.mode == "AT_NODE_XYZ":
            return f"{self._NAME}(NAME={self.node!r}, AT_NODE_XYZ={INPUT_NODE!r})"
        if self.mode == "AT_NODE_MATRIX":
            return f"{self._NAME}(NAME={self.node!r}, AT_NODE_MATRIX={INPUT_NODE!r})"
        raise ValueError(f"Unknown mode {self.mode}")


class ObjectOpacityState(ScriptObject):
    _NAME: str = "OBJECT_OPACITY_STATE"
    _NUMBER: int = 13
    _STRUCT: Struct = Struct("<2H f I")

    node: str
    is_set: bool
    state: bool
    opacity: float

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> ObjectOpacityState:
        is_set_raw, state_raw, opacity, node_index = reader.read(cls._STRUCT)
        # this could be another value (e.g. -1), in which case is set is not changed
        assert_in("is set", (0, 1), is_set_raw, reader.prev + 0)
        # the state does not seem to depend on is_set?
        assert_in("state", (0, 1), state_raw, reader.prev + 2)
        state = state_raw == 1
        if state:
            assert_between("opacity", 0.0, 1.0, opacity, reader.prev + 4)
        else:
            assert_eq("opacity", 0.0, opacity, reader.prev + 4)
        node = anim_def.get_node(node_index - 1, reader.prev + 8)
        return cls(node=node, is_set=is_set_raw == 1, state=state, opacity=opacity)

    def __repr__(self) -> str:
        state_name = "ON" if self.state else "OFF"
        return f"{self._NAME}(NAME={self.node!r}, IS_SET={self.is_set}, STATE={state_name}, OPACITY={self.opacity})"


class ObjectOpacityFromTo(ScriptObject):
    _NAME: str = "OBJECT_OPACITY_FROM_TO"
    _NUMBER: int = 14
    _STRUCT: Struct = Struct("<I 2h f f f f")

    node: str
    opacity_from: Tuple[float, int]
    opacity_to: Tuple[float, int]
    run_time: float
    delta: float

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> ObjectOpacityFromTo:
        (
            node_index,
            from_state,
            to_state,
            from_value,
            to_value,
            delta,
            run_time,
        ) = reader.read(cls._STRUCT)

        node = anim_def.get_node(node_index - 1, reader.prev + 0)
        assert_in("from state", (-1, 0, 1), from_state, reader.prev + 4)
        assert_in("to state", (-1, 0, 1), to_state, reader.prev + 6)
        assert_between("from opacity", 0.0, 1.0, from_value, reader.prev + 8)
        assert_between("to opacity", 0.0, 1.0, to_value, reader.prev + 12)
        # delta is roughly: (to_value - from_value) / run_time
        assert_gt("run time", 0.0, run_time, reader.prev + 20)

        return cls(
            node=node,
            opacity_from=(from_value, from_state),
            opacity_to=(to_value, to_state),
            run_time=run_time,
            delta=delta,
        )

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.node!r}, OPACITY_FROM={self.opacity_from}, OPACITY_TO={self.opacity_to}, RUN_TIME={self.run_time})"


class ObjectAddChild(ScriptObject):
    _NAME: str = "OBJECT_ADD_CHILD"
    _NUMBER: int = 15
    _STRUCT: Struct = Struct("<2H")

    parent: str
    child: str

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> ObjectAddChild:
        parent_index, child_index = reader.read(cls._STRUCT)
        parent_node = anim_def.get_node(parent_index - 1, reader.prev + 0)
        child_node = anim_def.get_node(child_index - 1, reader.prev + 2)
        return cls(parent=parent_node, child=child_node)

    def __repr__(self) -> str:
        # in the zbd, both values are fused into a list (PARENT_CHILD)
        return f"{self._NAME}(PARENT={self.parent!r}, CHILD={self.child!r})"


class ObjectCycleTexture(ScriptObject):
    _NAME: str = "OBJECT_CYCLE_TEXTURE"
    _NUMBER: int = 17
    _STRUCT: Struct = Struct("<4H")

    node: str
    reset: int

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> ObjectCycleTexture:
        one, zero, node_index, reset = reader.read(cls._STRUCT)
        # increment?
        assert_eq("field 0", 1, one, reader.prev + 0)
        # start index?
        assert_eq("field 4", 0, zero, reader.prev + 2)
        node = anim_def.get_node(node_index - 1, reader.prev + 4)
        assert_between("reset", 0, 5, reset, reader.prev + 6)
        return cls(node=node, reset=reset)

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.node!r}, RESET={self.reset})"


class ConnectorFlag(IntFlag):
    FromNode = 1 << 0
    FromInputNode = 1 << 1
    FromPos = 1 << 3
    FromInputPos = 1 << 4

    ToNode = 1 << 5  # this doesn't appear
    ToInputNode = 1 << 6
    ToPos = 1 << 8
    ToInputPos = 1 << 9

    MaxLength = 1 << 15


Vec3 = Tuple[float, float, float]


class ObjectConnector(ScriptObject):
    _NAME: str = "OBJECT_CONNECTOR"
    _NUMBER: int = 18
    _STRUCT: Struct = Struct("<I 2H 2H 3f 3f 9f f")

    node: str
    from_node: Optional[str] = None
    to_node: Optional[str] = None
    from_pos: Optional[Vec3] = None
    to_pos: Optional[Vec3] = None
    max_length: Optional[float] = None

    @classmethod
    def read(  # pylint: disable=too-many-locals,too-many-statements,too-many-branches
        cls, reader: BinReader, anim_def: AnimDef
    ) -> ObjectConnector:
        (
            flag_raw,
            node_index,
            from_index,
            to_index,
            pad10,
            from_x,
            from_y,
            from_z,
            to_x,
            to_y,
            to_z,
            zero36,
            zero40,
            zero44,
            zero48,
            one52,
            one56,
            zero60,
            zero64,
            zero68,
            max_length,
        ) = reader.read(cls._STRUCT)

        with assert_flag("flag", flag_raw, reader.prev + 0):  # 12
            flag = ConnectorFlag.check(flag_raw)

        node = anim_def.get_node(node_index - 1, reader.prev + 4)  # 16

        from_input_node = ConnectorFlag.FromInputNode(flag)
        from_input_pos = ConnectorFlag.FromInputPos(flag)

        from_node: Optional[str] = None
        if ConnectorFlag.FromNode(flag):
            assert_eq("from input node", False, from_input_node, reader.prev + 0)
            assert_eq("from input pos", False, from_input_pos, reader.prev + 0)
            from_node = anim_def.get_node(from_index - 1, reader.prev + 6)
        else:
            assert_eq("from node", 0, from_index, reader.prev + 6)  # 18
            if from_input_node:
                from_node = INPUT_NODE
            else:
                # this isn't required, but if it's false, from_input_pos would
                # need to be stored. as is, from_node = None and from_pos = None
                # implies from_input_pos
                assert_eq("from input pos", True, from_input_pos, reader.prev + 0)

        to_input_node = ConnectorFlag.ToInputNode(flag)
        to_input_pos = ConnectorFlag.ToInputPos(flag)

        to_node: Optional[str] = None
        if ConnectorFlag.ToNode(flag):
            assert_eq("to input node", False, to_input_node, reader.prev + 0)
            assert_eq("to input pos", False, to_input_pos, reader.prev + 0)
            to_node = anim_def.get_node(to_index - 1, reader.prev + 8)
        else:
            assert_eq("to node", 0, to_index, reader.prev + 8)  # 20
            if to_input_node:
                to_node = INPUT_NODE
            else:
                # this isn't required, but if it's false, to_input_pos would
                # need to be stored. as is, to_node = None and to_pos = None
                # implies to_input_pos
                assert_eq("to input pos", True, to_input_pos, reader.prev + 0)

        assert_eq("field 10", 0, pad10, reader.prev + 10)

        if ConnectorFlag.FromPos(flag):
            assert_eq("from input pos", False, from_input_pos, reader.prev + 0)
            from_pos: Optional[Vec3] = (from_x, from_y, from_z)
        else:
            assert_eq("from x", 0.0, from_x, reader.prev + 12)
            assert_eq("from y", 0.0, from_y, reader.prev + 16)
            assert_eq("from z", 0.0, from_z, reader.prev + 20)
            from_pos = None

        if ConnectorFlag.ToPos(flag):
            assert_eq("to input pos", False, to_input_pos, reader.prev + 0)
            to_pos: Optional[Vec3] = (to_x, to_y, to_z)
        else:
            assert_eq("to x", 0.0, to_x, reader.prev + 24)
            assert_eq("to y", 0.0, to_y, reader.prev + 28)
            assert_eq("to z", 0.0, to_z, reader.prev + 32)
            to_pos = None

        assert_eq("field 36", 0.0, zero36, reader.prev + 36)  # 48
        assert_eq("field 40", 0.0, zero40, reader.prev + 40)  # 52
        assert_eq("field 44", 0.0, zero44, reader.prev + 44)  # 56
        assert_eq("field 48", 0.0, zero48, reader.prev + 48)  # 60
        assert_eq("field 52", 1.0, one52, reader.prev + 52)  # 64
        assert_eq("field 56", 1.0, one56, reader.prev + 56)  # 68
        assert_eq("field 60", 0.0, zero60, reader.prev + 60)  # 72
        assert_eq("field 64", 0.0, zero64, reader.prev + 64)  # 76
        assert_eq("field 68", 0.0, zero68, reader.prev + 68)  # 80

        if ConnectorFlag.MaxLength(flag):
            assert_gt("max length", 0.0, max_length, reader.prev + 72)  # 84
        else:
            assert_eq("max length", 0.0, max_length, reader.prev + 72)
            max_length = None

        return cls(
            node=node,
            from_node=from_node,
            to_node=to_node,
            from_pos=from_pos,
            to_pos=to_pos,
            max_length=max_length,
        )

    def __repr__(self) -> str:
        return "\n".join(
            [
                f"{self._NAME}(",
                f"  NAME={self.node!r},",
                f"  FROM_NODE={self.from_node!r},",
                f"  TO_NODE={self.to_node!r},",
                f"  FROM_POS={self.from_pos},",
                f"  TO_POS={self.to_pos},",
                f"  MAX_LENGTH={self.max_length},",
                ")",
            ]
        )


class CallObjectConnector(ScriptObject):
    _NAME: str = "CALL_OBJECT_CONNECTOR"
    _NUMBER: int = 19
    _STRUCT: Struct = Struct("<I 32s 2h 2h 3f 3f")

    node: str
    from_node: str
    to_node: str
    to_pos: Tuple[float, float, float]

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> CallObjectConnector:
        (
            flag_raw,
            name_raw,
            node_index,
            save_index,
            from_index,
            to_index,
            from_x,
            from_y,
            from_z,
            to_x,
            to_y,
            to_z,
        ) = reader.read(cls._STRUCT)

        # this flag isn't the same as OBJECT_CONNECTOR, and unfortunately,
        # there are only 2 CALL_OBJECT_CONNECTOR script objects in the entirety
        # of the game - and even they have the same values!
        # these should correspond to FROM_NODE_POS, TO_INPUT_NODE_POS, TO_POS.
        expected = 1024 | 512 | 2
        assert_eq("flag", expected, flag_raw, reader.prev + 0)

        with assert_ascii("name", name_raw, reader.prev + 4):
            name = ascii_zterm_padded(name_raw)

        # this is always 0 and forces a node lookup from the name
        assert_eq("node", 0, node_index, reader.prev + 36)
        assert_eq("save", -1, save_index, reader.prev + 38)

        from_node = anim_def.get_node(from_index - 1, reader.prev + 40)
        assert_eq("to node", 0, to_index, reader.prev + 42)

        assert_eq("from_x", 0.0, from_x, reader.prev + 44)
        assert_eq("from_y", 0.0, from_y, reader.prev + 48)
        assert_eq("from_z", 0.0, from_z, reader.prev + 52)

        return cls(
            node=name,
            from_node=from_node,
            to_node=INPUT_NODE,
            to_pos=(to_x, to_y, to_z),
        )

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.node!r}, FROM_NODE_POS={self.from_node!r}, TO_POS={self.to_pos})"
