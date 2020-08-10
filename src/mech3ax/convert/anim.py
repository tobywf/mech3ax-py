"""Convert 'anim.zbd' files to JSON files.

The conversion is lossless and produces a binary accurate output by default.
"""
from argparse import Namespace, _SubParsersAction
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from ..parse.anim import read_anim
from .utils import dir_exists, output_resolve, path_exists

ANIM_METADATA = "metadata.json"


def anim_zbd_to_zip(input_zbd: Path, output_zip: Path) -> None:
    data = input_zbd.read_bytes()
    anim_md, anim_defs = read_anim(data)

    with ZipFile(output_zip, "w", compression=ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(ANIM_METADATA, anim_md.json(indent=2))

        for anim_def in anim_defs:
            z.writestr(
                anim_def.file_name, anim_def.json(exclude_defaults=True, indent=2)
            )


# def anim_json_to_zbd(input_json: Path, output_zbd: Path) -> None:
#     with input_json.open("r", encoding="utf-8") as ft:
#         scripts = Scripts.parse_raw(ft.read())
#     with output_zbd.open("wb") as fb:
#         write_anim(fb, scripts.__root__)


def anim_from_zbd_command(args: Namespace) -> None:
    output_zip = output_resolve(args.input_zbd, args.output_zip, ".zip")
    anim_zbd_to_zip(args.input_zbd, output_zip)


def anim_from_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("anim", description=__doc__)
    parser.set_defaults(command=anim_from_zbd_command)
    parser.add_argument("input_zbd", type=path_exists)
    parser.add_argument("output_zip", type=dir_exists, default=None, nargs="?")


# def anim_to_zbd_command(args: Namespace) -> None:
#     output_zbd = output_resolve(args.input_zip, args.output_zbd, ".zbd")
#     anim_json_to_zbd(args.input_zip, output_zbd)


def anim_to_zbd_subparser(_subparsers: _SubParsersAction) -> None:
    # parser = subparsers.add_parser("anim", description=__doc__)
    # parser.set_defaults(command=anim_to_zbd_command)
    # parser.add_argument("input_zip", type=path_exists)
    # parser.add_argument("output_zbd", type=dir_exists, default=None, nargs="?")
    pass
