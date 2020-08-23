from typing import List, Optional

from mech3ax.errors import (
    Mech3InternalError,
    Mech3ParseError,
    assert_all_zero,
    assert_ascii,
    assert_between,
    assert_eq,
    assert_flag,
)
from mech3ax.serde import NodeType

from ..utils import UINT32, BinReader, ascii_zterm_node_name
from .models import NODE_FLAG_BASE, NODE_INFO, Node, NodeFlag
from .node_data_read import READ_NODE_DATA
from .node_info import ASSERT_NODE_INFO


def _read_node_info(  # pylint: disable=too-many-locals
    reader: BinReader, mesh_count: int
) -> Node:
    (
        # 36s
        name_raw,
        # 4I
        flag_raw,  # 036
        zero040,
        unk044,
        zone_id,  # 048
        # 2Ii
        node_type_raw,  # 052
        data_ptr,  # 056
        mesh_index,  # 060
        # 3I
        environment_data,  # 064
        action_priority,  # 068
        action_callback,  # 072
        # 2i
        area_partition_x,  # 076
        area_partition_y,  # 080
        # 4I
        parent_count,  # 084
        parent_array_ptr,  # 088
        children_count,  # 092
        children_array_ptr,  # 096
        # 4I
        zero100,
        zero104,
        zero108,
        zero112,
        # 6f
        unk116,
        unk120,
        unk124,
        unk128,
        unk132,
        unk136,
        # 6f
        unk140,
        unk144,
        unk148,
        unk152,
        unk156,
        unk160,
        # 6f
        unk164,
        unk168,
        unk172,
        unk176,
        unk180,
        unk184,
        # 5I
        zero188,
        zero192,
        unk196,
        zero200,
        zero204,
    ) = reader.read(NODE_INFO)

    # --- invariants for every node type

    with assert_ascii("name", name_raw, reader.prev + 0):
        name = ascii_zterm_node_name(name_raw)

    with assert_flag("flag", flag_raw, reader.prev + 36):
        flag = NodeFlag.check(flag_raw)

    assert_eq("field 040", 0, zero040, reader.prev + 40)

    with assert_flag("node type", node_type_raw, reader.prev + 52):
        node_type = NodeType(node_type_raw)

    assert_eq("env data", 0, environment_data, reader.prev + 64)
    assert_eq("action prio", 1, action_priority, reader.prev + 68)
    assert_eq("action cb", 0, action_callback, reader.prev + 72)

    assert_eq("field 100", 0, zero100, reader.prev + 100)
    assert_eq("field 104", 0, zero104, reader.prev + 104)
    assert_eq("field 108", 0, zero108, reader.prev + 108)
    assert_eq("field 112", 0, zero112, reader.prev + 112)

    assert_eq("field 188", 0, zero188, reader.prev + 188)
    assert_eq("field 192", 0, zero192, reader.prev + 192)
    assert_eq("field 200", 0, zero200, reader.prev + 200)
    assert_eq("field 204", 0, zero204, reader.prev + 204)

    # --- node-specific assertions

    block1 = (unk116, unk120, unk124, unk128, unk132, unk136)
    block2 = (unk140, unk144, unk148, unk152, unk156, unk160)
    block3 = (unk164, unk168, unk172, unk176, unk180, unk184)

    node = Node(
        name=name,
        node_type=node_type,
        flag=flag,
        zone_id=zone_id,
        mesh_index=mesh_index,
        parent_count=parent_count,
        parent_array_ptr=parent_array_ptr,
        children_count=children_count,
        children_array_ptr=children_array_ptr,
        parent=0,
        children=[],
        data_ptr=data_ptr,
        area_partition_x=area_partition_x,
        area_partition_y=area_partition_y,
        flag_repr=repr(flag & ~NODE_FLAG_BASE),
        unk044=unk044,
        unk196=unk196,
        block1=block1,
        block2=block2,
        block3=block3,
    )

    assert_fn = ASSERT_NODE_INFO[node.node_type]
    assert_fn(node, reader.prev, mesh_count)

    return node


def _read_node_infos_zero(reader: BinReader, index: int, array_size: int) -> None:
    for i in range(index, array_size):
        name_raw, *values = reader.read(NODE_INFO)
        assert_all_zero("name", name_raw, reader.prev + 0)

        for j, value in enumerate(values):
            offset = j * 4 + 36
            if j == 6:
                assert_eq(f"field {offset:02d}", -1, value, reader.prev + offset)
            else:
                assert_eq(f"field {offset:02d}", 0, value, reader.prev + offset)

        expected_index = i + 1
        if expected_index == array_size:
            # we'll never know why???
            expected_index = 0xFFFFFF

        actual_index = reader.read_u32()
        assert_eq("index", expected_index, actual_index, reader.prev)


def _read_node_data(reader: BinReader, node: Node) -> None:
    read_data_fn = READ_NODE_DATA[node.node_type]
    node.data = read_data_fn(reader)

    if node.parent_count:
        node.parent = reader.read_u32()

    node.children = [reader.read_u32() for _ in range(node.children_count)]


def _assert_area_partitions(world_node: Optional[Node], nodes: List[Node]) -> None:
    if world_node and world_node.data:
        if world_node.node_type == NodeType.World and world_node.data.type == "World":
            x_count = world_node.data.area_partition_x_count
            y_count = world_node.data.area_partition_y_count
        else:  # pragma: no cover
            raise Mech3InternalError(
                f"World node data mismatch ({world_node.node_type}, {world_node.data.type!r})"
            )
    else:  # pragma: no cover
        raise Mech3ParseError("No world node or world node data")

    for node in nodes:
        x = node.area_partition_x
        y = node.area_partition_y
        if x > -1 and y > -1:
            assert_between("partition x", 0, x_count, x, "")
            assert_between("partition y", 0, y_count, y, "")
        else:
            assert_eq("partition x", -1, x, "")
            assert_eq("partition y", -1, y, "")


def read_nodes(reader: BinReader, array_size: int, mesh_count: int) -> List[Node]:
    prev_offset = end_offset = (
        reader.offset + NODE_INFO.size * array_size + UINT32.size * array_size
    )
    end_of_file = len(reader)

    nodes = []
    offsets = []
    world_node: Optional[Node] = None

    # the node_count is wildly inaccurate for some files, and there are more
    # nodes to read
    for i in range(array_size):  # pragma: no branch
        # if the first character of the name is null, this seems to be a
        # reliable indicator the node is unused
        if reader.data[reader.offset] == 0:
            break

        node = _read_node_info(reader, mesh_count)

        if node.node_type == NodeType.World:
            assert_eq("world node pos", 0, i, reader.prev)
            world_node = node
        elif node.node_type == NodeType.Window:
            assert_eq("window node pos", 1, i, reader.prev)
        elif node.node_type == NodeType.Camera:
            assert_eq("camera node pos", 2, i, reader.prev)
        # Display node is at position 3, but more than one display node is allowed

        nodes.append(node)
        offset = reader.read_u32()
        offsets.append(offset)

        if node.node_type == NodeType.Empty:
            # for empty nodes, this seems to point to other members in the tree
            assert_between("empty ref index", 4, array_size, offset, reader.prev)
            node.parent = offset
        else:
            # for other nodes, this seems to point to the location of node data
            assert_between(
                "node data offset", prev_offset, end_of_file - 1, offset, reader.prev,
            )
            prev_offset = offset

    _read_node_infos_zero(reader, i, array_size)

    assert_eq("node info end", end_offset, reader.offset, reader.offset)

    for node, offset in zip(nodes, offsets):
        if node.node_type == NodeType.Empty:
            continue

        assert_eq("node data offset", offset, reader.offset, reader.offset)
        _read_node_data(reader, node)

    _assert_area_partitions(world_node, nodes)
    assert_eq("node data end", end_of_file, reader.offset, reader.offset)

    return nodes
