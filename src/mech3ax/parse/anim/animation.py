from __future__ import annotations

from struct import Struct
from typing import Optional

from mech3ax.errors import (
    assert_ascii,
    assert_between,
    assert_eq,
    assert_flag,
    assert_in,
)

from ..int_flag import IntFlag
from ..utils import BinReader, ascii_zterm_padded
from .models import (
    INPUT_NODE,
    AnimDef,
    AtNodeFlex,
    AtNodeLong,
    AtNodeShort,
    ScriptObject,
)

DUMMY_IMPORT = None


class CallAnimationFlag(IntFlag):
    Nothing = 0
    # Call with AT_NODE (OPERAND_NODE can't be used)
    AtNode = 1 << 0
    # AT_NODE/WITH_NODE has translation coordinates
    Translation = 1 << 1
    # AT_NODE has rotation coordinates
    Rotation = 1 << 2
    # Call with WITH_NODE (OPERAND_NODE can't be used)
    WithNode = 1 << 3
    # WAIT_FOR_COMPLETION is set
    WaitFor = 1 << 4


class CallAnimation(ScriptObject):
    _NAME: str = "CALL_ANIMATION"
    _NUMBER: int = 24
    _STRUCT: Struct = Struct("<32s 4h i 3f 3f")

    name: str

    at_node: AtNodeFlex = None
    with_node: Optional[AtNodeShort] = None
    operand_node: Optional[str] = None
    wait_for_completion: int = -1

    @classmethod
    def read(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        cls, reader: BinReader, anim_def: AnimDef
    ) -> CallAnimation:
        (
            name_raw,
            operand_index,
            flag_raw,
            anim_index,
            wait_for_completion,
            node_index,
            tx,
            ty,
            tz,
            rx,
            ry,
            rz,
        ) = reader.read(cls._STRUCT)

        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        # not all combinations are present
        assert_in("flag", (0, 1, 3, 7, 8, 10, 16), flag_raw, reader.prev + 34)  # 46

        with assert_flag("flag", flag_raw, reader.prev + 34):
            flag = CallAnimationFlag.check(flag_raw)

        # this is used to store the index of the animation to call once loaded
        assert_eq("anim index", 0, anim_index, reader.prev + 36)  # 48

        if CallAnimationFlag.WaitFor(flag):
            # since multiple animation with the same name may be called, translating
            # this to a name would lose information
            max_pref_ref = len(anim_def.anim_refs) - 1
            assert_between(
                "wait for", 0, max_pref_ref, wait_for_completion, reader.prev + 38
            )
        else:
            assert_eq("wait for", -1, wait_for_completion, reader.prev + 38)  # 50

        has_at_node = CallAnimationFlag.AtNode(flag)
        has_with_node = CallAnimationFlag.WithNode(flag)
        has_translation = CallAnimationFlag.Translation(flag)
        has_rotation = CallAnimationFlag.Rotation(flag)

        if not has_translation:
            assert_eq("tx", 0.0, tx, reader.prev + 44)
            assert_eq("ty", 0.0, ty, reader.prev + 48)
            assert_eq("tz", 0.0, tz, reader.prev + 52)

        if not has_rotation:
            assert_eq("rx", 0.0, rx, reader.prev + 56)
            assert_eq("ry", 0.0, ry, reader.prev + 60)
            assert_eq("rz", 0.0, rz, reader.prev + 64)

        at_node: AtNodeFlex = None
        with_node = None
        if has_at_node:
            # when using AT_NODE, OPERAND_NODE can't be used
            assert_eq("operand node", 0, operand_index, reader.prev + 32)
            operand_node = None
            assert_eq("with node", False, has_with_node, reader.prev + 34)

            if node_index == 65336:
                node = INPUT_NODE
            else:
                node = anim_def.get_node(node_index - 1, reader.prev + 40)

            if has_rotation:
                at_node = AtNodeLong(
                    node=node, tx=tx, ty=ty, tz=tz, rx=rx, ry=ry, rz=rz
                )
            else:
                at_node = AtNodeShort(node=node, tx=tx, ty=ty, tz=tz)

        elif has_with_node:
            # when using WITH_NODE, OPERAND_NODE can't be used
            assert_eq("operand node", 0, operand_index, reader.prev + 32)
            operand_node = None
            assert_eq("has rotation", False, has_rotation, reader.prev + 34)

            # WITH_NODE doesn't seem to use INPUT_NODE
            node = anim_def.get_node(node_index - 1, reader.prev + 40)
            with_node = AtNodeShort(node=node, tx=tx, ty=ty, tz=tz)
        else:
            # otherwise, OPERAND_NODE may be used but doesn't need to be
            if operand_index < 1:
                assert_eq("operand node", 0, operand_index, reader.prev + 32)
                operand_node = None
            else:
                operand_node = anim_def.get_node(operand_index - 1, reader.prev + 32)
            assert_eq("node index", 0, node_index, reader.prev + 40)
            assert_eq("has translation", False, has_translation, reader.prev + 34)
            assert_eq("has rotation", False, has_rotation, reader.prev + 34)

        return cls(
            name=name,
            at_node=at_node,
            with_node=with_node,
            operand_node=operand_node,
            wait_for_completion=wait_for_completion,
        )

    def __repr__(self) -> str:
        at_node = f", AT_NODE={self.at_node!r}" if self.at_node else ""
        with_node = f", WITH_NODE={self.with_node!r}" if self.with_node else ""
        op_node = f", OPERAND_NODE={self.operand_node!r}" if self.operand_node else ""
        wait_for = (
            f", WAIT_FOR_COMPLETION={self.wait_for_completion}"
            if self.wait_for_completion > -1
            else ""
        )
        return (
            f"{self._NAME}(NAME={self.name!r}{at_node}{with_node}{op_node}{wait_for})"
        )


class StopAnimation(ScriptObject):
    _NAME: str = "STOP_ANIMATION"
    _NUMBER: int = 25
    _STRUCT: Struct = Struct("<32s i")

    name: str

    @classmethod
    def read(cls, reader: BinReader, _anim_def: AnimDef) -> StopAnimation:
        name_raw, sentinel = reader.read(cls._STRUCT)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        assert_eq("sentinel", 0, sentinel, reader.prev + 32)
        return cls(name=name)

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.name!r})"


class ResetAnimation(ScriptObject):
    _NAME: str = "RESET_ANIMATION"
    _NUMBER: int = 26
    _STRUCT: Struct = Struct("<32s i")

    name: str

    @classmethod
    def read(cls, reader: BinReader, _anim_def: AnimDef) -> ResetAnimation:
        name_raw, sentinel = reader.read(cls._STRUCT)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        assert_eq("sentinel", 0, sentinel, reader.prev + 0)
        return cls(name=name)

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.name!r})"


class InvalidateAnimation(ScriptObject):
    _NAME: str = "INVALIDATE_ANIMATION"
    _NUMBER: int = 27
    _STRUCT: Struct = Struct("<32s i")

    name: str

    @classmethod
    def read(cls, reader: BinReader, _anim_def: AnimDef) -> InvalidateAnimation:
        name_raw, sentinel = reader.read(cls._STRUCT)
        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        assert_eq("sentinel", 0, sentinel, reader.prev + 0)
        return cls(name=name)

    def __repr__(self) -> str:
        return f"{self._NAME}(NAME={self.name!r})"
