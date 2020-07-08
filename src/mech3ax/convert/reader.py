"""Convert 'reader.zbd' files to ZIP files.

The conversion is lossless and produces a binary accurate output by default.
"""
import json
import logging
from argparse import Namespace, _SubParsersAction
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from ..parse.archive import ArchiveEntry, read_archive, write_archive
from ..parse.reader import read_reader, write_reader
from .archive import MANIFEST, ArchiveInfo, ArchiveManifest, Renamer
from .utils import dir_exists, output_resolve, path_exists

LOG = logging.getLogger(__name__)


def reader_zbd_to_zip(input_zbd: Path, output_zip: Path) -> None:
    renamer = Renamer()

    with ZipFile(output_zip, "w", compression=ZIP_DEFLATED, compresslevel=9) as z:
        readers = []

        data = input_zbd.read_bytes()
        for entry in read_archive(data):
            name = entry.name.replace(".zrd", ".json")
            rename = renamer(name)
            root = read_reader(entry.data)
            z.writestr(rename, json.dumps(root, indent=2))
            readers.append(ArchiveInfo.from_entry(entry, rename))
        data = None  # type: ignore

        manifest = ArchiveManifest(__root__=readers)
        z.writestr(MANIFEST, manifest.json(exclude_defaults=True, indent=2))


def reader_zip_to_zbd(input_zip: Path, output_zbd: Path) -> None:
    with ZipFile(input_zip, "r") as z:
        with z.open(MANIFEST, "r") as ft:
            manifest = ArchiveManifest.parse_raw(ft.read())

        def load_reader(info: ArchiveInfo) -> ArchiveEntry:
            with z.open(info.rename) as ft:
                root = json.load(ft)

            with BytesIO() as fb:
                write_reader(fb, root)
                data = fb.getvalue()

            return info.to_entry(data)

        entries = iter(load_reader(info) for info in manifest.__root__)

        with output_zbd.open("wb") as fb:
            write_archive(fb, entries)


def reader_from_zbd_command(args: Namespace) -> None:
    output_zip = output_resolve(args.input_zbd, args.output_zip, ".zip")
    reader_zbd_to_zip(args.input_zbd, output_zip)


def reader_from_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("reader", description=__doc__)
    parser.set_defaults(command=reader_from_zbd_command)
    parser.add_argument("input_zbd", type=path_exists)
    parser.add_argument("output_zip", type=dir_exists, default=None, nargs="?")


def reader_to_zbd_command(args: Namespace) -> None:
    output_zbd = output_resolve(args.input_zip, args.output_zbd, ".zbd")
    reader_zip_to_zbd(args.input_zip, output_zbd)


def reader_to_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("reader", description=__doc__)
    parser.set_defaults(command=reader_to_zbd_command)
    parser.add_argument("input_zip", type=path_exists)
    parser.add_argument("output_zbd", type=dir_exists, default=None, nargs="?")
