from io import BytesIO
from struct import Struct, unpack_from
from zipfile import ZipFile

from PIL import Image

from .utils import ascii_zterm

TEXTURE_INFO = Struct("<6I")
TEXTURE_RECORD = Struct("<32s2I")
TEXTURE_HEADER = Struct("<I2HI2H")


def rgb16(pixels):
    for pixel in pixels:
        yield ((pixel >> 11) & 0b11111) << 3
        yield ((pixel >> 5) & 0b111111) << 2
        yield ((pixel >> 0) & 0b11111) << 3


def _stretch(img, stretch, name):
    if stretch in (0, 3):
        # unsure what stretch 3 implies. images look fine as is
        return img
    if stretch == 1:
        return img.resize((img.width * 2, img.height), resample=Image.BICUBIC)
    if stretch == 2:
        return img.resize((img.width, img.height * 2), resample=Image.BICUBIC)
    raise ValueError(f"Unknown stretch {stretch} for texture {name}")


def _extract_texture(data, start, name):  # pylint: disable=too-many-locals
    fmt, width, height, zero, palette_count, stretch = TEXTURE_HEADER.unpack_from(
        data, start
    )
    offset = start + TEXTURE_HEADER.size
    if zero != 0:
        raise ValueError(
            f"Expected field 4 to be 0 for texture {name} (but was {zero})"
        )
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
            offset += size
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

    return _stretch(img, stretch, name)


def extract_textures(data):
    zero1, one, zero2, count, zero3, zero4 = TEXTURE_INFO.unpack_from(data, 0)
    if zero1 != 0:
        raise ValueError(f"Expected field 1 to be 0 (but was {zero1})")
    if one != 1:
        raise ValueError(f"Expected field 2 to be 1 (but was {one})")
    if zero2 != 0:
        raise ValueError(f"Expected field 3 to be 0 (but was {zero2})")
    if zero3 != 0:
        raise ValueError(f"Expected field 5 to be 0 (but was {zero3})")
    if zero4 != 0:
        raise ValueError(f"Expected field 6 to be 0 (but was {zero4})")

    offset = TEXTURE_INFO.size
    for i in range(count):
        name, start, magic = TEXTURE_RECORD.unpack_from(data, offset)
        if magic != 0xFFFFFFFF:
            raise ValueError(
                f"Expected record {i} magic to be 0xFFFFFFFF (but was {magic:08X})"
            )
        name = ascii_zterm(name)
        yield name, _extract_texture(data, start, name)
        offset += TEXTURE_RECORD.size


def texture_archives_to_zip(output_file, *archive_paths):
    with ZipFile(output_file, "w") as z:
        for archive_path in archive_paths:
            data = archive_path.read_bytes()

            for name, img in extract_textures(data):
                with BytesIO() as f:
                    img.save(f, format="png")
                    z.writestr(f"{name}.png", f.getvalue())
