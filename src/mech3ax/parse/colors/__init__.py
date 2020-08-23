import logging
import warnings
from typing import TYPE_CHECKING, Sequence

from PIL import Image

from mech3ax.errors import Mech3TextureError, assert_eq

LOG = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .fallback import rgb565to888, rgb888to565, check_palette
else:
    try:
        from ._native import rgb565to888, rgb888to565, check_palette
    except ImportError:
        MSG = "C extension could not be imported, textures will be slow"
        warnings.warn(MSG)
        LOG.warning(MSG)
        from .fallback import rgb565to888, rgb888to565, check_palette


def simple_alpha565(colors: Sequence[int]) -> bytes:
    alpha = bytearray(len(colors))
    for i, color in enumerate(colors):
        alpha[i] = 0 if color == 0 else 255
    return bytes(alpha)


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
    assert_eq("image mode", "RGB", img.mode, name, Mech3TextureError)

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


__all__ = [
    "rgb565to888",
    "rgb888to565",
    "check_palette",
    "simple_alpha565",
    "rgb_to_palette",
]
