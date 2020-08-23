"""Convert 'gamez.zbd' files to ZIP files.

The conversion is lossless and produces a binary accurate output by default.
"""
import logging
from argparse import Namespace, _SubParsersAction
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from ..parse.gamez import (
    GameZ,
    GameZMetadata,
    Materials,
    Mesh,
    Nodes,
    Textures,
    read_gamez,
    write_gamez,
)
from .utils import dir_exists, output_resolve, path_exists

LOG = logging.getLogger(__name__)
TEXTURES = "textures.json"
MATERIALS = "materials.json"
NODES = "nodes.json"
METADATA = "metadata.json"


def gamez_zbd_to_zip(input_zbd: Path, output_zip: Path) -> None:
    data = input_zbd.read_bytes()
    gamez = read_gamez(data)
    data = None  # type: ignore

    # GameZ files contain a lot of data
    with ZipFile(output_zip, "w", compression=ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(METADATA, gamez.metadata.json(indent=2))
        z.writestr(TEXTURES, gamez.textures.json(indent=2))
        z.writestr(MATERIALS, gamez.materials.json(exclude_defaults=True, indent=2))
        z.writestr(NODES, gamez.nodes.json(exclude_defaults=True, indent=2))

        for i, mesh in enumerate(gamez.meshes):
            z.writestr(f"mesh_{i:04d}.json", mesh.json(exclude_defaults=True, indent=2))


def gamez_zip_to_zbd(input_zip: Path, output_zbd: Path) -> None:
    with ZipFile(input_zip, "r") as z:
        with z.open(METADATA, "r") as ft:
            metadata = GameZMetadata.parse_raw(ft.read())

        with z.open(TEXTURES, "r") as ft:
            textures = Textures.parse_raw(ft.read())

        with z.open(MATERIALS, "r") as ft:
            materials = Materials.parse_raw(ft.read())

        with z.open(NODES, "r") as ft:
            nodes = Nodes.parse_raw(ft.read())

        meshes = []
        for i in range(metadata.mesh_count):
            with z.open(f"mesh_{i:04d}.json", "r") as ft:
                mesh = Mesh.parse_raw(ft.read())
            meshes.append(mesh)

    gamez = GameZ(
        textures=textures,
        materials=materials,
        meshes=meshes,
        nodes=nodes,
        metadata=metadata,
    )

    with output_zbd.open("wb") as fb:
        write_gamez(fb, gamez)


def gamez_from_zbd_command(args: Namespace) -> None:
    output_zip = output_resolve(args.input_zbd, args.output_zip, ".zip")
    gamez_zbd_to_zip(args.input_zbd, output_zip)


def gamez_from_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("gamez", description=__doc__)
    parser.set_defaults(command=gamez_from_zbd_command)
    parser.add_argument("input_zbd", type=path_exists)
    parser.add_argument("output_zip", type=dir_exists, default=None, nargs="?")


def gamez_to_zbd_command(args: Namespace) -> None:
    output_zbd = output_resolve(args.input_zip, args.output_zbd, ".zbd")
    gamez_zip_to_zbd(args.input_zip, output_zbd)


def gamez_to_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("gamez", description=__doc__)
    parser.set_defaults(command=gamez_to_zbd_command)
    parser.add_argument("input_zip", type=path_exists)
    parser.add_argument("output_zbd", type=dir_exists, default=None, nargs="?")
