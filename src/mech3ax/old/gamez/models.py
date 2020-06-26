"""WARNING: This is really dumb, the code to read Mech models is subtly different
"""

from collections import namedtuple
from struct import Struct, unpack_from
from typing import Any, Mapping, Sequence, Tuple
from warnings import warn

Vertex = Tuple[float, float, float]
VERTEX = Struct("<3f")
assert VERTEX.size == 12

Color = Tuple[float, float, float]
COLOR = Struct("<3f")
assert COLOR.size == 12

UvCoord = Tuple[float, float]
UV_COORD = Struct("<2f")
assert UV_COORD.size == 8

Polygon = namedtuple(
    "Polygon",
    [
        "vertex_info",
        "unk1",
        "vertex_indices",
        "normal_indices",
        "uv_coords",
        "vertex_colors",
        "unk2",
        "texture_index",
        "texture_info",
    ],
)
POLYGON = Struct("<9I")
assert POLYGON.size == 36

LightData = Tuple[
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    float,
    float,
    float,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
]
LIGHT_DATA = Struct("<8I3f8I")
assert LIGHT_DATA.size == 76


class ModelReader:
    def __init__(self, data: bytes, offset: int = 0):
        self.data = data
        self.offset = offset

    def _read_vertices(self, count: int) -> Sequence[Vertex]:
        points = []
        for _ in range(count):
            vert = VERTEX.unpack_from(self.data, self.offset)
            self.offset += VERTEX.size
            points.append(vert)
        return points

    def _read_lights(self, count: int) -> Sequence[int]:
        lights = []
        for _ in range(count):
            light = LIGHT_DATA.unpack_from(self.data, self.offset)
            self.offset += LIGHT_DATA.size
            lights.append(list(light))
        for light in lights:
            light[11] = self._read_vertices(light[3])
        return lights

    def _read_colors(self, count: int) -> Sequence[Color]:
        colors = []
        for _ in range(count):
            color = COLOR.unpack_from(self.data, self.offset)
            self.offset += COLOR.size
            colors.append(color)
        return colors

    def _read_uv_coords(self, count: int) -> Sequence[UvCoord]:
        uv_coords = []
        for _ in range(count):
            u, v = UV_COORD.unpack_from(self.data, self.offset)
            self.offset += UV_COORD.size
            uv_coords.append((u, 1 - v))
        return uv_coords

    def _read_indices(self, count: int) -> Sequence[int]:
        indices = unpack_from(f"<{count}I", self.data, self.offset)
        self.offset += 4 * count
        return list(indices)

    def _read_polygons(
        self, count: int
    ) -> Tuple[Sequence[int], Sequence[Mapping[str, Any]]]:
        # Error reading GameZ Model3D polygon buffer.
        poly_headers = []
        for _ in range(count):
            fields = POLYGON.unpack_from(self.data, self.offset)
            self.offset += POLYGON.size
            poly_headers.append(Polygon(fields))

        textures = set()
        polygons = []
        for polygon in poly_headers:
            textures.add(polygon.texture_index)

            verts_in_poly = polygon.vertex_info & 0xFF

            has_vertices = verts_in_poly != 0
            has_normals = (polygon.vertex_info & 0x200) != 0
            has_uvs = (polygon.texture_info & 0x01000000) != 0

            # Error reading GameZ Model3D polygon vertex index.
            vertex_indices = None
            if has_vertices:
                vertex_indices = self._read_indices(verts_in_poly)

            # Error reading GameZ Model3D polygon vertex normal index.
            normal_indices = None
            if has_normals:
                normal_indices = self._read_indices(verts_in_poly)

            # Error reading GameZ Model3D polygon texture vertex data.
            uv_coords = None
            if has_uvs:
                uv_coords = self._read_uv_coords(verts_in_poly)

            # Error reading GameZ Model3D polygon vertex color data.
            vertex_colors = self._read_colors(verts_in_poly)

            polygons.append(
                {
                    "texture_index": polygon.texture_index,
                    "vertex_indices": vertex_indices,
                    "normal_indices": normal_indices,
                    "uv_coords": uv_coords,
                    "vertex_colors": vertex_colors,
                }
            )

        # sets can't be serialised to JSON
        # might as well sort the data while converting it to a list
        return sorted(textures), polygons

    def _read_model(self):
        # Error reading GameZ Model3D buffer data.
        fields = unpack_from("<23I", self.data, self.offset)
        self.offset += 92

        polygon_count = fields[4]
        vertex_count = fields[5]
        normal_count = fields[6]
        morph_count = fields[7]
        light_count = fields[8]

        vertices = None
        if vertex_count:
            # Error reading GameZ Model3D vertex data.
            vertices = self._read_vertices(vertex_count)

        normals = None
        if normal_count:
            # Error reading GameZ Model3D vertex normal data.
            normals = self._read_vertices(normal_count)

        morph = None
        if morph_count:
            #  Error reading GameZ Model3D morph vertex data.
            morph = self._read_vertices(morph_count)

        lights = None
        if light_count:
            # Error reading GameZ Model3D point light data
            lights = self._read_lights(light_count)

        textures = None
        polygons = None
        if polygon_count:
            textures, polygons = self._read_polygons(polygon_count)

        return {
            "textures": sorted(textures),
            "vertices": vertices,
            "normals": normals,
            "polygons": polygons,
            "morph": morph,
            "lights": lights,
        }

    def read(self):
        array_size, model_count, index_max = unpack_from("<3I", self.data, self.offset)
        self.offset += 3 * 4

        headers = []
        for i in range(0, model_count):
            header = unpack_from("<24I", self.data, self.offset)
            self.offset += 24 * 4
            headers.append(header)

        # don't care about failures here, but could be useful to catch errors
        for i in range(model_count, array_size):
            header = unpack_from("<24I", self.data, self.offset)
            self.offset += 24 * 4
            for j, value in enumerate(header[:-1], 1):
                if value != 0:
                    warn(f"Expected value at {i}:{j} to be 0 (was {value})")

            expected = i + 1
            if expected == array_size:
                expected = 0xFFFFFFFF

            actual = header[-1]
            if actual != expected:
                warn(f"Expected index at {i} to be {expected} (was {actual})")
