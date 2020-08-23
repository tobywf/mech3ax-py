from typing import Callable, Dict

from mech3ax.errors import assert_between, assert_eq, assert_in, assert_ne
from mech3ax.serde import NodeType

from .models import NODE_FLAG_BASE, NODE_FLAG_DEFAULT, Node, NodeFlag

AssertNode = Callable[[Node, int, int], None]
ASSERT_NODE_INFO: Dict[NodeType, AssertNode] = {}

BLOCK_EMPTY = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
BLOCK_LIGHT = (1.0, 1.0, -2.0, 2.0, 2.0, -1.0)
ZONE_DEFAULT = 255


def _assert_node(node_type: NodeType) -> Callable[[AssertNode], AssertNode]:
    def _wrap(f: AssertNode) -> AssertNode:
        ASSERT_NODE_INFO[node_type] = f
        return f

    return _wrap


@_assert_node(NodeType.Empty)
def _assert_node_info_empty(node: Node, offset: int, _mesh_count: int) -> None:
    # cannot assert name
    # these values are always set
    flag_base = node.flag & NODE_FLAG_BASE
    assert_eq("flag base", NODE_FLAG_BASE, flag_base, offset + 36)
    # flag?

    assert_in("field 044", (1, 3, 5, 7), node.unk044, offset + 44)
    assert_in("zone id", (1, ZONE_DEFAULT), node.zone_id, offset + 48)
    assert_eq("data ptr", 0, node.data_ptr, offset + 56)
    assert_eq("mesh index", -1, node.mesh_index, offset + 60)
    assert_eq("area partition x", -1, node.area_partition_x, offset + 76)
    assert_eq("area partition y", -1, node.area_partition_y, offset + 80)
    assert_eq("parent count", 0, node.parent_count, offset + 84)
    assert_eq("parent array ptr", 0, node.parent_array_ptr, offset + 88)
    assert_eq("children count", 0, node.children_count, offset + 92)
    assert_eq("children array ptr", 0, node.children_array_ptr, offset + 96)

    # unknowns are not 0.0

    assert_eq("field 196", 160, node.unk196, offset + 196)


@_assert_node(NodeType.Camera)
def _assert_node_info_camera(node: Node, offset: int, _mesh_count: int) -> None:
    assert_eq("name", "camera1", node.name, offset + 0)
    assert_eq("flag", NODE_FLAG_DEFAULT, node.flag, offset + 36)
    assert_eq("field 044", 0, node.unk044, offset + 44)
    assert_eq("zone id", ZONE_DEFAULT, node.zone_id, offset + 48)
    assert_ne("data ptr", 0, node.data_ptr, offset + 56)
    assert_eq("mesh index", -1, node.mesh_index, offset + 60)
    assert_eq("area partition x", -1, node.area_partition_x, offset + 76)
    assert_eq("area partition y", -1, node.area_partition_y, offset + 80)
    assert_eq("parent count", 0, node.parent_count, offset + 84)
    assert_eq("parent array ptr", 0, node.parent_array_ptr, offset + 88)
    assert_eq("children count", 0, node.children_count, offset + 92)
    assert_eq("children array ptr", 0, node.children_array_ptr, offset + 96)
    assert_eq("block 1", BLOCK_EMPTY, node.block1, offset + 116)
    assert_eq("block 2", BLOCK_EMPTY, node.block2, offset + 140)
    assert_eq("block 3", BLOCK_EMPTY, node.block3, offset + 164)
    assert_eq("field 196", 0, node.unk196, offset + 196)


@_assert_node(NodeType.World)
def _assert_node_info_world(node: Node, offset: int, _mesh_count: int) -> None:
    assert_eq("name", "world1", node.name, offset + 0)
    assert_eq("flag", NODE_FLAG_DEFAULT, node.flag, offset + 36)
    assert_eq("field 044", 0, node.unk044, offset + 44)
    assert_eq("zone id", ZONE_DEFAULT, node.zone_id, offset + 48)
    assert_ne("data ptr", 0, node.data_ptr, offset + 56)
    assert_eq("mesh index", -1, node.mesh_index, offset + 60)
    assert_eq("area partition x", -1, node.area_partition_x, offset + 76)
    assert_eq("area partition y", -1, node.area_partition_y, offset + 80)
    assert_eq("parent count", 0, node.parent_count, offset + 84)
    assert_eq("parent array ptr", 0, node.parent_array_ptr, offset + 88)
    # must have at least one child, upper bound is arbitrary
    assert_between("children count", 1, 64, node.children_count, offset + 92)
    assert_ne("children array ptr", 0, node.children_array_ptr, offset + 96)
    assert_eq("block 1", BLOCK_EMPTY, node.block1, offset + 116)
    assert_eq("block 2", BLOCK_EMPTY, node.block2, offset + 140)
    assert_eq("block 3", BLOCK_EMPTY, node.block3, offset + 164)
    assert_eq("field 196", 0, node.unk196, offset + 196)


@_assert_node(NodeType.Window)
def _assert_node_info_window(node: Node, offset: int, _mesh_count: int) -> None:
    assert_eq("name", "window1", node.name, offset + 0)
    assert_eq("flag", NODE_FLAG_DEFAULT, node.flag, offset + 36)
    assert_eq("field 044", 0, node.unk044, offset + 44)
    assert_eq("zone id", ZONE_DEFAULT, node.zone_id, offset + 48)
    assert_ne("data ptr", 0, node.data_ptr, offset + 56)
    assert_eq("mesh index", -1, node.mesh_index, offset + 60)
    assert_eq("area partition x", -1, node.area_partition_x, offset + 76)
    assert_eq("area partition y", -1, node.area_partition_y, offset + 80)
    assert_eq("parent count", 0, node.parent_count, offset + 84)
    assert_eq("parent array ptr", 0, node.parent_array_ptr, offset + 88)
    assert_eq("children count", 0, node.children_count, offset + 92)
    assert_eq("children array ptr", 0, node.children_array_ptr, offset + 96)
    assert_eq("block 1", BLOCK_EMPTY, node.block1, offset + 116)
    assert_eq("block 2", BLOCK_EMPTY, node.block2, offset + 140)
    assert_eq("block 3", BLOCK_EMPTY, node.block3, offset + 164)
    assert_eq("field 196", 0, node.unk196, offset + 196)


@_assert_node(NodeType.Display)
def _assert_node_info_display(node: Node, offset: int, _mesh_count: int) -> None:
    assert_eq("name", "display", node.name, offset + 0)
    assert_eq("flag", NODE_FLAG_DEFAULT, node.flag, offset + 36)
    assert_eq("field 044", 0, node.unk044, offset + 44)
    assert_eq("zone id", ZONE_DEFAULT, node.zone_id, offset + 48)
    assert_ne("data ptr", 0, node.data_ptr, offset + 56)
    assert_eq("mesh index", -1, node.mesh_index, offset + 60)
    assert_eq("area partition x", -1, node.area_partition_x, offset + 76)
    assert_eq("area partition y", -1, node.area_partition_y, offset + 80)
    assert_eq("parent count", 0, node.parent_count, offset + 84)
    assert_eq("parent array ptr", 0, node.parent_array_ptr, offset + 88)
    assert_eq("children count", 0, node.children_count, offset + 92)
    assert_eq("children array ptr", 0, node.children_array_ptr, offset + 96)
    assert_eq("block 1", BLOCK_EMPTY, node.block1, offset + 116)
    assert_eq("block 2", BLOCK_EMPTY, node.block2, offset + 140)
    assert_eq("block 3", BLOCK_EMPTY, node.block3, offset + 164)
    assert_eq("field 196", 0, node.unk196, offset + 196)


@_assert_node(NodeType.Object3D)
def _assert_node_info_object3d(node: Node, offset: int, mesh_count: int) -> None:
    # cannot assert name
    # these values are always set
    flag_base = node.flag & NODE_FLAG_BASE
    assert_eq("flag base", NODE_FLAG_BASE, flag_base, offset + 36)
    # TODO: flag?

    assert_eq("field 044", 1, node.unk044, offset + 44)
    if node.zone_id != ZONE_DEFAULT:
        assert_between("zone id", 1, 80, node.zone_id, offset + 48)
    assert_ne("data ptr", 0, node.data_ptr, offset + 56)

    if node.flag & NodeFlag.HasMesh != 0:
        assert_between("mesh index", 0, mesh_count, node.mesh_index, offset + 60)
    else:
        assert_eq("mesh index", -1, node.mesh_index, offset + 60)

    # assert area partition properly once we have read the world data
    assert_between("area partition x", -1, 64, node.area_partition_x, offset + 76)
    assert_between("area partition y", -1, 64, node.area_partition_y, offset + 80)

    # can only have one parent
    assert_in("parent count", (0, 1), node.parent_count, offset + 84)
    if node.parent_count:
        assert_ne("parent array ptr", 0, node.parent_array_ptr, offset + 88)
    else:
        assert_eq("parent array ptr", 0, node.parent_array_ptr, offset + 88)

    assert_between("children count", 0, 64, node.children_count, offset + 92)
    if node.children_count:
        assert_ne("children array ptr", 0, node.children_array_ptr, offset + 96)
    else:
        assert_eq("children array ptr", 0, node.children_array_ptr, offset + 96)

    # unknowns are not 0.0

    assert_eq("field 196", 160, node.unk196, offset + 196)


NODE_FLAG_LOD_BASE = NODE_FLAG_DEFAULT | NodeFlag.Unk10 | NodeFlag.Unk08


@_assert_node(NodeType.LOD)
def _assert_node_info_lod(node: Node, offset: int, _mesh_count: int) -> None:
    # cannot assert name
    # these values are always set
    flag_base = node.flag & NODE_FLAG_BASE
    assert_eq("flag base", NODE_FLAG_BASE, flag_base, offset + 36)
    # TODO:
    # flag_lod_base = node.flag & NODE_FLAG_LOD_BASE
    # assert_eq("flag lod base", NODE_FLAG_LOD_BASE, flag_lod_base, offset + 36)
    # # the only variable flag is Unk15
    # flag_lod_mask = node.flag & ~NODE_FLAG_LOD_BASE
    # assert_in("flag lod mask", (0, NodeFlag.Unk15), flag_lod_mask, offset + 36)

    assert_eq("field 044", 1, node.unk044, offset + 44)
    if node.zone_id != ZONE_DEFAULT:
        assert_between("zone id", 1, 80, node.zone_id, offset + 48)
    assert_ne("data ptr", 0, node.data_ptr, offset + 56)
    assert_eq("mesh index", -1, node.mesh_index, offset + 60)
    # assert area partition properly once we have read the world data
    assert_between("area partition x", -1, 64, node.area_partition_x, offset + 76)
    assert_between("area partition y", -1, 64, node.area_partition_y, offset + 80)
    # must have one parent
    assert_eq("parent count", 1, node.parent_count, offset + 84)
    assert_ne("parent array ptr", 0, node.parent_array_ptr, offset + 88)
    # always has at least one child
    assert_between("children count", 1, 32, node.children_count, offset + 92)
    assert_ne("children array ptr", 0, node.children_array_ptr, offset + 96)
    assert_ne("block 1", BLOCK_EMPTY, node.block1, offset + 116)
    assert_eq("block 2", BLOCK_EMPTY, node.block2, offset + 140)
    assert_eq("block 3", node.block1, node.block3, offset + 164)
    assert_eq("field 196", 160, node.unk196, offset + 196)


@_assert_node(NodeType.Light)
def _assert_node_info_light(node: Node, offset: int, _mesh_count: int) -> None:
    assert_eq("name", "sunlight", node.name, offset + 0)
    assert_eq("flag", NODE_FLAG_DEFAULT | NodeFlag.Unk08, node.flag, offset + 36)
    assert_eq("field 044", 0, node.unk044, offset + 44)
    assert_eq("zone id", ZONE_DEFAULT, node.zone_id, offset + 48)
    assert_ne("data ptr", 0, node.data_ptr, offset + 56)
    assert_eq("mesh index", -1, node.mesh_index, offset + 60)
    assert_eq("area partition x", -1, node.area_partition_x, offset + 76)
    assert_eq("area partition y", -1, node.area_partition_y, offset + 80)
    # lights seem to have an internal parent pointer
    assert_eq("parent count", 0, node.parent_count, offset + 84)
    assert_eq("parent array ptr", 0, node.parent_array_ptr, offset + 88)
    assert_eq("children count", 0, node.children_count, offset + 92)
    assert_eq("children array ptr", 0, node.children_array_ptr, offset + 96)
    assert_eq("block 1", BLOCK_LIGHT, node.block1, offset + 116)
    assert_eq("block 2", BLOCK_EMPTY, node.block2, offset + 140)
    assert_eq("block 3", BLOCK_EMPTY, node.block3, offset + 164)
    assert_eq("field 196", 0, node.unk196, offset + 196)


assert ASSERT_NODE_INFO.keys() == set(NodeType)
