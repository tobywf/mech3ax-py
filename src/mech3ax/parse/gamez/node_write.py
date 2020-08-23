from typing import BinaryIO, List, Mapping

from mech3ax.errors import assert_lt
from mech3ax.serde import NodeType

from ..utils import UINT32, pack_node_name
from .models import NODE_INFO, Node
from .node_data_size import SIZE_NODE_DATA
from .node_data_write import WRITE_NODE_DATA

UNK196: Mapping[NodeType, int] = {
    NodeType.Empty: 160,
    NodeType.Camera: 0,
    NodeType.World: 0,
    NodeType.Window: 0,
    NodeType.Display: 0,
    NodeType.Object3D: 160,
    NodeType.LOD: 160,
    NodeType.Light: 0,
}
assert UNK196.keys() == set(NodeType)


def _write_node_info(f: BinaryIO, node: Node) -> int:
    name_raw = pack_node_name(node.name, 36)
    unk196 = UNK196[node.node_type]

    data = NODE_INFO.pack(
        name_raw,
        node.flag,
        0,
        node.unk044,
        node.zone_id,
        node.node_type.value,
        node.data_ptr,
        node.mesh_index,
        0,
        1,
        0,
        node.area_partition_x,
        node.area_partition_y,
        node.parent_count,
        node.parent_array_ptr,
        node.children_count,
        node.children_array_ptr,
        0,
        0,
        0,
        0,
        *node.block1,
        *node.block2,
        *node.block3,
        0,
        0,
        unk196,
        0,
        0,
    )
    f.write(data)

    if node.node_type == NodeType.Empty:
        return 0

    size_data_fn = SIZE_NODE_DATA[node.node_type]
    size = size_data_fn(node.data)

    if node.parent_count:
        size += 4
    if node.children_count:
        size += 4 * node.children_count

    return size


def _write_node_info_zero(f: BinaryIO) -> None:
    data = NODE_INFO.pack(
        b"",
        0,
        0,
        0,
        0,
        0,
        0,
        -1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    )
    f.write(data)


def _write_node_data(f: BinaryIO, node: Node) -> None:
    write_data_fn = WRITE_NODE_DATA[node.node_type]
    write_data_fn(f, node.data)

    if node.parent_count:
        f.write(UINT32.pack(node.parent))

    for child in node.children:
        f.write(UINT32.pack(child))


def write_nodes(f: BinaryIO, array_size: int, nodes: List[Node], offset: int) -> None:
    node_count = len(nodes)
    assert_lt("node count", array_size, node_count, offset)
    offset += NODE_INFO.size * array_size + UINT32.size * array_size

    for node in nodes:
        size = _write_node_info(f, node)
        if node.node_type == NodeType.Empty:
            index = node.parent
        else:
            index = offset
        f.write(UINT32.pack(index))
        offset += size

    for i in range(node_count, array_size):
        _write_node_info_zero(f)

        index = i + 1
        if index == array_size:
            index = 0xFFFFFF
        f.write(UINT32.pack(index))

    for node in nodes:
        if node.node_type != NodeType.Empty:
            _write_node_data(f, node)
