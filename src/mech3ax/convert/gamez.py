"""Convert 'gamez.zbd' files to ZIP files.

Incomplete.
"""
import logging
from argparse import Namespace, _SubParsersAction
from pathlib import Path

from ..parse.gamez import (
    GameZ,
    GameZMetadata,
    Materials,
    Meshes,
    Nodes,
    Textures,
    read_gamez,
    write_gamez,
)
from .utils import dir_exists, output_resolve, path_exists

LOG = logging.getLogger(__name__)


def gamez_zbd_to_zip(input_zbd: Path, output_zip: Path) -> None:
    # with ZipFile(output_zip, "w") as z:
    data = input_zbd.read_bytes()
    gamez = read_gamez(data)
    data = None  # type: ignore

    output_json = output_zip.parent / f"{output_zip.stem}-textures.json"
    with output_json.open("w", encoding="utf-8") as f:
        f.write(gamez.textures.json(indent=2))

    output_json = output_zip.parent / f"{output_zip.stem}-materials.json"
    with output_json.open("w", encoding="utf-8") as f:
        f.write(gamez.materials.json(exclude_defaults=True, indent=2))

    output_json = output_zip.parent / f"{output_zip.stem}-meshes.json"
    with output_json.open("w", encoding="utf-8") as f:
        f.write(gamez.meshes.json(exclude_defaults=True, indent=2))

    output_json = output_zip.parent / f"{output_zip.stem}-nodes.json"
    with output_json.open("w", encoding="utf-8") as f:
        f.write(gamez.nodes.json(exclude_defaults=True, indent=2))

    output_json = output_zip.parent / f"{output_zip.stem}-metadata.json"
    with output_json.open("w", encoding="utf-8") as f:
        f.write(gamez.metadata.json(indent=2))


def gamez_from_zbd_command(args: Namespace) -> None:
    output_zip = output_resolve(args.input_zbd, args.output_zip, ".zip")
    gamez_zbd_to_zip(args.input_zbd, output_zip)


def gamez_from_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("gamez", description=__doc__)
    parser.set_defaults(command=gamez_from_zbd_command)
    parser.add_argument("input_zbd", type=path_exists)
    parser.add_argument("output_zip", type=dir_exists, default=None, nargs="?")


def gamez_zip_to_zbd(input_zip: Path, output_zbd: Path) -> None:
    input_json = input_zip.parent / f"{input_zip.stem}-textures.json"
    with input_json.open("r", encoding="utf-8") as ft:
        textures = Textures.parse_raw(ft.read())

    input_json = input_zip.parent / f"{input_zip.stem}-materials.json"
    with input_json.open("r", encoding="utf-8") as ft:
        materials = Materials.parse_raw(ft.read())

    input_json = input_zip.parent / f"{input_zip.stem}-meshes.json"
    with input_json.open("r", encoding="utf-8") as ft:
        meshes = Meshes.parse_raw(ft.read())

    input_json = input_zip.parent / f"{input_zip.stem}-nodes.json"
    with input_json.open("r", encoding="utf-8") as ft:
        nodes = Nodes.parse_raw(ft.read())

    input_json = input_zip.parent / f"{input_zip.stem}-metadata.json"
    with input_json.open("r", encoding="utf-8") as ft:
        metadata = GameZMetadata.parse_raw(ft.read())

    gamez = GameZ(
        textures=textures,
        materials=materials,
        meshes=meshes,
        nodes=nodes,
        metadata=metadata,
    )

    with output_zbd.open("wb") as fb:
        write_gamez(fb, gamez)


def gamez_to_zbd_command(args: Namespace) -> None:
    output_zbd = output_resolve(args.input_zip, args.output_zbd, ".zbd")
    gamez_zip_to_zbd(args.input_zip, output_zbd)


def gamez_to_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("gamez", description=__doc__)
    parser.set_defaults(command=gamez_to_zbd_command)
    parser.add_argument("input_zip", type=path_exists)
    parser.add_argument("output_zbd", type=dir_exists, default=None, nargs="?")
