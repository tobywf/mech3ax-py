from functools import wraps
from math import tan
from typing import BinaryIO, Callable, Dict, List, Type, TypeVar

from mech3ax.errors import Mech3NodeError, assert_eq
from mech3ax.serde import NodeType

from ..float import approx_sqrt, euler_to_matrix
from ..utils import UINT32
from .models import (
    CAMERA,
    DISPLAY,
    IDENTITY_MATRIX,
    LEVEL_OF_DETAIL,
    LIGHT,
    LIGHT_FLAG,
    OBJECT3D,
    PARTITION,
    WINDOW,
    WORLD,
    Camera,
    Display,
    LevelOfDetail,
    Light,
    NodeData,
    Object3d,
    Partition,
    Window,
    World,
)
from .sign import apply_zero_signs

_T = TypeVar("_T")

WriteNodeDataAny = Callable[[BinaryIO, NodeData], None]
WriteNodeDataT = Callable[[BinaryIO, _T], None]
WRITE_NODE_DATA: Dict[NodeType, WriteNodeDataAny] = {}


def _write_node_data(
    node_type: NodeType, node_data: Type[_T]
) -> Callable[[WriteNodeDataT[_T]], WriteNodeDataAny]:
    def _wrap(func: WriteNodeDataT[_T]) -> WriteNodeDataAny:
        @wraps(func)
        def wrapper(f: BinaryIO, node: NodeData) -> None:
            if not isinstance(node, node_data):  # pragma: no cover
                raise Mech3NodeError(f"Expected {node_data!r}, but got {type(node)!r}")
            func(f, node)

        WRITE_NODE_DATA[node_type] = wrapper
        return wrapper

    return _wrap


@_write_node_data(NodeType.Camera, Camera)
def _write_node_data_camera(f: BinaryIO, camera: Camera) -> None:
    clip_near_z, clip_far_z = camera.clip
    fov_h, fov_v = camera.fov

    fov_h_half = fov_h / 2.0
    fov_v_half = fov_v / 2.0

    data = CAMERA.pack(
        0,  # world_index
        1,  # window_index
        -1,  # focus_node_xy
        -1,  # focus_node_xz
        0,  # flag_raw
        0.0,  # trans_x
        0.0,  # trans_y
        0.0,  # trans_z
        0.0,  # rot_x
        0.0,  # rot_y
        0.0,  # rot_z
        b"",
        clip_near_z,
        clip_far_z,
        b"",
        1.0,  # lod_multiplier
        1.0,  # lod_inv_sq
        1.0,  # fov_h_zoom_factor
        1.0,  # fov_v_zoom_factor
        fov_h,  # fov_h_base
        fov_v,  # fov_v_base
        fov_h,
        fov_v,
        fov_h_half,
        fov_v_half,
        1,  # one248
        b"",
        1,  # one312
        b"",
        1,  # one388
        b"",
        0,  # zero464
        1.0 / tan(fov_h_half),
        1.0 / tan(fov_v_half),
        0,  # stride
        0,  # zone_set
        -256,  # unk484
    )
    f.write(data)


def _write_partitions(f: BinaryIO, partitions: List[List[Partition]]) -> None:
    for subpartition in partitions:
        for partition in subpartition:
            x = partition.x
            y = partition.y
            unk20, unk32, unk44 = partition.unk
            temp = (unk32 - unk20) * 0.5
            unk52 = approx_sqrt(128 * 128 + temp * temp + 128 * 128)
            data = PARTITION.pack(
                0x100,  # flag_raw
                -1,  # mone04
                x,
                y,
                x,  # unk16
                unk20,
                y - 256,  # unk24
                x + 256,  # unk28
                unk32,
                y,  # unk36
                x + 128,  # unk40
                unk44,
                y - 128,  # unk48
                unk52,
                0,  # zero56
                len(partition.nodes),
                partition.ptr,
                0,  # zero64
                0,  # zero68
            )
            f.write(data)

            for node in partition.nodes:
                f.write(UINT32.pack(node))


@_write_node_data(NodeType.World, World)
def _write_node_data_world(f: BinaryIO, world: World) -> None:
    area_left, area_top, area_right, area_bottom = world.area
    area_width = area_right - area_left
    area_height = area_top - area_bottom

    area_partition_count = world.area_partition_x_count * world.area_partition_y_count

    data = WORLD.pack(
        0,  # flag_raw
        0,  # area_partition_used
        area_partition_count - (1 if world.fudge_count else 0),
        world.area_partition_ptr,
        1,  # fog_state_raw
        0.0,  # fog_color_r
        0.0,  # fog_color_g
        0.0,  # fog_color_b
        0.0,  # fog_range_near
        0.0,  # fog_range_far
        0.0,  # fog_alti_high
        0.0,  # fog_alti_low
        0.0,  # fog_density
        area_left,
        area_bottom,
        area_width,
        area_height,
        area_right,
        area_top,
        16,  # partition_max_dec_feature_count
        1,  # virtual_partition
        1,  # virt_partition_x_min
        1,  # virt_partition_y_min
        world.area_partition_x_count - 1,  # virt_partition_x_max
        world.area_partition_y_count - 1,  # virt_partition_y_max
        256.0,  # virt_partition_x_size
        -256.0,  # virt_partition_y_size
        128.0,  # virt_partition_x_half
        -128.0,  # virt_partition_y_half
        1.0 / 256.0,  # virt_partition_x_inv
        1.0 / -256.0,  # virt_partition_y_inv
        -192.0,  # virt_partition_diag
        3.0,  # partition_inclusion_tol_low
        3.0,  # partition_inclusion_tol_high
        world.area_partition_x_count,  # virt_partition_x_count
        world.area_partition_y_count,  # virt_partition_y_count
        world.virt_partition_ptr,
        1.0,  # one148
        1.0,  # one152
        1.0,  # one156
        1,  # children_count
        world.children_ptr,
        world.lights_ptr,
        0,  # zero172
        0,  # zero176
        0,  # zero180
        0,  # zero184
    )
    f.write(data)

    assert_eq("children count", 1, len(world.children), "world1")
    f.write(UINT32.pack(world.children[0]))

    _write_partitions(f, world.partitions)


@_write_node_data(NodeType.Window, Window)
def _write_node_data_window(f: BinaryIO, window: Window) -> None:
    resolution_x, resolution_y = window.resolution
    data = WINDOW.pack(
        0,  # origin_x
        0,  # origin_y
        resolution_x,
        resolution_y,
        b"",
        -1,  # buffer_index
        0,  # buffer_ptr
        0,  # zero236
        0,  # zero240
        0,  # zero244
    )
    f.write(data)


@_write_node_data(NodeType.Display, Display)
def _write_node_data_display(f: BinaryIO, display: Display) -> None:
    resolution_x, resolution_y = display.resolution
    clear_color_r, clear_color_g, clear_color_b = display.clear_color
    data = DISPLAY.pack(
        0,  # origin_x
        0,  # origin_y
        resolution_x,
        resolution_y,
        clear_color_r,
        clear_color_g,
        clear_color_b,
    )
    f.write(data)


def write_node_data_object3d(f: BinaryIO, object3d: Object3d) -> None:
    if object3d.rotation and object3d.translation:
        rot_x, rot_y, rot_z = object3d.rotation
        trans_x, trans_y, trans_z = object3d.translation
        if object3d.matrix:
            # in this case, we have the raw matrix with the correct zero signs
            matrix = object3d.matrix
        else:
            matrix = euler_to_matrix(rot_x, rot_y, rot_z)
            matrix = apply_zero_signs(object3d.matrix_sign, matrix)
        flag_raw = 32
    else:
        rot_x = rot_y = rot_z = 0.0
        trans_x = trans_y = trans_z = 0.0
        matrix = apply_zero_signs(object3d.matrix_sign, IDENTITY_MATRIX)
        flag_raw = 40

    data = OBJECT3D.pack(
        flag_raw,
        # opacity
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        rot_x,
        rot_y,
        rot_z,
        # scale
        1.0,
        1.0,
        1.0,
        *matrix,
        trans_x,
        trans_y,
        trans_z,
        b"",
    )
    f.write(data)


@_write_node_data(NodeType.Object3D, Object3d)
def _write_node_data_object3d(f: BinaryIO, object3d: Object3d) -> None:
    write_node_data_object3d(f, object3d)


@_write_node_data(NodeType.LOD, LevelOfDetail)
def _write_node_data_lod(f: BinaryIO, lod: LevelOfDetail) -> None:
    level = 1 if lod.level else 0
    range_near, range_far = lod.range
    data = LEVEL_OF_DETAIL.pack(
        level,
        range_near * range_near,
        range_far,
        range_far * range_far,
        b"",
        lod.unk60,
        lod.unk60 * lod.unk60,
        1,  # one68
        1 if lod.unk76 else 0,
        lod.unk76,
    )
    f.write(data)


@_write_node_data(NodeType.Light, Light)
def _write_node_data_light(f: BinaryIO, light: Light) -> None:
    direction_x, direction_y, direction_z = light.direction
    color_r, color_g, color_b = light.color
    range_min, range_max = light.range
    data = LIGHT.pack(
        direction_x,
        direction_y,
        direction_z,
        0.0,  # trans_x
        0.0,  # trans_y
        0.0,  # trans_z
        b"",
        1.0,  # one136
        0.0,  # zero140
        0.0,  # zero144
        0.0,  # zero148
        0.0,  # zero152
        light.diffuse,
        light.ambient,
        color_r,
        color_g,
        color_b,
        LIGHT_FLAG,
        range_min,
        range_max,
        range_min * range_min,
        range_max * range_max,
        1.0 / (range_max - range_min),
        1,
        light.parent_ptr,
        0,  # zero208
    )
    f.write(data)


assert WRITE_NODE_DATA.keys() == (set(NodeType) - {NodeType.Empty})
