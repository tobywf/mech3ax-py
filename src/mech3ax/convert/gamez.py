"""Convert 'gamez.zbd' files to ZIP files.

Incomplete.
"""
import logging
from argparse import Namespace, _SubParsersAction
from pathlib import Path

from ..parse.gamez import read_gamez
from .utils import dir_exists, output_resolve, path_exists

LOG = logging.getLogger(__name__)


def gamez_zbd_to_zip(input_zbd: Path, output_zip: Path) -> None:
    # with ZipFile(output_zip, "w") as z:
    data = input_zbd.read_bytes()
    gamez = read_gamez(data)
    data = None  # type: ignore
    with output_zip.open("w", encoding="utf-8") as f:
        f.write(gamez.json(exclude_defaults=True, indent=2))


def gamez_from_zbd_command(args: Namespace) -> None:
    output_zip = output_resolve(args.input_zbd, args.output_zip, ".zip")
    gamez_zbd_to_zip(args.input_zbd, output_zip)


def gamez_from_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("gamez", description=__doc__)
    parser.set_defaults(command=gamez_from_zbd_command)
    parser.add_argument("input_zbd", type=path_exists)
    parser.add_argument("output_zip", type=dir_exists, default=None, nargs="?")


# def gamez_to_zbd_command(args: Namespace) -> None:
#     output_zbd = output_resolve(args.input_zip, args.output_zbd, ".zbd")
#     gamez_zip_to_zbd(args.input_zip, output_zbd)


# def gamez_to_zbd_subparser(subparsers: _SubParsersAction) -> None:
#     parser = subparsers.add_parser("gamez", description=__doc__)
#     parser.set_defaults(command=gamez_to_zbd_command)
#     parser.add_argument("input_zip", type=path_exists)
#     parser.add_argument("output_zbd", type=dir_exists, default=None, nargs="?")
