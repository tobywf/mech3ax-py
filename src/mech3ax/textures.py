from io import BytesIO
from struct import Struct, unpack_from
from zipfile import ZipFile

from PIL import Image

from .utils import ascii_zero

TEXTURE_INFO = Struct("<6I")
TEXTURE_RECORD = Struct("<32s2I")
TEXTURE_HEADER = Struct("<I2HI2H")


def rgb16(pixels):
    for pixel in pixels:
        yield ((pixel >> 11) & 0b11111) << 3
        yield ((pixel >> 5) & 0b111111) << 2
        yield ((pixel >> 0) & 0b11111) << 3


def _extract_texture(data, start, name):  # pylint: disable=too-many-locals
    fmt, width, height, zero, palette_count, stretch = TEXTURE_HEADER.unpack_from(
        data, start
    )
    assert zero == 0, f"header: zero {name}"
    offset = start + TEXTURE_HEADER.size
    size = width * height

    alpha = None

    # This could probably be generalised:
    #   3 = 0b00000011  (rgb, simple alpha)
    #   5 = 0b00000101  (rgb, no alpha)
    #  11 = 0b00001011  (rgb, full alpha)
    # 165 = 0b10100101  (pal, no alpha)
    # 171 = 0b10101011  (pal, full alpha)

    if fmt in (3, 5, 11):
        pixels = unpack_from(f"<{size}H", data, offset)
        offset += size * 2
        img = Image.frombytes("RGB", (width, height), bytes(rgb16(pixels)))

        if fmt == 11:
            alpha = data[offset : offset + size]
        elif fmt == 3:
            alpha = bytes(255 if pixel else 0 for pixel in pixels)

    elif fmt in (165, 171):
        indices = data[offset : offset + size]
        offset += size

        if fmt == 171:
            alpha = data[offset : offset + size]
            offset += size

        palette = unpack_from(f"<{palette_count}H", data, offset)
        offset += palette_count * 2

        img = Image.frombytes("P", (width, height), indices)
        img.putpalette(bytes(rgb16(palette)))

        if alpha:
            # can't save palette + alpha as PNG
            img = img.convert("RGB")
    else:
        raise ValueError(f"Unknown format {fmt} for texture {name}")

    if alpha:
        mask = Image.frombytes("L", (width, height), alpha)
        img.putalpha(mask)

    if stretch == 0:
        pass
    elif stretch == 1:
        img = img.resize((width * 2, height), resample=Image.BICUBIC)
    elif stretch == 2:
        img = img.resize((width, height * 2), resample=Image.BICUBIC)
    elif stretch == 3:
        img = img.resize((width * 2, height * 2), resample=Image.BICUBIC)
    else:
        raise ValueError(f"Unknown stretch {stretch} for texture {name}")

    return img


def extract_textures(data):
    zero1, one, zero2, count, zero3, zero4 = TEXTURE_INFO.unpack_from(data, 0)
    assert zero1 == 0, "info: zero 1"
    assert zero2 == 0, "info: zero 2"
    assert zero3 == 0, "info: zero 3"
    assert zero4 == 0, "info: zero 4"
    assert one == 1, "info: one"

    offset = TEXTURE_INFO.size
    for i in range(count):
        name, start, magic = TEXTURE_RECORD.unpack_from(data, offset)
        assert magic == 0xFFFFFFFF, f"record: magic {i}"
        name = ascii_zero(name)
        yield name, _extract_texture(data, start, name)
        offset += TEXTURE_RECORD.size


def texture_archives_to_zip(output_file, *archive_paths):
    with ZipFile(output_file, "w") as z:
        for archive_path in archive_paths:
            with archive_path.open("rb") as f:
                data = f.read()

            for name, img in extract_textures(data):
                with BytesIO() as f:
                    img.save(f, format="png")
                    z.writestr(f"{name}.png", f.getvalue())
