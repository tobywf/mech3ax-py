from __future__ import annotations

from enum import IntEnum
from struct import Struct
from typing import Any, Dict, List, Literal, Optional, Tuple, Type, TypeVar, Union

from pydantic import BaseModel, validator

from mech3ax.errors import assert_between, assert_eq
from mech3ax.serde import Base64

from ..utils import BinReader


class NamePtrFlag(BaseModel):
    name: str
    ptr: int = 0
    flag: int = 0


class NameRaw(BaseModel):
    name: str
    pad: Base64 = Base64(b"")


class StartOffset(IntEnum):
    Unset = 0
    Animation = 1
    Sequence = 2
    Event = 3


T = TypeVar("T", bound="ScriptObject")
OBJECT_REGISTRY_NUM: Dict[int, Type[ScriptObject]] = {}
OBJECT_REGISTRY_NAME: Dict[str, Type[ScriptObject]] = {}


class ScriptObject(BaseModel):
    # class attributes must begin with an underscore to work with pydantic
    _NAME: str
    _NUMBER: int
    _STRUCT: Struct

    @classmethod
    def read(cls: Type[T], reader: BinReader, anim_def: AnimDef) -> T:
        raise NotImplementedError

    @classmethod
    def validate_length(cls, reader: BinReader, actual_length: int) -> None:
        assert_eq(
            f"{cls._NAME} size", cls._STRUCT.size, actual_length, reader.prev + 4,
        )

    @classmethod
    def validate_and_read(
        cls: Type[T], reader: BinReader, anim_def: AnimDef, actual_length: int
    ) -> T:
        cls.validate_length(reader, actual_length)
        return cls.read(reader, anim_def)

    def __init_subclass__(cls) -> None:
        number = cls._NUMBER
        name = cls._NAME
        if number < 0 and not name:
            return

        try:
            existing = OBJECT_REGISTRY_NUM[number]
        except KeyError:
            try:
                existing = OBJECT_REGISTRY_NAME[name]
            except KeyError:
                OBJECT_REGISTRY_NUM[number] = cls
                OBJECT_REGISTRY_NAME[name] = cls
            else:
                raise ValueError(
                    f"{name!r} already registered to {type(existing)} for {type(cls)}"
                )
        else:
            raise ValueError(
                f"{number} already registered to {type(existing)} for {type(cls)}"
            )


class ScriptItem(BaseModel):
    name: str
    item: ScriptObject
    start_offset: StartOffset = StartOffset.Unset
    start_time: float = 0.0

    @validator("item", pre=True)
    @classmethod
    def validate_item(cls, value: Any, values: Dict[str, str]) -> ScriptObject:
        if isinstance(value, ScriptObject):
            return value
        if not isinstance(value, dict):
            raise ValueError("value must be dict")

        name = values["name"]
        try:
            base_model = OBJECT_REGISTRY_NAME[name]
        except KeyError:
            raise ValueError(f"unknown script item {name}")

        return base_model(**value)


SeqActivation = Union[Literal["NONE"], Literal["ON_CALL"]]


class SeqDef(BaseModel):
    activation: SeqActivation = "NONE"
    script: List[ScriptItem]
    ptr: int


class PrereqObject(BaseModel):
    required: bool
    active: bool
    name: str
    ptr: int
    parent_name: str = ""
    parent_ptr: int = 0


class ActivationPrereq(BaseModel):
    min_to_satisfy: int = 0
    anim_list: List[str] = []
    obj_list: List[PrereqObject] = []


AnimActivation = Union[
    Literal["WEAPON_HIT"],
    Literal["COLLIDE_HIT"],
    Literal["WEAPON_OR_COLLIDE_HIT"],
    Literal["ON_CALL"],
    Literal["ON_STARTUP"],
]

ANIM_ACTIVATION: List[AnimActivation] = [
    "WEAPON_HIT",
    "COLLIDE_HIT",
    "WEAPON_OR_COLLIDE_HIT",
    "ON_CALL",
    "ON_STARTUP",
]


class AnimDef(BaseModel):
    name: str
    anim_name: str
    anim_root: str

    reset_time: float = 0.0
    health: float = 0.0

    activation: AnimActivation
    execution_by_range: Tuple[float, float] = (0.0, 0.0)

    objects: List[NameRaw] = []
    nodes: List[NamePtrFlag] = []
    lights: List[NamePtrFlag] = []
    puffers: List[NamePtrFlag] = []
    dynamic_sounds: List[NamePtrFlag] = []
    static_sounds: List[NameRaw] = []
    activation_prereq: Optional[ActivationPrereq] = None
    anim_refs: List[NameRaw] = []
    reset_sequence: Optional[SeqDef] = None
    sequences: List[SeqDef] = []

    objects_ptr: int = 0
    nodes_ptr: int = 0
    lights_ptr: int = 0
    puffers_ptr: int = 0
    dynamic_sounds_ptr: int = 0
    static_sounds_ptr: int = 0
    activ_prereqs_ptr: int = 0
    anim_refs_ptr: int = 0
    reset_state_ptr: int = 0
    seq_defs_ptr: int = 0

    def get_node_or_input(self, index: int, offset: int) -> str:
        if index < 0:
            return "INPUT_NODE"
        return self.get_node(index, offset)

    def get_node(self, index: int, offset: int) -> str:
        max_index = len(self.nodes) - 1
        assert_between("node index", 0, max_index, index, offset)
        return self.nodes[index].name

    def get_light(self, index: int, offset: int) -> str:
        max_index = len(self.lights) - 1
        assert_between("light index", 0, max_index, index, offset)
        return self.lights[index].name

    def get_puffer(self, index: int, offset: int) -> str:
        max_index = len(self.puffers) - 1
        assert_between("puffer index", 0, max_index, index, offset)
        return self.puffers[index].name

    def get_sound(self, index: int, offset: int) -> str:
        max_index = len(self.static_sounds) - 1
        assert_between("sound index", 0, max_index, index, offset)
        return self.static_sounds[index].name


class AtNodeShort(BaseModel):
    node: str
    tx: float = 0.0
    ty: float = 0.0
    tz: float = 0.0

    def __repr__(self) -> str:
        if self.tx == 0.0 and self.ty == 0.0 and self.tz == 0.0:
            return f"({self.node!r})"
        return f"({self.node!r}, {self.tx}, {self.ty}, {self.tz})"

    @classmethod
    def from_index(  # pylint: disable=too-many-arguments
        cls, anim_def: AnimDef, index: int, tx: float, ty: float, tz: float, offset: int
    ) -> Optional[AtNodeShort]:
        if index == 0:
            return None

        node = anim_def.get_node(index - 1, offset)
        return cls(node=node, tx=tx, ty=ty, tz=tz)


class AtNodeLong(BaseModel):
    node: str
    tx: float = 0.0
    ty: float = 0.0
    tz: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    rz: float = 0.0

    def __repr__(self) -> str:
        if self.rx == 0.0 and self.ry == 0.0 and self.rz == 0.0:
            if self.tx == 0.0 and self.ty == 0.0 and self.tz == 0.0:
                return f"({self.node!r})"
            return f"({self.node!r}, {self.tx}, {self.ty}, {self.tz})"
        return f"({self.node!r}, {self.tx}, {self.ty}, {self.tz}, {self.rx}, {self.ry}, {self.rz})"

    @classmethod
    def from_index(  # pylint: disable=too-many-arguments
        cls,
        anim_def: AnimDef,
        index: int,
        tx: float,
        ty: float,
        tz: float,
        rx: float,
        ry: float,
        rz: float,
        offset: int,
    ) -> Optional[AtNodeLong]:
        if index == 0:
            return None

        if index > 100:  # TODO: use max node count
            node = "INPUT_NODE"
        else:
            node = anim_def.get_node_or_input(index - 1, offset)

        return cls(node=node, tx=tx, ty=ty, tz=tz, rx=rx, ry=ry, rz=rz)
