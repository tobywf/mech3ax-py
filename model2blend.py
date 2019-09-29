# Blender is probably not installed in the linting environment,
# so importing bpy and bmesh will fail
# pylint: disable=import-error
import json
import sys
from functools import lru_cache
from itertools import count
from math import radians
from pathlib import Path

import bmesh
import bpy


def _create_objects(part, parent, get_material):  # pylint: disable=too-many-locals
    name = part["name"]
    data = part["object"]
    children = part["children"]

    if not data:
        obj = bpy.data.objects.new(name, None)  # empty
    else:
        mesh = bpy.data.meshes.new(name=name)
        obj = bpy.data.objects.new(name, mesh)

        textures = data["textures"]
        vertices = data["vertices"]
        # skipped: normals
        polygons = data["polygons"]

        tex_index_to_mat_index = {}
        for material_index, texture_index in enumerate(textures):
            mat = get_material(texture_index)
            obj.data.materials.append(mat)
            tex_index_to_mat_index[texture_index] = material_index

        # it may be possible to do this with a normal Mesh object, similar
        # to Blender's import_obj.py add-on. But this works.
        bm = bmesh.new()
        for vert in vertices:
            bm.verts.new(vert)

        bm.verts.ensure_lookup_table()
        bm.verts.index_update()

        uv_layer = bm.loops.layers.uv.new()

        for poly in polygons:
            vertex_indices = poly["vertex_indices"]
            texture_index = poly["texture_index"]
            # skipped: normal_indices
            uvs = poly["uv_coords"]
            # skipped: vertex_colors

            face = bm.faces.new(bm.verts[i] for i in vertex_indices)
            face.material_index = tex_index_to_mat_index[texture_index]

            if uvs:
                # because all our faces are created as loops, this should work
                for index_in_mesh, loop, uv in zip(vertex_indices, face.loops, uvs):
                    assert loop.vert.index == index_in_mesh
                    loop[uv_layer].uv = uv

        bm.to_mesh(mesh)
        bm.free()

    obj.location = part["location"]
    obj.rotation_euler = part["rotation"]

    bpy.context.collection.objects.link(obj)
    if parent:
        obj.parent = parent

    for child in children:
        _create_objects(child, obj, get_material)

    return obj


def _material_factory(tex_path, blend_path, materials):

    output_path = blend_path.parent
    unknown_materials = count()

    @lru_cache(maxsize=None)
    def _get_material(texture_index):
        material_name = materials[texture_index]
        if material_name:
            mat = bpy.data.materials.new(material_name)
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes["Principled BSDF"]

            material_path = tex_path / f"{material_name}.png"

            try:
                material_path = material_path.resolve(strict=True)
            except FileNotFoundError:
                print("Material", material_name, "not found:", material_path)
            else:
                try:
                    material_path = material_path.relative_to(output_path)
                except ValueError:
                    print("Could not make", material_path, "relative to", output_path)
                    print("Using absolute path")
                    material_path = str(material_path)
                else:
                    material_path = f"//{material_path!s}"

                image = bpy.data.images.load(material_path)

                tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
                tex.image = image

                mat.node_tree.links.new(bsdf.inputs["Base Color"], tex.outputs["Color"])
        else:
            unknown_material = next(unknown_materials)
            material_name = f"unknown.{unknown_material}"
            mat = bpy.data.materials.new(material_name)
            mat.use_nodes = True

        return mat

    return _get_material


def model_to_blend(json_path, tex_path, blend_path, materials):
    # empty scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    get_material = _material_factory(tex_path, blend_path, materials)

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    model = data["model"]
    root = _create_objects(model, None, get_material)
    # hack to convert Y-up model to Blender's coordinate system
    root.rotation_euler = (radians(90), radians(0), radians(180))

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :]
    print(argv)

    json_path = Path(argv[0]).resolve(strict=True)
    tex_path = Path(argv[1]).resolve(strict=True)
    blend_path = Path.cwd() / f"{json_path.stem}.blend"
    mat_path = (json_path.parent / "materials.json").resolve(strict=True)

    with mat_path.open("r", encoding="utf-8") as f:
        materials = json.load(f)

    model_to_blend(json_path, tex_path, blend_path, materials)


if __name__ == "__main__":
    main()
