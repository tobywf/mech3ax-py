"""Convert 'anim.zbd' files to JSON files.

The conversion is lossless and produces a binary accurate output by default.
"""
from argparse import Namespace, _SubParsersAction
from pathlib import Path

from ..parse.anim import read_anim
from .utils import dir_exists, output_resolve, path_exists


def anim_zbd_to_json(input_zbd: Path, output_json: Path) -> None:
    data = input_zbd.read_bytes()
    anim, text = read_anim(data)

    with output_json.open("w", encoding="utf-8") as f:
        f.write(anim.json(exclude_defaults=True, indent=2))

    with output_json.with_suffix(".txt").open("w", encoding="utf-8") as f:
        f.write(text)


# def anim_json_to_zbd(input_json: Path, output_zbd: Path) -> None:
#     with input_json.open("r", encoding="utf-8") as ft:
#         scripts = Scripts.parse_raw(ft.read())
#     with output_zbd.open("wb") as fb:
#         write_anim(fb, scripts.__root__)


def anim_from_zbd_command(args: Namespace) -> None:
    output_json = output_resolve(args.input_zbd, args.output_json, ".json")
    anim_zbd_to_json(args.input_zbd, output_json)


def anim_from_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("anim", description=__doc__)
    parser.set_defaults(command=anim_from_zbd_command)
    parser.add_argument("input_zbd", type=path_exists)
    parser.add_argument("output_json", type=dir_exists, default=None, nargs="?")


# def anim_to_zbd_command(args: Namespace) -> None:
#     output_zbd = output_resolve(args.input_json, args.output_zbd, ".zbd")
#     anim_json_to_zbd(args.input_json, output_zbd)


def anim_to_zbd_subparser(_subparsers: _SubParsersAction) -> None:
    # parser = subparsers.add_parser("anim", description=__doc__)
    # parser.set_defaults(command=anim_to_zbd_command)
    # parser.add_argument("input_json", type=path_exists)
    # parser.add_argument("output_zbd", type=dir_exists, default=None, nargs="?")
    pass
