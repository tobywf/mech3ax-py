"""Convert 'mechlib.zbd' files to ZIP files.

The conversion is lossless and produces a binary accurate output by default.
"""
import logging
from argparse import Namespace, _SubParsersAction
from io import BytesIO
from pathlib import Path
from typing import List
from zipfile import ZIP_DEFLATED, ZipFile

from pydantic import BaseModel

from ..parse.archive import ArchiveEntry, read_archive, write_archive
from ..parse.mechlib import (
    FORMAT_DATA,
    VERSION_DATA,
    Material,
    Node,
    read_format,
    read_materials,
    read_model,
    read_version,
    write_materials,
    write_model,
)
from .archive import MANIFEST, ArchiveInfo, ArchiveManifest, Renamer
from .utils import dir_exists, output_resolve, path_exists

MATERIALS = "materials.json"
LOG = logging.getLogger(__name__)


class Materials(BaseModel):
    __root__: List[Material]


def mechlib_read(z: ZipFile, entry: ArchiveEntry, renamer: Renamer) -> ArchiveInfo:
    if entry.name == "version":
        read_version(entry.data)
        z.writestr(entry.name, "")
        return ArchiveInfo.from_entry(entry, entry.name)

    if entry.name == "format":
        read_format(entry.data)
        z.writestr(entry.name, "")
        return ArchiveInfo.from_entry(entry, entry.name)

    if entry.name == "materials":
        materials = Materials(__root__=list(read_materials(entry.data)))
        z.writestr(MATERIALS, materials.json(exclude_defaults=True, indent=2))
        return ArchiveInfo.from_entry(entry, MATERIALS)

    rename = renamer(entry.name.replace(".flt", ".json"))
    root = read_model(entry.data)
    z.writestr(rename, root.json(indent=2))

    return ArchiveInfo.from_entry(entry, rename)


def mechlib_zbd_to_zip(input_zbd: Path, output_zip: Path) -> None:
    renamer = Renamer()

    # the models can get rather big...
    with ZipFile(output_zip, "w", compression=ZIP_DEFLATED, compresslevel=9) as z:
        files = []

        data = input_zbd.read_bytes()
        for entry in read_archive(data):
            info = mechlib_read(z, entry, renamer)
            files.append(info)
        data = None  # type: ignore

        manifest = ArchiveManifest(__root__=files)
        z.writestr(MANIFEST, manifest.json(exclude_defaults=True, indent=2))


def mechlib_write(z: ZipFile, info: ArchiveInfo) -> ArchiveEntry:
    if info.name == "version":
        return info.to_entry(VERSION_DATA)

    if info.name == "format":
        return info.to_entry(FORMAT_DATA)

    if info.name == "materials":
        with z.open(info.rename) as ft:
            materials = Materials.parse_raw(ft.read())

        with BytesIO() as fb:
            write_materials(fb, materials.__root__)
            return info.to_entry(fb.getvalue())

    with z.open(info.rename) as ft:
        root = Node.parse_raw(ft.read())

    with BytesIO() as fb:
        write_model(fb, root)
        data = fb.getvalue()

    return info.to_entry(data)


def mechlib_zip_to_zbd(input_zip: Path, output_zbd: Path) -> None:
    with ZipFile(input_zip, "r") as z:
        with z.open(MANIFEST, "r") as ft:
            manifest = ArchiveManifest.parse_raw(ft.read())

        entries = iter(mechlib_write(z, info) for info in manifest.__root__)

        with output_zbd.open("wb") as fb:
            write_archive(fb, entries)


def mechlib_from_zbd_command(args: Namespace) -> None:
    output_zip = output_resolve(args.input_zbd, args.output_zip, ".zip")
    mechlib_zbd_to_zip(args.input_zbd, output_zip)


def mechlib_from_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("mechlib", description=__doc__)
    parser.set_defaults(command=mechlib_from_zbd_command)
    parser.add_argument("input_zbd", type=path_exists)
    parser.add_argument("output_zip", type=dir_exists, default=None, nargs="?")


def mechlib_to_zbd_command(args: Namespace) -> None:
    output_zbd = output_resolve(args.input_zip, args.output_zbd, ".zbd")
    mechlib_zip_to_zbd(args.input_zip, output_zbd)


def mechlib_to_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("mechlib", description=__doc__)
    parser.set_defaults(command=mechlib_to_zbd_command)
    parser.add_argument("input_zip", type=path_exists)
    parser.add_argument("output_zbd", type=dir_exists, default=None, nargs="?")
