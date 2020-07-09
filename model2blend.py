# Blender is probably not installed in the linting environment,
# so importing bpy and bmesh will fail
# pylint: disable=import-error
import argparse
import json
import sys
from math import radians
from pathlib import Path
from zipfile import ZipFile

import bmesh
import bpy


def _process_mesh(name, mesh_data, material_factory):  # pylint: disable=too-many-locals
    mesh = bpy.data.meshes.new(name=name)
    obj = bpy.data.objects.new(name, mesh)

    vertices = mesh_data["vertices"]
    # skipped: normals
    polygons = mesh_data["polygons"]

    textures = set()
    for poly in polygons:
        textures.add(poly["texture_index"])

    tex_index_to_mat_index = {}
    for material_index, texture_index in enumerate(textures):
        mat = material_factory(texture_index)
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
        # skipped: vertex_colors
        # skipped: normal_indices
        uvs = poly["uv_coords"]
        texture_index = poly["texture_index"]

        try:
            face = bm.faces.new(bm.verts[i] for i in vertex_indices)
        except ValueError as e:
            # some models contain duplicate faces. they are identical, so
            # skipping them seems harmless
            print("Mesh", name, "error:", str(e), "ptr:", poly["vertex_ptr"])
            continue

        face.material_index = tex_index_to_mat_index[texture_index]

        if uvs:
            # because all our faces are created as loops, this should work
            for index_in_mesh, loop, uv in zip(vertex_indices, face.loops, uvs):
                assert loop.vert.index == index_in_mesh
                loop[uv_layer].uv = uv

    bm.to_mesh(mesh)
    bm.free()

    return obj


def _process_node(node, parent, material_factory):
    name = node["name"]
    object3d = node["object3d"]
    mesh_data = node["mesh"]
    children = node["children"]

    if not mesh_data:
        obj = bpy.data.objects.new(name, None)  # empty
    else:
        obj = _process_mesh(name, mesh_data, material_factory)

    obj.location = (object3d["trans_x"], object3d["trans_y"], object3d["trans_z"])
    obj.rotation_euler = (object3d["rot_x"], object3d["rot_y"], object3d["rot_z"])

    bpy.context.collection.objects.link(obj)

    if parent:
        obj.parent = parent

    for child in children:
        _process_node(child, obj, material_factory)

    # move the "head" object to a different layer
    if name == "head":
        collection = bpy.context.scene.collection
        head = bpy.data.collections.new("head")
        collection.children.link(head)
        head.objects.link(obj)
        collection.objects.unlink(obj)
        head.hide_viewport = True
        head.hide_render = True

    return obj


def _add_camera():
    camera = bpy.data.cameras.new("Camera")
    camera.lens = 18

    camera_obj = bpy.data.objects.new("Camera", camera)
    camera_obj.location = (0.0, -60.0, 8.0)
    camera_obj.rotation_euler = (radians(80), 0.0, 0.0)

    bpy.context.scene.collection.objects.link(camera_obj)
    bpy.context.scene.camera = camera_obj


def _set_shading():
    for area in bpy.context.workspace.screens[0].areas:
        for space in area.spaces:
            if space.type == "VIEW_3D":
                space.shading.type = "MATERIAL"


def _create_anim(anim):
    objects = dict(bpy.data.objects.items())
    frames = anim["frames"]

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = frames

    for obj_name, anim_data in anim["parts"].items():
        try:
            obj = objects[obj_name]
        except KeyError:
            print("Unknown anim object", obj_name)
            continue

        # prime the animation with the first keyframe
        prev_loc, prev_rot = anim_data[0]

        obj.location = prev_loc
        obj.keyframe_insert(data_path="location", frame=1)

        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = prev_rot
        obj.keyframe_insert(data_path="rotation_quaternion", frame=1)

        # step through the next frames. if they're the same, don't insert
        for frame, (next_loc, next_rot) in enumerate(anim_data[1:], 2):
            if next_loc != prev_loc:
                obj.location = next_loc
                obj.keyframe_insert(data_path="location", frame=frame)
                prev_loc = next_loc

            if next_rot != prev_rot:
                obj.rotation_quaternion = next_rot
                obj.keyframe_insert(data_path="rotation_quaternion", frame=frame)
                prev_rot = next_rot


def model_to_blend(root_node, material_factory, name, anim):
    # empty scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    root_obj = _process_node(root_node, None, material_factory)
    # hack to convert Y-up model to Blender's coordinate system
    root_obj.rotation_euler = (radians(90), radians(0), radians(180))

    if anim:
        _create_anim(anim)

    _add_camera()
    _set_shading()
    bpy.context.scene.render.filepath = f"//{name}_##"

    bpy.ops.wm.save_as_mainfile(filepath=f"{name}.blend")


class MaterialFactory:
    def __init__(self, mechtex, materials):
        self.mechtex = ZipFile(mechtex)
        self.materials = materials
        self.cache = {}

    def __call__(self, texture_index):
        try:
            return self.cache[texture_index]
        except KeyError:
            pass

        material_info = self.materials[texture_index]

        try:
            material_name = material_info["name"]
        except KeyError:
            # untextured
            mat = bpy.data.materials.new(f"material_{texture_index}")
            mat.use_nodes = True

            try:
                red = material_info["red"] / 255.0
                green = material_info["green"] / 255.0
                blue = material_info["blue"] / 255.0
            except KeyError:
                pass
            else:
                bsdf = mat.node_tree.nodes["Principled BSDF"]
                bsdf.inputs[0].default_value = (red, green, blue, 1)
        else:
            self.mechtex.extract(f"{material_name}.png")

            mat = bpy.data.materials.new(material_name)
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes["Principled BSDF"]
            image = bpy.data.images.load(f"//{material_name}.png")

            tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
            tex.image = image

            mat.node_tree.links.new(bsdf.inputs["Base Color"], tex.outputs["Color"])

        self.cache[texture_index] = mat
        return mat


def main():
    parser = argparse.ArgumentParser(
        prog="blender --background --factory-startup --python model2blend.py --",
        description="Convert dumped MechWarrior 3 model data to Blender files.",
    )
    parser.add_argument(
        "directory",
        type=lambda value: Path(value).resolve(strict=True),
        help="A directory containing 'mechlib.zip' and 'rmechtex.zip'",
    )
    parser.add_argument("model_name", help="The model to convert")
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

    mechlib = (args.directory / "mechlib.zip").resolve(strict=True)
    mechtex = (args.directory / "rmechtex.zip").resolve(strict=True)

    if args.anim:
        name = f"{args.model_name}_{args.anim}"
    else:
        name = f"{args.model_name}"

    print(f"Converting '{args.model_name}' to '{name}.blend'")

    with ZipFile(mechlib) as zipfile:
        with zipfile.open("materials.json", "r") as f:
            materials = json.load(f)

        mechfile = f"mech_{args.model_name}.json"
        with zipfile.open(mechfile, "r") as f:
            root_node = json.load(f)

    if args.anim:
        motion = (args.directory / "motion.zip").resolve(strict=True)
        with ZipFile(motion) as zipfile:
            with zipfile.open(f"{name}.json", "r") as f:
                anim = json.load(f)
    else:
        anim = None

    material_factory = MaterialFactory(mechtex, materials)
    model_to_blend(root_node, material_factory, name, anim)


if __name__ == "__main__":
    main()
