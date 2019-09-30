from struct import Struct, unpack_from

from .utils import ascii_zterm

POINT_3D = Struct("<3f")
PURE_WHITE = (255.0, 255.0, 255.0)
ALMOST_WHITE = (254.0, 254.0, 254.0)


def _read_mesh_data(
    data, offset
):  # pylint: disable=too-many-locals,too-many-statements
    def _read_points(count):
        nonlocal offset
        points = []
        for _ in range(count):
            vert = POINT_3D.unpack_from(data, offset)
            offset += POINT_3D.size
            points.append(vert)
        return points

    # 005e8c08 "Error reading GameZ Model3D buffer data."
    fields = unpack_from("<23I", data, offset)
    offset += 92

    polygon_count = fields[4]
    vertex_count = fields[5]
    normal_count = fields[6]
    morph_count = fields[7]

    # 005e87f8 "Error reading GameZ Model3D vertex data."
    vertices = _read_points(vertex_count)
    # 005e8850 "Error reading GameZ Model3D vertex normal data."
    normals = _read_points(normal_count)
    # 005e88ac "Error reading GameZ Model3D morph vertex data."
    # always seems to be 0, otherwise try _read_points
    assert morph_count == 0, morph_count
    # 005e8908 "Error reading GameZ Model3D point light data."
    light_count = fields[8]
    # always seems to be 0 in the release code
    assert light_count == 0, light_count
    # if this was not 0, additional data would need to be read
    # 005e8964 "Error reading GameZ Model3D point light data."

    # 005e89c0 "Error reading GameZ Model3D polygon buffer."
    poly_headers = []
    for _poly in range(polygon_count):
        fields = unpack_from("<9I", data, offset)
        offset += 36
        poly_headers.append(fields)

    textures = set()
    polygons = []
    for fields in poly_headers:
        # this is by process of elimination. a lot of other fields are used
        # to hold pointers to buffers, but 7 and 8 aren't used in the function
        texture_index = fields[7]
        textures.add(texture_index)
        assert fields[8] == 0xFFFFFF00, fields[8]

        verts_in_poly = fields[0] & 0xFF

        has_vertices = verts_in_poly != 0
        has_normals = ((fields[0] & 0x200) != 0) and (fields[3] != 0)
        has_uvs = fields[4] != 0
        has_color = fields[5] != 0

        # 005e8a1 "Error reading GameZ Model3D polygon vertex index."
        vertex_indices = None
        if has_vertices:
            vertex_indices = unpack_from(f"<{verts_in_poly}I", data, offset)
            offset += 4 * verts_in_poly

        # 005e8a78 "Error reading GameZ Model3D polygon vertex normal index."
        normal_indices = None
        if has_normals:
            normal_indices = unpack_from(f"<{verts_in_poly}I", data, offset)
            offset += 4 * verts_in_poly

        # 005e8ae0 "Error reading GameZ Model3D polygon texture vertex data."
        uv_coords = None
        if has_uvs:
            uv_coords = []
            for _uv in range(verts_in_poly):
                u, v = unpack_from("<2f", data, offset)
                offset += 8
                uv_coords.append((u, 1 - v))

        # 005e8b48 "Error reading GameZ Model3D polygon vertex color data."
        vertex_colors = None
        if has_color:
            vertex_colors = _read_points(verts_in_poly)
            if all(color == PURE_WHITE for color in vertex_colors):
                vertex_colors = None
            elif all(color == ALMOST_WHITE for color in vertex_colors):
                vertex_colors = None
            else:
                # The only model/parts where this is not true is lfoot/rfoot on
                # `mech_supernova_1.flt`. I'm not sure how useful this data is.
                pass

        # 005e502c "read model: %d verts, %d polys [%d] bytes\n"

        polygons.append(
            {
                "texture_index": texture_index,
                "vertex_indices": vertex_indices,
                "normal_indices": normal_indices,
                "uv_coords": uv_coords,
                "vertex_colors": vertex_colors,
            }
        )

    return (
        offset,
        {
            # sets can't be serialised to JSON
            # might as well sort the data while converting it to a list
            "textures": sorted(textures),
            "vertices": vertices,
            "normals": normals,
            "polygons": polygons,
        },
    )


def _read_additional_header(data, offset):
    # first integer seems to be some count?
    additional_headers = [unpack_from("<3I", data, offset)]
    offset += 12
    additional_headers.extend(
        POINT_3D.unpack_from(data, offset + 12 * i) for i in range(11)
    )
    offset += 12 * 11

    assert (
        additional_headers[0] == (40, 0, 0)
        or additional_headers[0] == (32, 0, 0)
        # or additional_headers[0] == (0, 0, 0)  # in the demo?
    ), additional_headers[0]
    # unused?
    assert additional_headers[1] == (0.0, 0.0, 0.0), additional_headers[1]
    assert additional_headers[8] == (0.0, 0.0, 0.0), additional_headers[8]
    assert additional_headers[9] == (0.0, 0.0, 0.0), additional_headers[9]
    assert additional_headers[10] == (0.0, 0.0, 0.0), additional_headers[10]
    assert additional_headers[11] == (0.0, 0.0, 0.0), additional_headers[11]

    # 2 is rotation, all values between (a generously rounded) PI
    assert all(
        r > -3.1416 and r < 3.1416 for r in additional_headers[2]
    ), additional_headers[2]
    # 3 could have been intended for scale, and then was optimised out by
    # pre-scaling geometry
    assert additional_headers[3] == (1.0, 1.0, 1.0), additional_headers[3]
    # unknown - rotation axes?
    # assert additional_headers[4] == (1.0, 0.0, -0.0), additional_headers[4]
    # assert additional_headers[5] == (-0.0, 1.0, 0.0), additional_headers[5]
    # assert additional_headers[6] == (0.0, 0.0, 1.0), additional_headers[6]
    # 7 is location, can be inferred from the large variations (and trial & error)

    return offset, additional_headers


def _extract_nodes(data, offset):
    # 005e4ff8 "reading node\n"

    # initial header = 208
    part_name, *fields = unpack_from("<36s43I", data, offset)
    offset += 208
    # the unpack above is probably wrong, but the fields needs to extract the
    # nodes are all (u)int32.

    part_name = ascii_zterm(part_name)

    # 52 = 36 + 16 = 36 + 4 * 4
    node_type = fields[4]
    # 60 = 36 + 24 = 36 + 4 * 6
    has_data = fields[6] != 0
    # 92 = 36 + 36 = 36 + 4 * 14
    node_count = fields[14]

    if node_type != 5:
        raise ValueError(f"Unknown node type: {node_type}")

    # 005e5014 "read node: %s type=%s\n"
    # node type 5 always has the additional header
    offset, additional_headers = _read_additional_header(data, offset)

    rotation = additional_headers[2]
    location = additional_headers[7]

    obj = None
    if has_data:
        offset, obj = _read_mesh_data(data, offset)

    children = []
    for _ in range(node_count):
        offset, child_part = _extract_nodes(data, offset)
        children.append(child_part)

    # 005e4fe8 "read complete\n"

    part = {
        "name": part_name,
        "location": location,
        "rotation": rotation,
        "object": obj,
        "children": children,
        "additional_headers": additional_headers,
    }
    return offset, part


def extract_model(data):
    _, root = _extract_nodes(data, 0)

    # The first node is always a dummy node. I think this was done to simplify
    # parsing, so the first node could always be allocated with a size of 1.
    assert root["name"].endswith(".flt"), root["name"]
    assert len(root["children"]) == 1, root["children"]
    assert root["location"] == (0.0, 0.0, 0.0), root["location"]
    assert root["rotation"] == (0.0, 0.0, 0.0), root["rotation"]
    return {"model": root["children"][0], "animations": {}}
