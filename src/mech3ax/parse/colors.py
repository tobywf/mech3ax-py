import logging
from typing import Sequence

from PIL import Image

from ..errors import Mech3TextureError, assert_value

LOG = logging.getLogger(__name__)


def calc_lerp888(ushort: int) -> bytes:
    """Linear interpolate from 5/6/5 bits to 8/8/8 bits.

    By naively shifting the values, the bottom bits will always be
    zero, and so the color will never have full brightness.
    """
    bits = (ushort >> 11) & 0b11111
    red = int(bits * 255.0 / 31.0 + 0.5)
    bits = (ushort >> 5) & 0b111111
    green = int(bits * 255.0 / 63.0 + 0.5)
    bits = (ushort >> 0) & 0b11111
    blue = int(bits * 255.0 / 31.0 + 0.5)
    return bytes([red, green, blue])


LERP888 = [calc_lerp888(value) for value in range(0x10000)]


def rgb565to888(colors: Sequence[int]) -> bytes:
    length = len(colors)
    rgb = bytearray(length * 3)
    i = 0
    for color in colors:
        rgb[i : i + 3] = LERP888[color]
        i += 3
    return bytes(rgb)


def simple_alpha565(colors: Sequence[int]) -> bytes:
    alpha = bytearray(len(colors))
    for i, color in enumerate(colors):
        alpha[i] = 0 if color == 0 else 255
    return bytes(alpha)


def calc_lerp5(value: int) -> int:
    """Linear interpolate from 8 bits to 5 bits."""
    return int(value * 31.0 / 255.0 + 0.5)


def calc_lerp6(value: int) -> int:
    """Linear interpolate from 8 bits to 6 bits."""
    return int(value * 63.0 / 255.0 + 0.5)


LERP5 = [calc_lerp5(value) for value in range(0x100)]
LERP6 = [calc_lerp6(value) for value in range(0x100)]


def rgb888to565(colors: bytes) -> bytes:
    count = len(colors)
    values = bytearray(count // 3 * 2)
    it = iter(colors)
    i = 0
    for red, green, blue in zip(it, it, it):
        bits = LERP6[green]
        high = (bits << 5) & 0xFF | (LERP5[blue])
        values[i] = high
        i += 1
        low = (LERP5[red] << 3) | (bits >> 3)
        values[i] = low
        i += 1
    return bytes(values)


def rgb_to_palette(img: Image, palette: bytes, name: str) -> bytes:
    """Convert an RGB image to palette entries.

    Pillow's quantize is pretty broken, so don't use that.

    :param img: The image to be converted. Must be RGB.
    :param palette: The colors of the palette. Must be RGB.
    :param name: The name of the image (for debug).
    :return: The corresponding indices in the palette for each pixel.

    :raises Mech3TextureError: if the image is not RGB
    :raises Mech3TextureError: if the palette contains duplicate colors
    :raises Mech3TextureError: if the palette does not contain a color in the image
    """
    assert_value("image mode", "RGB", img.mode, name, Mech3TextureError)

    rgb_to_index = {}
    it = iter(palette)
    for i, rgb in enumerate(zip(it, it, it)):
        if rgb in rgb_to_index:
            # this occurs frequently; but the original images use the first color/index
            LOG.debug("Duplicate color found in palette of %s", name)
        else:
            rgb_to_index[rgb] = i

    size = img.width * img.height
    buf = bytearray(size)
    it = iter(img.tobytes())
    try:
        for i, rgb in enumerate(zip(it, it, it)):
            buf[i] = rgb_to_index[rgb]
    except KeyError:
        raise Mech3TextureError(f"Color not found in palette of {name}")

    return bytes(buf)
