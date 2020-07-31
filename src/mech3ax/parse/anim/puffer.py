from __future__ import annotations

from struct import Struct
from typing import List, Optional, Tuple

from mech3ax.errors import assert_ascii, assert_eq, assert_ge, assert_in

from ..utils import BinReader, ascii_zterm_padded
from .models import AnimDef, AtNodeShort, ScriptObject

DUMMY_IMPORT = None


class PufferState(ScriptObject):
    _NAME: str = "PUFFER_STATE"
    _NUMBER: int = 42
    _STRUCT: Struct = Struct(
        "<32s I 2bh i I3f 6f 6f 3f If2f2f2ff2I2ff 4I 36s 36s 36s 36s 36s 36s 36s 36s 36s 5I 3f 8I"
    )

    name: str
    at_node: Optional[AtNodeShort] = None

    active_state: int = 0

    local_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    world_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    min_random_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    max_random_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    world_acceleration: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    is_distance_interval: bool = False
    interval: float = 0.0
    size_range: Tuple[float, float] = (0.0, 0.0)
    lifetime_range: Tuple[float, float] = (0.0, 0.0)
    start_age_range: Tuple[float, float] = (0.0, 0.0)
    deviation_distance: float = 0.0

    fade_range: Tuple[float, float] = (0.0, 0.0)
    friction: float = 0.0

    textures: List[str] = []

    growth_factor: float = 0.0

    unk: List[int] = []

    @classmethod
    def read(  # pylint: disable=too-many-locals,too-many-statements
        cls, reader: BinReader, anim_def: AnimDef
    ) -> PufferState:
        (
            name_raw,
            index,
            unk036,
            unk037,
            unk038,
            active_state,
            at_index,
            at_tx,
            at_ty,
            at_tz,
            local_velocity_x,
            local_velocity_y,
            local_velocity_z,
            world_velocity_x,
            world_velocity_y,
            world_velocity_z,
            min_random_velocity_x,
            min_random_velocity_y,
            min_random_velocity_z,
            max_random_velocity_x,
            max_random_velocity_y,
            max_random_velocity_z,
            world_acceleration_x,
            world_acceleration_y,
            world_acceleration_z,
            is_distance_interval,
            interval,
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
            tex408,
            tex444,
            tex480,
            zero516,
            zero520,
            zero524,
            unk528,
            zero532,
            unk536,
            unk540,
            growth_factor,
            zero548,
            zero552,
            zero556,
            zero560,
            zero564,
            zero568,
            zero572,
            zero576,
        ) = reader.read(cls._STRUCT)

        with assert_ascii("name", name_raw, reader.prev + 0):
            name = ascii_zterm_padded(name_raw)

        expected_name = anim_def.get_puffer(index - 1, reader.prev + 32)
        assert_eq("index name", expected_name, name, reader.prev + 32)

        assert_in("active_state", (-1, 1, 2, 3, 4, 5), active_state, reader.prev + 40)

        if active_state < 0:
            assert_in("field 036", (0, 4), unk036, reader.prev + 36)
            assert_eq("field 037", 0, unk037, reader.prev + 37)
            assert_eq("field 038", 0, unk038, reader.prev + 38)
        else:
            assert_in("field 038", (0, 2, 3), unk038, reader.prev + 38)

        at_node = AtNodeShort.from_index(
            anim_def, at_index, at_tx, at_ty, at_tz, reader.prev + 44
        )

        # 060, 064, 068
        local_velocity = (local_velocity_x, local_velocity_y, local_velocity_z)
        # 072, 076, 080
        world_velocity = (world_velocity_x, world_velocity_y, world_velocity_z)
        # 084, 088, 092
        min_random_velocity = (
            min_random_velocity_x,
            min_random_velocity_y,
            min_random_velocity_z,
        )
        # 096, 100, 104
        max_random_velocity = (
            max_random_velocity_x,
            max_random_velocity_y,
            max_random_velocity_z,
        )
        # 108, 112, 116
        world_acceleration = (
            world_acceleration_x,
            world_acceleration_y,
            world_acceleration_z,
        )

        assert_in("interval type", (0, 1), is_distance_interval, reader.prev + 120)
        assert_ge("interval", 0.0, interval, reader.prev + 124)

        assert_ge("size range min", 0.0, size_range_min, reader.prev + 128)
        assert_ge("size range max", size_range_min, size_range_max, reader.prev + 132)
        size_range = (size_range_min, size_range_max)

        assert_ge("lifetime range min", 0.0, lifetime_range_min, reader.prev + 136)
        assert_ge("lifetime range max", 0.0, lifetime_range_max, reader.prev + 140)
        lifetime_range = (lifetime_range_min, lifetime_range_max)

        assert_ge("lifetime range min", 0.0, start_age_range_min, reader.prev + 144)
        assert_ge(
            "lifetime range max",
            start_age_range_min,
            start_age_range_max,
            reader.prev + 148,
        )
        start_age_range = (start_age_range_min, start_age_range_max)

        assert_ge("deviation distance", 0.0, deviation_distance, reader.prev + 152)

        assert_eq("field 156", 0, zero156, reader.prev + 156)
        assert_eq("field 160", 0, zero160, reader.prev + 160)

        assert_ge("fade range min", 0.0, fade_range_min, reader.prev + 164)
        assert_ge("fade range max", fade_range_min, fade_range_max, reader.prev + 168)
        fade_range = (fade_range_min, fade_range_max)

        assert_ge("friction", 0.0, friction, reader.prev + 172)

        assert_eq("field 176", 0, zero176, reader.prev + 176)
        assert_eq("field 180", 0, zero180, reader.prev + 180)
        assert_eq("field 184", 0, zero184, reader.prev + 184)
        assert_eq("field 188", 0, zero188, reader.prev + 188)

        textures_raw = [
            tex192,
            tex228,
            tex264,
            tex300,
            tex336,
            tex372,
            tex408,
            tex444,
            tex480,
        ]

        textures: List[str] = []
        for i, texture_raw in enumerate(textures_raw):
            with assert_ascii("texture", name_raw, reader.prev + 192 + i * 36):
                texture = ascii_zterm_padded(texture_raw)
            if texture:
                textures.append(texture)

        assert_eq("field 516", 0, zero516, reader.prev + 516)
        assert_eq("field 520", 0, zero520, reader.prev + 520)
        assert_eq("field 524", 0, zero524, reader.prev + 524)
        assert_eq("field 532", 0, zero532, reader.prev + 532)

        if active_state < 0:
            assert_eq("field 528", 0, unk528, reader.prev + 528)
            assert_eq("field 536", 0.0, unk536, reader.prev + 536)
            assert_eq("field 540", 0.0, unk540, reader.prev + 540)
        else:
            assert_eq("field 528", 2, unk528, reader.prev + 528)
            assert_eq("field 536", 1.0, unk536, reader.prev + 536)
            assert_eq("field 540", 1.0, unk540, reader.prev + 540)

        assert_ge("growth factor", 0.0, growth_factor, reader.prev + 544)

        assert_eq("field 548", 0, zero548, reader.prev + 548)
        assert_eq("field 552", 0, zero552, reader.prev + 552)
        assert_eq("field 556", 0, zero556, reader.prev + 556)
        assert_eq("field 560", 0, zero560, reader.prev + 560)
        assert_eq("field 564", 0, zero564, reader.prev + 564)
        assert_eq("field 568", 0, zero568, reader.prev + 568)
        assert_eq("field 572", 0, zero572, reader.prev + 572)
        assert_eq("field 576", 0, zero576, reader.prev + 576)

        return cls(
            name=name,
            active_state=active_state,
            at_node=at_node,
            local_velocity=local_velocity,
            world_velocity=world_velocity,
            min_random_velocity=min_random_velocity,
            max_random_velocity=max_random_velocity,
            world_acceleration=world_acceleration,
            is_distance_interval=is_distance_interval == 1,
            interval=interval,
            size_range=size_range,
            lifetime_range=lifetime_range,
            start_age_range=start_age_range,
            deviation_distance=deviation_distance,
            fade_range=fade_range,
            friction=friction,
            growth_factor=growth_factor,
            unk=[unk036, unk037, unk038, active_state],
        )

    def __repr__(self) -> str:
        state_name = "INACTIVE" if self.active_state < 0 else "ACTIVE"
        interval_type = (
            "DISTANCE_INTERVAL" if self.is_distance_interval else "TIME_INTERVAL"
        )
        return "\n".join(
            [
                f"{self._NAME}(",
                f"  NAME={self.name!r},",
                f"  UNK={self.unk},",
                f"  ACTIVE_STATE={state_name},",
                f"  AT_NODE={self.at_node!r},",
                f"  {interval_type}={self.interval},",
                f"  LOCAL_VELOCITY={self.local_velocity},",
                f"  WORLD_VELOCITY={self.world_velocity},",
                f"  MIN_RANDOM_VELOCITY={self.min_random_velocity},",
                f"  MAX_RANDOM_VELOCITY={self.max_random_velocity},",
                f"  WORLD_ACCELERATION={self.world_acceleration},",
                f"  SIZE_RANGE={self.size_range},",
                f"  LIFETIME_RANGE={self.lifetime_range},",
                f"  START_AGE_RANGE={self.start_age_range},",
                f"  DEVIATION_DISTANCE={self.deviation_distance},",
                f"  FRICTION={self.friction},",
                f"  GROWTH_FACTOR={self.growth_factor},",
                f"  FADE_RANGE={self.fade_range},",
                f"  TEXTURES={self.textures},",
                ")",
            ]
        )
