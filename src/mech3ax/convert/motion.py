"""Convert 'motion.zbd' files to ZIP files.

The conversion is lossless and produces a binary accurate output by default.
"""
import json
import logging
from argparse import Namespace, _SubParsersAction
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import Dict
from zipfile import ZipFile

from ..parse.archive import ArchiveEntry, read_archive, write_archive
from ..parse.motion import Motion, read_motion, write_motion
from .archive import MANIFEST, ArchiveInfo, ArchiveManifest
from .utils import dir_exists, output_resolve, path_exists

MECH_MOTIONS = "mech_motions.json"
LOG = logging.getLogger(__name__)


def motion_zbd_to_zip(input_zbd: Path, output_zip: Path) -> None:
    with ZipFile(output_zip, "w") as z:
        motions = []
        mech_motions: Dict[str, Dict[str, str]] = defaultdict(dict)

        data = input_zbd.read_bytes()
        for entry in read_archive(data):
            rename = f"{entry.name}.json"
            motion = read_motion(entry.data)
            z.writestr(rename, motion.json(indent=2))
            motions.append(ArchiveInfo.from_entry(entry, rename))

            if "_" in entry.name:
                mech_name, _, motion_name = entry.name.partition("_")
                mech_motions[mech_name][motion_name] = rename
        data = None  # type: ignore

        # helper file to make loading them easier
        z.writestr(MECH_MOTIONS, json.dumps(mech_motions, indent=2))

        manifest = ArchiveManifest(__root__=motions)
        z.writestr(MANIFEST, manifest.json(exclude_defaults=True, indent=2))


def motion_zip_to_zbd(input_zip: Path, output_zbd: Path) -> None:
    with ZipFile(input_zip, "r") as z:
        with z.open(MANIFEST, "r") as ft:
            manifest = ArchiveManifest.parse_raw(ft.read())

        def load_motion(info: ArchiveInfo) -> ArchiveEntry:
            with z.open(info.rename) as ft:
                motion = Motion.parse_raw(ft.read())

            with BytesIO() as fb:
                write_motion(fb, motion)
                data = fb.getvalue()

            return info.to_entry(data)

        entries = iter(load_motion(info) for info in manifest.__root__)

        with output_zbd.open("wb") as fb:
            write_archive(fb, entries)


def motion_from_zbd_command(args: Namespace) -> None:
    output_zip = output_resolve(args.input_zbd, args.output_zip, ".zip")
    motion_zbd_to_zip(args.input_zbd, output_zip)


def motion_from_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("motion", description=__doc__)
    parser.set_defaults(command=motion_from_zbd_command)
    parser.add_argument("input_zbd", type=path_exists)
    parser.add_argument("output_zip", type=dir_exists, default=None, nargs="?")


def motion_to_zbd_command(args: Namespace) -> None:
    output_zbd = output_resolve(args.input_zip, args.output_zbd, ".zbd")
    motion_zip_to_zbd(args.input_zip, output_zbd)


def motion_to_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("motion", description=__doc__)
    parser.set_defaults(command=motion_to_zbd_command)
    parser.add_argument("input_zip", type=path_exists)
    parser.add_argument("output_zbd", type=dir_exists, default=None, nargs="?")
