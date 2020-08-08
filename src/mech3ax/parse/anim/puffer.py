from __future__ import annotations

from struct import Struct
from typing import List, Literal, Optional, Tuple, Union

from mech3ax.errors import (
    assert_all_zero,
    assert_ascii,
    assert_between,
    assert_eq,
    assert_flag,
    assert_ge,
    assert_gt,
    assert_in,
)

from ..int_flag import IntFlag
from ..utils import BinReader, ascii_zterm_padded
from .models import AnimDef, AtNodeShort, ScriptObject

DUMMY_IMPORT = None

IntervalType = Union[Literal["TIME"], Literal["DISTANCE"], Literal["UNSET"]]
Interval = Tuple[IntervalType, float, bool]

Vec2 = Tuple[float, float]
Vec3 = Tuple[float, float, float]


class PufferFlag(IntFlag):
    Inactive = 0
    Translate = 1 << 0
    GrowthFactor = 1 << 1
    State = 1 << 2
    LocalVelocity = 1 << 3
    WorldVelocity = 1 << 4
    MinRandomVelocity = 1 << 5
    MaxRandomVelocity = 1 << 6
    IntervalType = 1 << 7
    IntervalValue = 1 << 8
    SizeRange = 1 << 9
    LifetimeRange = 1 << 10
    DeviationDistance = 1 << 11
    FadeRange = 1 << 12
    Active = 1 << 13
    CycleTexture = 1 << 14
    StartAgeRange = 1 << 15
    WorldAcceleration = 1 << 16
    Friction = 1 << 17


class PufferState(ScriptObject):
    _NAME: str = "PUFFER_STATE"
    _NUMBER: int = 42
    _STRUCT: Struct = Struct(
        "<32s 2I i I3f 6f 6f 3f If2f2f2ff2I2ff 4I 36s 36s 36s 36s 36s 36s 120s 2I 3f 32s"
    )

    name: str
    puffer_state: bool = True
    active_state: int = 0

    at_node: Optional[AtNodeShort] = None

    local_velocity: Optional[Vec3] = None
    world_velocity: Optional[Vec3] = None

    min_random_velocity: Optional[Vec3] = None
    max_random_velocity: Optional[Vec3] = None
    world_acceleration: Optional[Vec3] = None

    interval: Interval
    size_range: Optional[Vec2] = None
    lifetime_range: Optional[Vec2] = None
    start_age_range: Optional[Vec2] = None
    deviation_distance: Optional[float] = None

    fade_range: Optional[Vec2] = None
    friction: Optional[float] = None

    textures: Optional[List[str]] = None

    growth_factor: Optional[float] = None

    @classmethod
    def read(  # pylint: disable=too-many-locals,too-many-statements,too-many-branches
        cls, reader: BinReader, anim_def: AnimDef
    ) -> PufferState:
        (
            name_raw,
            puffer_index,
            flag_raw,
            active_state,
            node_index,
            tx,
            ty,
            tz,
            local_vel_x,
            local_vel_y,
            local_vel_z,
            world_vel_x,
            world_vel_y,
            world_vel_z,
            min_random_vel_x,
            min_random_vel_y,
            min_random_vel_z,
            max_random_vel_x,
            max_random_vel_y,
            max_random_vel_z,
            world_accel_x,
            world_accel_y,
            world_accel_z,
            interval_type_raw,
            interval_value,
            size_range_min,
            size_range_max,
            lifetime_range_min,
            lifetime_range_max,
            start_age_range_min,
            start_age_range_max,
            deviation_distance,
            zero156,
            zero160,
            fade_range_min,
            fade_range_max,
            friction,
            zero176,
            zero180,
            zero184,
            zero188,
            tex192,
            tex228,
            tex264,
            tex300,
            tex336,
            tex372,
            zero408,  # 120 zero bytes
            unk528,
            zero532,
            unk536,
            unk540,
            growth_factor,
            zero548,  # 32 zero bytes
        ) = reader.read(cls._STRUCT)

        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        expected_name = anim_def.get_puffer(puffer_index - 1, reader.prev + 32)
        assert_eq("index name", expected_name, name, reader.prev + 32)

        with assert_flag("flag", flag_raw, reader.prev + 36):
            flag = PufferFlag.check(flag_raw)

        puffer_state = PufferFlag.State(flag)
        if not puffer_state:
            # if the puffer state is disabled/inactive, then nothing else may be
            # specified. this ensures all further branches check for zero values.
            assert_eq("flag", 0, flag_raw, reader.prev + 36)

        if not PufferFlag.Active(flag):
            assert_eq("active state", -1, active_state, reader.prev + 40)
        else:
            assert_between("active state", 1, 5, active_state, reader.prev + 40)

        if node_index == 0:
            at_node = None
        else:
            node = anim_def.get_node(node_index - 1, reader.prev + 44)
            at_node = AtNodeShort(node=node, tx=tx, ty=ty, tz=tz)

        if not PufferFlag.LocalVelocity(flag):
            assert_eq("local vel x", 0.0, local_vel_x, reader.prev + 60)
            assert_eq("local vel y", 0.0, local_vel_y, reader.prev + 64)
            assert_eq("local vel z", 0.0, local_vel_z, reader.prev + 68)
            local_velocity = None
        else:
            local_velocity = (local_vel_x, local_vel_y, local_vel_z)

        if not PufferFlag.WorldVelocity(flag):
            assert_eq("world vel x", 0.0, world_vel_x, reader.prev + 72)
            assert_eq("world vel y", 0.0, world_vel_y, reader.prev + 76)
            assert_eq("world vel z", 0.0, world_vel_z, reader.prev + 80)
            world_velocity = None
        else:
            world_velocity = (world_vel_x, world_vel_y, world_vel_z)

        if not PufferFlag.MinRandomVelocity(flag):
            assert_eq("min rnd vel x", 0.0, min_random_vel_x, reader.prev + 84)
            assert_eq("min rnd vel y", 0.0, min_random_vel_y, reader.prev + 88)
            assert_eq("min rnd vel z", 0.0, min_random_vel_z, reader.prev + 92)
            min_random_velocity = None
        else:
            min_random_velocity = (
                min_random_vel_x,
                min_random_vel_y,
                min_random_vel_z,
            )

        if not PufferFlag.MaxRandomVelocity(flag):
            assert_eq("max rnd vel x", 0.0, max_random_vel_x, reader.prev + 96)
            assert_eq("max rnd vel y", 0.0, max_random_vel_y, reader.prev + 100)
            assert_eq("max rnd vel z", 0.0, max_random_vel_z, reader.prev + 104)
            max_random_velocity = None
        else:
            max_random_velocity = (
                max_random_vel_x,
                max_random_vel_y,
                max_random_vel_z,
            )

        if not PufferFlag.WorldAcceleration(flag):
            assert_eq("world accel x", 0.0, world_accel_x, reader.prev + 108)
            assert_eq("world accel y", 0.0, world_accel_y, reader.prev + 112)
            assert_eq("world accel z", 0.0, world_accel_z, reader.prev + 116)
            world_acceleration = None
        else:
            world_acceleration = (
                world_accel_x,
                world_accel_y,
                world_accel_z,
            )

        if not PufferFlag.IntervalType(flag):
            assert_eq("interval type", 0, interval_type_raw, reader.prev + 120)
            interval_type: IntervalType = "UNSET"
        else:
            assert_in("interval type", (0, 1), interval_type_raw, reader.prev + 120)
            if interval_type_raw == 1:
                interval_type = "DISTANCE"
            else:
                interval_type = "TIME"

        # does not obey the flag
        assert_ge("interval value", 0.0, interval_value, reader.prev + 124)
        interval = (interval_type, interval_value, PufferFlag.IntervalValue(flag))

        if not PufferFlag.SizeRange(flag):
            assert_eq("size range min", 0.0, size_range_min, reader.prev + 128)
            assert_eq("size range max", 0.0, size_range_max, reader.prev + 132)
            size_range = None
        else:
            assert_gt("size range min", 0.0, size_range_min, reader.prev + 128)
            assert_gt(
                "size range max", size_range_min, size_range_max, reader.prev + 132
            )
            size_range = (size_range_min, size_range_max)

        if not PufferFlag.LifetimeRange(flag):
            assert_eq("lifetime range min", 0.0, lifetime_range_min, reader.prev + 136)
            assert_eq("lifetime range max", 0.0, lifetime_range_max, reader.prev + 140)
            lifetime_range = None
        else:
            assert_gt("lifetime range min", 0.0, lifetime_range_min, reader.prev + 136)
            assert_gt("lifetime range max", 0.0, lifetime_range_max, reader.prev + 140)
            # does not obey ordering
            lifetime_range = (lifetime_range_min, lifetime_range_max)

        if not PufferFlag.StartAgeRange(flag):
            assert_eq(
                "start age range min", 0.0, start_age_range_min, reader.prev + 144
            )
            assert_eq(
                "start age range max", 0.0, start_age_range_max, reader.prev + 148,
            )
            start_age_range = None
        else:
            assert_ge(
                "start age range min", 0.0, start_age_range_min, reader.prev + 144
            )
            assert_gt(
                "start age range max",
                start_age_range_min,
                start_age_range_max,
                reader.prev + 148,
            )
            start_age_range = (start_age_range_min, start_age_range_max)

        if not PufferFlag.DeviationDistance(flag):
            assert_eq("deviation distance", 0.0, deviation_distance, reader.prev + 152)
            deviation_distance = None
        else:
            assert_gt("deviation distance", 0.0, deviation_distance, reader.prev + 152)

        assert_eq("field 156", 0, zero156, reader.prev + 156)
        assert_eq("field 160", 0, zero160, reader.prev + 160)

        if not PufferFlag.FadeRange(flag):
            assert_eq("fade range min", 0.0, fade_range_min, reader.prev + 164)
            assert_eq("fade range max", 0.0, fade_range_max, reader.prev + 168)
            fade_range = None
        else:
            assert_gt("fade range min", 0.0, fade_range_min, reader.prev + 164)
            assert_gt(
                "fade range max", fade_range_min, fade_range_max, reader.prev + 168
            )
            fade_range = (fade_range_min, fade_range_max)

        if not PufferFlag.Friction(flag):
            assert_eq("friction", 0.0, friction, reader.prev + 172)
            friction = None
        else:
            assert_ge("friction", 0.0, friction, reader.prev + 172)

        assert_eq("field 176", 0, zero176, reader.prev + 176)
        assert_eq("field 180", 0, zero180, reader.prev + 180)
        assert_eq("field 184", 0, zero184, reader.prev + 184)
        assert_eq("field 188", 0, zero188, reader.prev + 188)

        if not PufferFlag.CycleTexture(flag):
            assert_all_zero("texture 1", tex192, reader.prev + 192)
            assert_all_zero("texture 2", tex228, reader.prev + 228)
            assert_all_zero("texture 3", tex264, reader.prev + 264)
            assert_all_zero("texture 4", tex300, reader.prev + 300)
            assert_all_zero("texture 5", tex336, reader.prev + 336)
            assert_all_zero("texture 6", tex372, reader.prev + 372)
            textures: Optional[List[str]] = None
        else:
            textures_raw = [
                tex192,
                tex228,
                tex264,
                tex300,
                tex336,
                tex372,
            ]

            textures = []
            for i, texture_raw in enumerate(textures_raw):
                with assert_ascii("texture", texture_raw, reader.prev + 192 + i * 36):
                    texture = ascii_zterm_padded(texture_raw)
                if texture:
                    textures.append(texture)

        # 120 zero bytes
        assert_all_zero("field 408", zero408, reader.prev + 408)

        assert_eq("field 532", 0, zero532, reader.prev + 532)
        if not PufferFlag.Active(flag):
            assert_eq("field 528", 0, unk528, reader.prev + 528)
            assert_eq("field 536", 0.0, unk536, reader.prev + 536)
            assert_eq("field 540", 0.0, unk540, reader.prev + 540)
        else:
            assert_eq("field 528", 2, unk528, reader.prev + 528)
            assert_eq("field 536", 1.0, unk536, reader.prev + 536)
            assert_eq("field 540", 1.0, unk540, reader.prev + 540)

        if not PufferFlag.GrowthFactor(flag):
            assert_eq("growth factor", 0.0, growth_factor, reader.prev + 544)
            growth_factor = None
        else:
            assert_gt("growth factor", 0.0, growth_factor, reader.prev + 544)

        # 32 zero bytes
        assert_all_zero("field 548", zero548, reader.prev + 548)

        return cls(
            name=name,
            puffer_state=puffer_state,
            active_state=active_state,
            at_node=at_node,
            local_velocity=local_velocity,
            world_velocity=world_velocity,
            min_random_velocity=min_random_velocity,
            max_random_velocity=max_random_velocity,
            world_acceleration=world_acceleration,
            interval=interval,
            size_range=size_range,
            lifetime_range=lifetime_range,
            start_age_range=start_age_range,
            deviation_distance=deviation_distance,
            fade_range=fade_range,
            friction=friction,
            textures=textures,
            growth_factor=growth_factor,
        )
