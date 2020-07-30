"""Convert 'sounds*.zbd' files to ZIP files.

The conversion is lossless and produces a binary accurate output by default.
"""
import logging
from argparse import Namespace, _SubParsersAction
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

from ..parse.archive import read_archive, write_archive
from .archive import MANIFEST, ArchiveInfo, ArchiveManifest, Renamer
from .utils import dir_exists, output_resolve, path_exists

LOG = logging.getLogger(__name__)


def sounds_zbd_to_zip(
    input_zbd: Path, output_zip: Path, include_loose: bool = False
) -> None:
    renamer = Renamer()

    with ZipFile(output_zip, "w") as z:
        sounds = []

        data = input_zbd.read_bytes()
        for entry in read_archive(data):
            rename = renamer(entry.name)
            z.writestr(rename, entry.data)
            sounds.append(ArchiveInfo.from_entry(entry, rename))
        end = len(data)
        data = None  # type: ignore

        if include_loose:
            base_path = input_zbd.parent
            for i, path in enumerate(base_path.glob("*.wav")):
                name = path.name
                LOG.debug("Including loose sound file '%s'", name)

                rename = renamer(name)
                z.writestr(rename, path.read_bytes())
                info = ArchiveInfo(
                    name=path.name,
                    rename=rename,
                    start=end + i,
                    write_time=datetime.now(timezone.utc),
                )
                sounds.append(info)

        manifest = ArchiveManifest(__root__=sounds)
        z.writestr(MANIFEST, manifest.json(exclude_defaults=True, indent=2))


def sounds_zip_to_zbd(input_zip: Path, output_zbd: Path) -> None:
    with ZipFile(input_zip, "r") as z:
        with z.open(MANIFEST, "r") as ft:
            manifest = ArchiveManifest.parse_raw(ft.read())

        entries = iter(info.to_entry(z.read(info.rename)) for info in manifest.__root__)

        with output_zbd.open("wb") as fb:
            write_archive(fb, entries)


def sounds_from_zbd_command(args: Namespace) -> None:
    output_zip = output_resolve(args.input_zbd, args.output_zip, ".zip")
    sounds_zbd_to_zip(args.input_zbd, output_zip, args.include_loose)


def sounds_from_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("sounds", description=__doc__)
    parser.set_defaults(command=sounds_from_zbd_command)
    parser.add_argument("input_zbd", type=path_exists)
    parser.add_argument("output_zip", type=dir_exists, default=None, nargs="?")
    parser.add_argument(
        "--include-loose",
        action="store_true",
        help="Include loose sounds files that the patch installs",
    )


def sounds_to_zbd_command(args: Namespace) -> None:
    output_zbd = output_resolve(args.input_zip, args.output_zbd, ".zbd")
    sounds_zip_to_zbd(args.input_zip, output_zbd)


def sounds_to_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("sounds", description=__doc__)
    parser.set_defaults(command=sounds_to_zbd_command)
    parser.add_argument("input_zip", type=path_exists)
    parser.add_argument("output_zbd", type=dir_exists, default=None, nargs="?")
