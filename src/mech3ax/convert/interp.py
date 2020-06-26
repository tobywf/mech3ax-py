"""Convert 'interp.zbd' files to JSON files.

The conversion is lossless and produces a binary accurate output by default.
"""
from argparse import Namespace, _SubParsersAction
from pathlib import Path
from typing import List

from pydantic import BaseModel

from ..parse.interp import Script, read_interp, write_interp
from .utils import dir_exists, output_resolve, path_exists


class Scripts(BaseModel):
    __root__: List[Script]


def interp_zbd_to_json(input_zbd: Path, output_json: Path) -> None:
    data = input_zbd.read_bytes()
    scripts = Scripts(__root__=list(read_interp(data)))

    with output_json.open("w", encoding="utf-8") as f:
        f.write(scripts.json(indent=2))


def interp_json_to_zbd(input_json: Path, output_zbd: Path) -> None:
    with input_json.open("r", encoding="utf-8") as ft:
        scripts = Scripts.parse_raw(ft.read())

    with output_zbd.open("wb") as fb:
        write_interp(fb, scripts.__root__)


def interp_from_zbd_command(args: Namespace) -> None:
    output_json = output_resolve(args.input_zbd, args.output_json, ".json")
    interp_zbd_to_json(args.input_zbd, output_json)


def interp_from_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("interp", description=__doc__)
    parser.set_defaults(command=interp_from_zbd_command)
    parser.add_argument("input_zbd", type=path_exists)
    parser.add_argument("output_json", type=dir_exists, default=None, nargs="?")


def interp_to_zbd_command(args: Namespace) -> None:
    output_zbd = output_resolve(args.input_json, args.output_zbd, ".zbd")
    interp_json_to_zbd(args.input_json, output_zbd)


def interp_to_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("interp", description=__doc__)
    parser.set_defaults(command=interp_to_zbd_command)
    parser.add_argument("input_json", type=path_exists)
    parser.add_argument("output_zbd", type=dir_exists, default=None, nargs="?")
