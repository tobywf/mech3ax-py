"""Convert texture and image files to ZIP files.

The conversion is lossless and produces a binary accurate output by default.
"""
from __future__ import annotations

from argparse import Namespace, _SubParsersAction
from pathlib import Path
from typing import List, Optional
from zipfile import ZipFile

from PIL import Image
from pydantic import BaseModel

from ..parse.textures import DecodedTexture, TextureFlag, read_textures, write_textures
from .utils import Base64, dir_exists, output_resolve, path_exists

MANIFEST = "manifest.json"


class TextureFlagExpander(BaseModel):
    HasAlpha: bool
    NoAlpha: bool
    FullAlpha: bool
    BytesPerPixels2: bool = True
    UseGlobalPalette: bool = False
    ImageLoaded: bool = False
    AlphaLoaded: bool = False
    PaletteLoaded: bool = False

    def to_flag(self) -> TextureFlag:
        combination = TextureFlag(0)
        for name, value in self.dict().items():
            # always check the flag name
            flag = TextureFlag.__members__[name]
            if value:
                combination |= flag
        return combination

    @classmethod
    def from_flag(cls, combination: TextureFlag) -> TextureFlagExpander:
        return cls(
            **{
                name: flag(combination)
                for name, flag in TextureFlag.__members__.items()
            }
        )


class TextureInfo(BaseModel):
    name: str
    mode: str
    flags: TextureFlagExpander
    stretch: int = 0
    palette_count: int = 0
    palette_data: Optional[Base64] = None


class TextureManifest(BaseModel):
    class Config:
        json_encoders = {bytes: Base64.to_str}

    __root__: List[TextureInfo]


def textures_zbd_to_zip(
    input_zbd: Path, output_zip: Path, do_stretch: bool = False
) -> None:
    with ZipFile(output_zip, "w") as z:
        data = input_zbd.read_bytes()

        textures = []
        for texture in read_textures(data, do_stretch=do_stretch):
            with z.open(f"{texture.name}.png", mode="w") as f:
                texture.image.save(f, format="png")
            info = TextureInfo(
                name=texture.name,
                mode=texture.image.mode,
                flags=TextureFlagExpander.from_flag(texture.flag),
                stretch=texture.stretch,
                palette_count=texture.palette_count,
                palette_data=texture.palette_data,
            )
            textures.append(info)

        manifest = TextureManifest(__root__=textures)
        z.writestr(MANIFEST, manifest.json(exclude_defaults=True, indent=2))


def textures_zip_to_zbd(input_zip: Path, output_zbd: Path) -> None:
    with ZipFile(input_zip, "r") as z:
        with z.open(MANIFEST, "r") as ft:
            manifest = TextureManifest.parse_raw(ft.read())

        def load_texture(info: TextureInfo) -> DecodedTexture:
            with z.open(f"{info.name}.png", mode="r") as f:
                img = Image.open(f)
                img.load()

            return DecodedTexture(
                info.name,
                img,
                info.flags.to_flag(),
                info.stretch,
                info.palette_count,
                info.palette_data,
            )

        entries = (load_texture(info) for info in manifest.__root__)

        with output_zbd.open("wb") as f:
            write_textures(f, entries)


def textures_from_zbd_command(args: Namespace) -> None:
    output_zip = output_resolve(args.input_zbd, args.output_zip, ".zip")
    textures_zbd_to_zip(args.input_zbd, output_zip, args.do_stretch)


def textures_from_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("textures", description=__doc__)
    parser.set_defaults(command=textures_from_zbd_command)
    parser.add_argument("input_zbd", type=path_exists)
    parser.add_argument("output_zip", type=dir_exists, default=None, nargs="?")
    parser.add_argument(
        "--do-stretch",
        action="store_true",
        help=(
            "Stretch textures according to the stretch value. This is great for "
            "using the textures, but bad for re-creating the ZBD."
        ),
    )


def textures_to_zbd_command(args: Namespace) -> None:
    output_zbd = output_resolve(args.input_zip, args.output_zbd, ".zbd")
    textures_zip_to_zbd(args.input_zip, output_zbd)


def textures_to_zbd_subparser(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("textures", description=__doc__)
    parser.set_defaults(command=textures_to_zbd_command)
    parser.add_argument("input_zip", type=path_exists)
    parser.add_argument("output_zbd", type=dir_exists, default=None, nargs="?")
