"""Convert 'mech3msg.dll' files to JSON files.

The conversion is lossless, but can only be performed one-way.
"""
from argparse import Namespace, _SubParsersAction
from pathlib import Path

import pefile

from ..parse.resources import LocaleID, read_messages
from .utils import dir_exists, json_dump, output_resolve, path_exists


def messages_dll_to_json(
    input_dll: Path, output_json: Path, locale_id: LocaleID = LocaleID.English
) -> None:
    pe = pefile.PE(str(input_dll.resolve(strict=True)))
    messages = read_messages(pe, locale_id)
    json_dump(output_json, messages, sort_keys=True)


def messages_from_dll_command(args: Namespace) -> None:
    output_json = output_resolve(args.input_dll, args.output_json, ".json")
    messages_dll_to_json(args.input_dll, output_json, args.locale_id)


def messages_from_dll_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("messages", description=__doc__)
    parser.set_defaults(command=messages_from_dll_command)
    parser.add_argument("input_dll", type=path_exists)
    parser.add_argument("output_json", type=dir_exists, default=None, nargs="?")
    parser.add_argument(
        "--locale-id", type=LocaleID.from_string, choices=list(LocaleID)
    )
