import argparse
import sys

from .interp import interp_from_zbd_subparser, interp_to_zbd_subparser
from .reader import reader_from_zbd_subparser, reader_to_zbd_subparser
from .resources import messages_from_dll_subparser
from .sounds import sounds_from_zbd_subparser, sounds_to_zbd_subparser
from .textures import textures_from_zbd_subparser, textures_to_zbd_subparser
from .utils import configure_debug_logging


def main_from_zbd() -> None:
    parser = argparse.ArgumentParser()

    def no_command(_args: argparse.Namespace) -> None:
        parser.print_help()

    parser.set_defaults(command=no_command)
    subparsers = parser.add_subparsers(dest="subparser_name")
    interp_from_zbd_subparser(subparsers)
    reader_from_zbd_subparser(subparsers)
    messages_from_dll_subparser(subparsers)
    sounds_from_zbd_subparser(subparsers)
    textures_from_zbd_subparser(subparsers)

    configure_debug_logging("INFO")

    try:
        args = parser.parse_args()
    except Exception as e:  # pylint: disable=broad-except
        sys.stdout.write(str(e) + "\n")
    else:
        args.command(args)


def main_to_zbd() -> None:
    parser = argparse.ArgumentParser()

    def no_command(_args: argparse.Namespace) -> None:
        parser.print_help()

    parser.set_defaults(command=no_command)
    subparsers = parser.add_subparsers(dest="subparser_name")
    interp_to_zbd_subparser(subparsers)
    reader_to_zbd_subparser(subparsers)
    sounds_to_zbd_subparser(subparsers)
    textures_to_zbd_subparser(subparsers)

    configure_debug_logging("INFO")

    try:
        args = parser.parse_args()
    except Exception as e:  # pylint: disable=broad-except
        sys.stdout.write(str(e) + "\n")
    else:
        args.command(args)
