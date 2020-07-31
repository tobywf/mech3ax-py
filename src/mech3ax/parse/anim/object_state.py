from __future__ import annotations

from math import degrees, pi
from struct import Struct
from typing import Tuple

from mech3ax.errors import (
    assert_ascii,
    assert_between,
    assert_eq,
    assert_ge,
    assert_gt,
    assert_in,
)

from ..utils import BinReader, ascii_zterm_padded
from .models import AnimDef, ScriptObject

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
        state, index = reader.read(cls._STRUCT)
        assert_in("state", (0, 1), state, reader.prev + 0)
        node = anim_def.get_node(index - 1, reader.prev + 4)
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
        at_node_matrix, tx, ty, tz, index = reader.read(cls._STRUCT)
        assert_eq("field 00", 0, at_node_matrix, reader.prev + 0)
        node = anim_def.get_node_or_input(index - 1, reader.prev + 16)
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
        sx, sy, sz, index = reader.read(cls._STRUCT)
        node = anim_def.get_node(index - 1, reader.prev + 12)
        return cls(node=node, state=(sx, sy, sz))

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.node!r}, STATE={self.state})"


class ObjectRotateState(ScriptObject):
    _NAME: str = "OBJECT_ROTATE_STATE"
    _NUMBER: int = 9
    _STRUCT: Struct = Struct("<i 3f i")

    node: str
    state: Tuple[float, float, float]
    at_node_matrix: int = 0

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> ObjectRotateState:
        at_node_matrix, rx, ry, rz, index = reader.read(cls._STRUCT)

        assert_in("at node matrix", (0, 2, 4), at_node_matrix, reader.prev + 0)
        assert_between("rot x", -PI2, PI2, rx, reader.prev + 4)
        assert_between("rot y", -PI2, PI2, ry, reader.prev + 8)
        assert_between("rot z", -PI2, PI2, rz, reader.prev + 12)

        state = (degrees(rx), degrees(ry), degrees(rz))
        node = anim_def.get_node_or_input(index - 1, reader.prev + 16)

        return cls(node=node, state=state, at_node_matrix=at_node_matrix)

    def __repr__(self) -> str:
        if self.at_node_matrix:
            return f"{self._NAME}(NAME={self.node!r}, AT_NODE_MATRIX={self.at_node_matrix}, STATE={self.state})"
        return f"{self._NAME}(NAME={self.node!r}, STATE={self.state})"


class ObjectOpacityState(ScriptObject):
    _NAME: str = "OBJECT_OPACITY_STATE"
    _NUMBER: int = 13
    _STRUCT: Struct = Struct("<2H f I")

    node: str
    state: bool
    opacity: float
    unk: int

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> ObjectOpacityState:
        unk, state, opacity, index = reader.read(cls._STRUCT)
        assert_in("field 0", (0, 1), unk, reader.prev + 0)
        assert_in("state", (0, 1), state, reader.prev + 2)
        if state == 1:
            assert_between("opacity", 0.0, 1.0, opacity, reader.prev + 4)
        else:
            assert_eq("opacity", 0.0, opacity, reader.prev + 4)
        node = anim_def.get_node(index - 1, reader.prev + 8)
        return cls(node=node, state=state == 1, opacity=opacity, unk=unk)

    def __repr__(self) -> str:
        state_name = "ON" if self.state else "OFF"
        return f"{self._NAME}(NAME={self.node!r}, STATE={state_name}, OPACITY={self.opacity}, UNK={self.unk})"


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
            index,
            from_state,
            to_state,
            from_value,
            to_value,
            delta,
            run_time,
        ) = reader.read(cls._STRUCT)

        node = anim_def.get_node(index - 1, reader.prev + 0)
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
        one, zero, index, reset = reader.read(cls._STRUCT)
        # increment?
        assert_eq("field 0", 1, one, reader.prev + 0)
        # start index?
        assert_eq("field 4", 0, zero, reader.prev + 2)
        node = anim_def.get_node(index - 1, reader.prev + 4)
        assert_between("reset", 0, 5, reset, reader.prev + 6)
        return cls(node=node, reset=reset)

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.node!r}, RESET={self.reset})"


class ObjectConnector(ScriptObject):
    _NAME: str = "OBJECT_CONNECTOR"
    _NUMBER: int = 18
    _STRUCT: Struct = Struct("<2H 2H 2H 3f 3f 9f f")

    node: str
    from_node: str
    to_node: str
    from_pos: Tuple[float, float, float]
    to_pos: Tuple[float, float, float]
    max_length: float
    unk: int

    @classmethod
    def read(  # pylint: disable=too-many-locals
        cls, reader: BinReader, anim_def: AnimDef
    ) -> ObjectConnector:
        (
            unk00,
            zero02,
            index,
            from_index,
            to_index,
            zero10,
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

        assert_eq("field 02", 0, zero02, reader.prev + 2)
        node = anim_def.get_node(index - 1, reader.prev + 4)
        from_node = anim_def.get_node_or_input(from_index - 1, reader.prev + 6)
        to_node = anim_def.get_node_or_input(to_index - 1, reader.prev + 8)
        assert_eq("field 10", 0, zero10, reader.prev + 10)

        assert_eq("field 36", 0.0, zero36, reader.prev + 36)
        assert_eq("field 40", 0.0, zero40, reader.prev + 40)
        assert_eq("field 44", 0.0, zero44, reader.prev + 44)
        assert_eq("field 48", 0.0, zero48, reader.prev + 48)
        assert_eq("field 52", 1.0, one52, reader.prev + 52)
        assert_eq("field 56", 1.0, one56, reader.prev + 56)
        assert_eq("field 60", 0.0, zero60, reader.prev + 60)
        assert_eq("field 64", 0.0, zero64, reader.prev + 64)
        assert_eq("field 68", 0.0, zero68, reader.prev + 68)
        assert_ge("max length", 0.0, max_length, reader.prev + 72)

        return cls(
            node=node,
            from_node=from_node,
            to_node=to_node,
            from_pos=(from_x, from_y, from_z),
            to_pos=(to_x, to_y, to_z),
            max_length=max_length,
            # this must have something to do with from/to node/pos
            unk=unk00,
        )

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.node!r}, FROM_NODE={self.from_node!r}, TO_NODE={self.to_node!r}, FROM_POS={self.from_pos}, TO_POS={self.to_pos}, MAX_LENGTH={self.max_length}, UNK={self.unk:4X})"


class CallObjectConnector(ScriptObject):
    _NAME: str = "CALL_OBJECT_CONNECTOR"
    _NUMBER: int = 19
    _STRUCT: Struct = Struct("<2b h 32s 2h I 3f 3f")

    node: str
    from_node: str
    to_pos: Tuple[float, float, float]

    @classmethod
    def read(cls, reader: BinReader, anim_def: AnimDef) -> CallObjectConnector:
        (
            two00,
            six01,
            zero02,
            name_raw,
            # to_index?
            zero36,
            mone38,
            from_index,
            # FROM_POS?
            zero44,
            zero48,
            zero52,
            to_x,
            to_y,
            to_z,
        ) = reader.read(cls._STRUCT)

        # these may have something to do with from/to node/pos
        # (how to call OBJECT_CONNECTOR?)
        assert_eq("field 00", 2, two00, reader.prev + 0)
        assert_eq("field 01", 6, six01, reader.prev + 1)
        assert_eq("field 02", 0, zero02, reader.prev + 2)

        with assert_ascii("name", name_raw, reader.prev + 4):
            name = ascii_zterm_padded(name_raw)

        # TO_INPUT_NODE_POS / TO_NODE_POS: INPUT_NODE ?
        assert_eq("field 36", 0, zero36, reader.prev + 36)
        assert_eq("field 38", -1, mone38, reader.prev + 38)

        from_node = anim_def.get_node(from_index - 1, reader.prev + 40)
        assert_eq("field 44", 0.0, zero44, reader.prev + 44)
        assert_eq("field 48", 0.0, zero48, reader.prev + 48)
        assert_eq("field 52", 0.0, zero52, reader.prev + 52)

        return cls(node=name, from_node=from_node, to_pos=(to_x, to_y, to_z),)

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.node!r}, FROM_NODE={self.from_node!r}, TO_POS={self.to_pos})"
