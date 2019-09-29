# Blender is probably not installed in the linting environment,
# so importing bpy and bmesh will fail
# pylint: disable=import-error
import argparse
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


def _create_actions(animation):
    objects = dict(bpy.data.objects.items())
    frame_count = animation["frame_count"]

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = frame_count

    for obj_name, anim_data in animation.items():
        if obj_name == "frame_count":
            continue

        try:
            obj = objects[obj_name]
        except KeyError:
            continue

        prev_loc, prev_rot = anim_data[0]
        # delta_loc = [blender - first for blender, first in zip(obj.location, prev_loc)]
        # blender_loc = [current + delta for delta, current in zip(delta_loc, prev_loc)]
        # print(obj_name, tuple(obj.location), prev_loc)

        obj.location = prev_loc
        obj.keyframe_insert(data_path="location", frame=1)

        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = prev_rot
        obj.keyframe_insert(data_path="rotation_quaternion", frame=1)

        for frame, (next_loc, next_rot) in enumerate(anim_data[1:], 2):
            if next_loc != prev_loc:
                # blender_loc = [current + delta for delta, current in zip(delta_loc, next_loc)]
                obj.location = next_loc
                obj.keyframe_insert(data_path="location", frame=frame)
                prev_loc = next_loc

            if next_rot != prev_rot:
                obj.rotation_quaternion = next_rot
                obj.keyframe_insert(data_path="rotation_quaternion", frame=frame)
                prev_rot = next_rot


def model_to_blend(json_path, tex_path, blend_path, materials, anim_name):
    # empty scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    get_material = _material_factory(tex_path, blend_path, materials)

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    model = data["model"]
    root = _create_objects(model, None, get_material)
    # hack to convert Y-up model to Blender's coordinate system
    root.rotation_euler = (radians(90), radians(0), radians(180))

    if anim_name:
        animation = data["animations"][anim_name]
        _create_actions(animation)

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))


def main():
    parser = argparse.ArgumentParser(
        prog="blender --background --factory-startup --python model2blend.py --",
        description="Convert dumped MechWarrior 3 model data to Blender files.",
    )
    parser.add_argument(
        "model",
        type=lambda value: Path(value).resolve(strict=True),
        help="The the model's dumped data (JSON)",
    )
    parser.add_argument(
        "tex_dir",
        type=lambda value: Path(value).resolve(strict=True),
        help="The path to a directory containing extracted 'mech textures",
    )
    parser.add_argument(
        "--mat",
        default=None,
        type=lambda value: Path(value).resolve(strict=True),
        help=(
            "The material index (JSON). If not specified, the script will look "
            "for 'materials.json' in the same directory as the model."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        type=lambda value: Path(value).resolve(),
        help=(
            "The output Blender file. If not specified, the script will infer "
            "the name from the model and animation, and output to the current "
            "directory."
        ),
    )
    parser.add_argument(
        "--anim",
        default=None,
        help=(
            "If specified, the animation name to apply to the model. "
            "(The animation data is not posed, and it's difficult to save "
            "multiple key-framed animations to a Blender file.)"
        ),
    )

    # split our arguments from Blender arguments
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :]

    args = parser.parse_args(argv)

    if not args.tex_dir.is_dir():
        raise ValueError("tex_dir must be a directory")

    if args.output:
        blend_path = args.output
    else:
        if args.anim:
            filename = f"{args.model.stem}_{args.anim}.blend"
        else:
            filename = f"{args.model.stem}.blend"
        blend_path = Path.cwd() / filename

    if args.mat:
        mat_path = args.mat
    else:
        mat_path = (args.model.parent / "materials.json").resolve(strict=True)

    print(f"Converting '{args.model}' to '{blend_path}' with animation '{args.anim}'")
    print("Textures:", args.tex_dir)
    print("Materials:", mat_path)

    with mat_path.open("r", encoding="utf-8") as f:
        materials = json.load(f)

    model_to_blend(args.model, args.tex_dir, blend_path, materials, args.anim)


if __name__ == "__main__":
    main()
