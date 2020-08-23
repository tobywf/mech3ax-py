from functools import wraps
from typing import Callable, Dict, Type, TypeVar

from mech3ax.errors import Mech3NodeError
from mech3ax.serde import NodeType

from .models import (
    CAMERA,
    DISPLAY,
    LEVEL_OF_DETAIL,
    LIGHT,
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
    Window,
    World,
)

_T = TypeVar("_T")

SizeNodeDataAny = Callable[[NodeData], int]
SizeNodeDataT = Callable[[_T], int]
SIZE_NODE_DATA: Dict[NodeType, SizeNodeDataAny] = {}


def _size_node_data(
    node_type: NodeType, node_data: Type[_T]
) -> Callable[[SizeNodeDataT[_T]], SizeNodeDataAny]:
    def _wrap(func: SizeNodeDataT[_T]) -> SizeNodeDataAny:
        @wraps(func)
        def wrapper(node: NodeData) -> int:
            if not isinstance(node, node_data):  # pragma: no cover
                raise Mech3NodeError(f"Expected {node_data!r}, but got {type(node)!r}")
            return func(node)

        SIZE_NODE_DATA[node_type] = wrapper
        return wrapper

    return _wrap


@_size_node_data(NodeType.Camera, Camera)
def _size_node_data_camera(_camera: Camera) -> int:
    return CAMERA.size


@_size_node_data(NodeType.World, World)
def _size_node_data_world(world: World) -> int:
    partition_count = world.area_partition_x_count * world.area_partition_y_count
    item_count = 0
    for subpartition in world.partitions:
        for partition in subpartition:
            item_count += len(partition.nodes)

    return WORLD.size + 4 + PARTITION.size * partition_count + 4 * item_count


@_size_node_data(NodeType.Window, Window)
def _size_node_data_window(_window: Window) -> int:
    return WINDOW.size


@_size_node_data(NodeType.Display, Display)
def _size_node_data_display(_display: Display) -> int:
    return DISPLAY.size


@_size_node_data(NodeType.Object3D, Object3d)
def _size_node_data_object3d(_object3d: Object3d) -> int:
    return OBJECT3D.size


@_size_node_data(NodeType.LOD, LevelOfDetail)
def _size_node_data_lod(_lod: LevelOfDetail) -> int:
    return LEVEL_OF_DETAIL.size


@_size_node_data(NodeType.Light, Light)
def _size_node_data_light(_light: Light) -> int:
    return LIGHT.size


assert SIZE_NODE_DATA.keys() == (set(NodeType) - {NodeType.Empty})
