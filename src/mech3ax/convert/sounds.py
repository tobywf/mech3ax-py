"""Convert 'sounds*.zbd' files to ZIP files.

The conversion is lossless and produces a binary accurate output by default.
"""
import logging
from argparse import Namespace, _SubParsersAction
from pathlib import Path
from typing import List, Set
from zipfile import ZipFile

from pydantic import BaseModel

from ..parse.archive import read_archive, write_archive
from .utils import Base64, dir_exists, output_resolve, path_exists

MANIFEST = "manifest.json"

LOG = logging.getLogger(__name__)


class SoundInfo(BaseModel):
    name: str
    rename: str
    garbage: Base64


class SoundManifest(BaseModel):
    class Config:
        json_encoders = {bytes: Base64.to_str}

    __root__: List[SoundInfo]


class Renamer:
    """Rename duplicates"""

    def __init__(self) -> None:
        self._names: Set[str] = set()

    def __call__(self, name: str) -> str:
        basename = Path(name)
        i = 1
        while name in self._names:
            name = f"{basename.stem}_{i}{basename.suffix}"
            i += 1

        self._names.add(name)
        return name


def sounds_zbd_to_zip(
    input_zbd: Path, output_zip: Path, include_loose: bool = False
) -> None:
    renamer = Renamer()

    with ZipFile(output_zip, "w") as z:
        sounds = []

        data = input_zbd.read_bytes()
        for name, filedata, garbage in read_archive(data):
            rename = renamer(name)
            z.writestr(rename, filedata)
            info = SoundInfo(name=name, rename=rename, garbage=garbage)
            sounds.append(info)
        data = None  # type: ignore

        if include_loose:
            base_path = input_zbd.parent
            for path in base_path.glob("*.wav"):
                name = path.name
                LOG.debug("Including loose sound file '%s'", name)

                rename = renamer(name)
                z.writestr(rename, path.read_bytes())
                info = SoundInfo(name=path.name, rename=rename, garbage=b"")
                sounds.append(info)

        manifest = SoundManifest(__root__=sounds)
        z.writestr(MANIFEST, manifest.json(indent=2))


def sounds_zip_to_zbd(input_zip: Path, output_zbd: Path) -> None:
    with ZipFile(input_zip, "r") as z:
        with z.open(MANIFEST, "r") as ft:
            manifest = SoundManifest.parse_raw(ft.read())

        entries = iter(
            (info.name, z.read(info.rename), info.garbage) for info in manifest.__root__
        )

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
