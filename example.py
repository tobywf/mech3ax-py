"""This script is an example of how to use the mech3ax library.

Assuming you have installed mech3ax somehow, for example in a virtual
environment (see README), it can be run like this:

.. code-block:: console

    $ python example.py "<install location with Mech3.exe>"

This script is only an example, and completely unsupported. If you run into
issues using it, please don't raise an issue until you are sure it's an issue
with the underlying library.
"""
import json
import sys
from pathlib import Path

from mech3ax.archive import extract_archive
from mech3ax.mechlib import extract_materials
from mech3ax.models import extract_model
from mech3ax.motion import add_motions_to_models
from mech3ax.reader import extract_reader
from mech3ax.resources import extract_messages
from mech3ax.sounds import sound_archive_to_zip
from mech3ax.textures import texture_archives_to_zip

base_path = Path(sys.argv[1])
zbd_path = base_path / "zbd"

print("sounds")
output_path = Path.cwd() / "sounds"
output_path.mkdir()
sound_archive_to_zip(
    output_path / "sounds-low.zip", zbd_path, sound_archive="soundsL.zbd"
)
sound_archive_to_zip(
    output_path / "sounds-high.zip", zbd_path, sound_archive="soundsH.zbd"
)

print("textures (this may take a while)")

output_path = Path.cwd() / "textures"
output_path.mkdir()
for tex_path in zbd_path.rglob("*tex*.zbd"):
    rel_path = tex_path.relative_to(zbd_path)
    mission = rel_path.parent.name
    if not mission:
        zip_name = f"{tex_path.stem}.zip"
    else:
        zip_name = f"{mission}-{tex_path.stem}.zip"
    texture_archives_to_zip(output_path / zip_name, tex_path)
texture_archives_to_zip(output_path / "rimage.zip", zbd_path / "rimage.zbd")

print("executable resources")
output_path = Path.cwd() / "resources"
output_path.mkdir()
dll_path = base_path / "Mech3Msg.dll"
json_path = output_path / "messages.json"
extract_messages(dll_path, json_path)


print("mechlib and motion")
output_path = Path.cwd() / "mechlib"
output_path.mkdir()
data = (zbd_path / "mechlib.zbd").read_bytes()
for item_name, item_data in extract_archive(data):
    if item_name.endswith(".flt"):
        model = extract_model(item_data)
        json_path = output_path / item_name.replace(".flt", ".json")
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(model, f, indent=2)
    elif item_name == "materials":
        materials = list(extract_materials(item_data))
        json_path = output_path / "materials.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(materials, f, indent=2)
    else:
        print("skipped", item_name)
add_motions_to_models(zbd_path / "motion.zbd", output_path)

print("reader")
output_path = Path.cwd() / "reader"
output_path.mkdir()
for reader_path in zbd_path.rglob("reader*.zbd"):
    rel_path = reader_path.relative_to(zbd_path)
    mission = rel_path.parent.name
    base_path = output_path
    if mission:
        base_path = base_path / mission
        base_path.mkdir(exist_ok=True)
    base_path = base_path / reader_path.stem
    base_path.mkdir(exist_ok=True)
    extract_reader(reader_path, base_path)
