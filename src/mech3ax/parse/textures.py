from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import IntFlag
from struct import Struct, unpack_from
from typing import BinaryIO, Iterable, Optional, Sequence, Tuple, cast

from PIL import Image

from ..errors import (
    Mech3InternalError,
    Mech3ParseError,
    Mech3TextureError,
    assert_eq,
    assert_in,
)
from .colors import rgb565to888, rgb888to565, rgb_to_palette, simple_alpha565
from .utils import BinReader, ascii_zterm

TEX_HEADER = Struct("<6I")
assert TEX_HEADER.size == 24, TEX_HEADER.size
TEX_ENTRY = Struct("<32s Ii")
assert TEX_ENTRY.size == 40, TEX_ENTRY.size
TEX_INFO = Struct("<I 2H I 2H")
assert TEX_INFO.size == 16, TEX_INFO.size

LOG = logging.getLogger(__name__)


class TextureFlag(IntFlag):
    # If set, 2 bytes per pixel, else 1 byte per pixel
    BytesPerPixels2 = 1 << 0
    HasAlpha = 1 << 1
    NoAlpha = 1 << 2
    FullAlpha = 1 << 3
    UseGlobalPalette = 1 << 4
    # these are used internally to track allocated buffers
    # if these are set in the file, they can be ignored
    ImageLoaded = 1 << 5
    AlphaLoaded = 1 << 6
    PaletteLoaded = 1 << 7

    def __call__(self, value: int) -> bool:
        return value & self == self

    @classmethod
    def check(cls, value: int) -> TextureFlag:
        if value == 0:
            raise ValueError(f"Undefined flag: {value}")
        mask = 0
        for flag in cls.__members__.values():
            if flag(value):
                mask |= flag.value
        if value != mask:
            raise ValueError(f"Undefined flag: {value}")
        return cls(value)


@dataclass
class DecodedTexture:
    name: str
    image: Image
    flag: TextureFlag
    stretch: int
    palette_count: int
    palette_data: Optional[bytes]


@dataclass
class EncodedTexture:  # pylint: disable=too-many-instance-attributes
    name: str
    flag: TextureFlag
    width: int
    height: int
    palette_count: int
    stretch: int
    image_data: bytes
    alpha_data: Optional[bytes]
    palette_data: Optional[bytes]


def stretch_img(img: Image, stretch: int) -> Image:
    if stretch == 1:
        return img.resize((img.width * 2, img.height), resample=Image.BICUBIC)
    if stretch == 2:
        return img.resize((img.width, img.height * 2), resample=Image.BICUBIC)
    if stretch == 3:
        return img.resize((img.width * 2, img.height * 2), resample=Image.BICUBIC)
    raise Mech3InternalError("stretch")


def _validate_texture_info(
    offset: int, flag: int, zero: int, stretch: int
) -> TextureFlag:
    assert_eq("field 8", 0, zero, offset)
    assert_in("stretch", (0, 1, 2, 3), stretch, offset)

    try:
        flag = TextureFlag.check(flag)
    except ValueError as e:
        raise Mech3ParseError(f"flag: {flag:02X} is invalid (at {offset})") from e

    # one byte per pixel support isn't implemented
    assert_eq(
        "2 bytes per pixel",
        True,
        TextureFlag.BytesPerPixels2(flag),
        offset,
        Mech3TextureError,
    )

    # global palette support isn't implemented
    assert_eq(
        "use global palette",
        False,
        TextureFlag.UseGlobalPalette(flag),
        offset,
        Mech3TextureError,
    )

    return flag


def _read_texture(  # pylint: disable=too-many-locals
    reader: BinReader, name: str, do_stretch: bool
) -> DecodedTexture:
    flag_raw, width, height, zero, palette_count, stretch = reader.read(TEX_INFO)

    LOG.debug(
        "Texture '%s', data at %d, flag 0x%02x, %d x %d, zero %d, palette %d, stretch %d",
        name,
        reader.prev,
        flag_raw,
        width,
        height,
        zero,
        palette_count,
        stretch,
    )

    flag = _validate_texture_info(reader.prev, flag_raw, zero, stretch)

    size = width * height

    LOG.debug("Reading image data at %d", reader.offset)
    alpha_data: Optional[bytes] = None

    has_full_alpha = TextureFlag.FullAlpha(flag)
    has_simple_alpha = TextureFlag.HasAlpha(flag) and not has_full_alpha

    if palette_count == 0:
        pixels = unpack_from(f"<{size}H", reader.data, reader.offset)
        reader.offset += size * 2
        if has_simple_alpha:
            alpha_data = simple_alpha565(pixels)
        image_data = rgb565to888(pixels)
    else:
        image_data = reader.read_bytes(size)
        in_range = all(index < palette_count for index in image_data)
        assert_eq(
            "image data (palette) in range",
            True,
            in_range,
            reader.prev,
            Mech3TextureError,
        )
        # if a palette image has simple alpha, then it would have to be constructed
        # after the palette data is loaded. however, this never seems to happen
        assert_eq(
            "has simple alpha", False, has_simple_alpha, reader.prev, Mech3TextureError,
        )

    if has_full_alpha:
        LOG.debug("Reading alpha data at %d", reader.offset)
        alpha_data = reader.read_bytes(size)

    palette_data: Optional[bytes] = None
    if palette_count == 0:
        img = Image.frombytes("RGB", (width, height), image_data)
    else:
        LOG.debug("Reading palette data at %d", reader.offset)
        colors = unpack_from(f"<{palette_count}H", reader.data, reader.offset)
        reader.offset += palette_count * 2

        img = Image.frombytes("P", (width, height), image_data)
        palette_data = rgb565to888(colors)
        img.putpalette(palette_data)

        if alpha_data:
            LOG.debug(
                "Texture '%s' uses palette and has alpha (converting to RGB)", name
            )
            # can't save palette + alpha as PNG
            img = img.convert("RGB")

    if alpha_data:
        mask = Image.frombytes("L", (width, height), alpha_data)
        img.putalpha(mask)

    if do_stretch and stretch > 0:
        img = stretch_img(img, stretch)

    return DecodedTexture(name, img, flag, stretch, palette_count, palette_data)


def read_textures(data: bytes, do_stretch: bool = True) -> Iterable[DecodedTexture]:
    reader = BinReader(data)
    LOG.debug("Reading texture data...")
    (zero1, has_entries, global_palette_count, count, zero2, zero3,) = reader.read(
        TEX_HEADER
    )
    LOG.debug(
        "Texture archive count %d, has entries %d, global palette %d (%d, %d, %d)",
        count,
        has_entries,
        global_palette_count,
        zero1,
        zero2,
        zero3,
    )

    assert_eq("field 00", 0, zero1, reader.prev + 0)
    assert_eq("has entries", 1, has_entries, reader.prev + 4)
    # global palette support isn't implemented
    assert_eq("global palette count", 0, global_palette_count, reader.prev + 8)
    assert_eq("field 16", 0, zero2, reader.prev + 16)
    assert_eq("field 20", 0, zero3, reader.prev + 20)

    table = []
    for i in range(count):
        LOG.debug("Reading entry %d at %d", i, reader.offset)
        name, start, palette_index = reader.read(TEX_ENTRY)
        # global palette support isn't implemented
        assert_eq("global palette index", -1, palette_index, reader.offset - 4)
        name = ascii_zterm(name)
        table.append((name, start))

    for name, start in table:
        assert_eq("offset", start, reader.offset, name)
        yield _read_texture(reader, name, do_stretch)

    LOG.debug("Read texture data")


def _convert_textures(
    texture: DecodedTexture, img: Image
) -> Tuple[bytes, Optional[bytes]]:
    mode = texture.image.mode
    name = texture.name

    has_palette = texture.palette_count != 0

    size = img.width * img.height

    palette_data: Optional[bytes] = None
    if has_palette:
        assert_eq(
            "has palette data",
            True,
            texture.palette_data is not None,
            name,
            Mech3TextureError,
        )

        if TextureFlag.FullAlpha(texture.flag):
            assert_eq("image mode", "RGBA", mode, name, Mech3TextureError)
            palette = cast(bytes, texture.palette_data)
            image_data = rgb_to_palette(img, palette, name)
            palette_data = rgb888to565(palette)
        else:
            assert_eq("image mode", "P", mode, name, Mech3TextureError)
            image_data = img.tobytes()

            # PIL always returns 256 palette entries
            component_count = texture.palette_count * 3
            palette = img.getpalette()
            assert_eq(
                "PIL palette size", 256 * 3, len(palette), name, Mech3InternalError
            )
            real_palette = palette[:component_count]
            palette_data = rgb888to565(real_palette)

        in_range = all(index < texture.palette_count for index in image_data)
        assert_eq(
            "image data (palette) in range", True, in_range, name, Mech3InternalError,
        )
    else:
        expected_mode = "RGBA" if TextureFlag.HasAlpha(texture.flag) else "RGB"
        assert_eq("image mode", expected_mode, mode, name, Mech3TextureError)

        image_data = rgb888to565(img.tobytes())
        assert_eq(
            "image data length", size * 2, len(image_data), name, Mech3InternalError
        )

    return image_data, palette_data


def write_textures(f: BinaryIO, textures: Iterable[DecodedTexture]) -> None:
    encoded = []
    for i, texture in enumerate(textures):
        mode = texture.image.mode
        LOG.debug("Encoding texture %d '%s' (%s)", i, texture.name, mode)

        assert_eq(
            "2 bytes per pixel",
            True,
            TextureFlag.BytesPerPixels2(texture.flag),
            texture.name,
            Mech3TextureError,
        )

        if mode == "RGBA":
            red, green, blue, alpha = texture.image.split()
            img = Image.merge("RGB", [red, green, blue])
            alpha_data = alpha.tobytes()
        elif mode in ("RGB", "P"):
            img = texture.image
            alpha_data = None
        else:
            raise Mech3TextureError(f"Unsupported mode {mode} for {texture.name!r}")

        if not TextureFlag.FullAlpha(texture.flag):
            # drop the simple/fake alpha
            alpha_data = None

        image_data, palette_data = _convert_textures(texture, img)

        enc = EncodedTexture(
            texture.name,
            texture.flag,
            img.width,
            img.height,
            texture.palette_count,
            texture.stretch,
            image_data,
            alpha_data,
            palette_data,
        )
        encoded.append(enc)

    _write_encoded_textures(f, encoded)


def _write_encoded_textures(f: BinaryIO, encoded: Sequence[EncodedTexture]) -> None:
    LOG.debug("Writing texture data...")

    count = len(encoded)
    LOG.debug("Texture archive count %d", count)
    f.write(TEX_HEADER.pack(0, 1, 0, count, 0, 0))

    offset = TEX_HEADER.size + TEX_ENTRY.size * count
    for i, texture in enumerate(encoded):
        LOG.debug("Writing entry %d '%s', start %d", i, texture.name, offset)
        raw_name = texture.name.encode("ascii")
        f.write(TEX_ENTRY.pack(raw_name, offset, -1))
        offset += TEX_INFO.size

        size = texture.width * texture.height

        has_palette = texture.palette_count != 0
        length = size if has_palette else size * 2
        assert_eq(
            "image data length",
            length,
            len(texture.image_data),
            texture.name,
            Mech3InternalError,
        )
        offset += length

        has_full_alpha = TextureFlag.FullAlpha(texture.flag)
        assert_eq(
            "has alpha data",
            has_full_alpha,
            texture.alpha_data is not None,
            texture.name,
            Mech3TextureError,
        )
        if has_full_alpha:
            assert_eq(
                "alpha data length",
                size,
                len(cast(bytes, texture.alpha_data)),
                texture.name,
                Mech3TextureError,
            )
            offset += size

        assert_eq(
            "has palette data",
            has_palette,
            texture.palette_data is not None,
            texture.name,
            Mech3TextureError,
        )
        if has_palette:
            length = texture.palette_count * 2
            assert_eq(
                "palette data length",
                length,
                len(cast(bytes, texture.palette_data)),
                texture.name,
                Mech3TextureError,
            )
            offset += length

    offset = TEX_HEADER.size + TEX_ENTRY.size * count
    for texture in encoded:
        LOG.debug(
            "Texture '%s', data at %d, flag 0x%02x, %d x %d, palette %d, stretch %d",
            texture.name,
            offset,
            texture.flag,
            texture.width,
            texture.height,
            texture.palette_count,
            texture.stretch,
        )
        info = TEX_INFO.pack(
            texture.flag,
            texture.width,
            texture.height,
            0,
            texture.palette_count,
            texture.stretch,
        )
        f.write(info)
        offset += TEX_INFO.size
        LOG.debug("Writing image data at %d", offset)
        f.write(texture.image_data)
        offset += len(texture.image_data)
        if texture.alpha_data:
            LOG.debug("Writing alpha data at %d", offset)
            f.write(texture.alpha_data)
            offset += len(texture.alpha_data)
        if texture.palette_data:
            LOG.debug("Writing palette data at %d", offset)
            f.write(texture.palette_data)
            offset += len(texture.palette_data)

    LOG.debug("Wrote texture data")
