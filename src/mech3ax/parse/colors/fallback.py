def _calc_lerp888(ushort: int) -> bytes:
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


LERP888 = [_calc_lerp888(value) for value in range(0x10000)]


def _calc_lerp5(value: int) -> int:
    """Linear interpolate from 8 bits to 5 bits."""
    return int(value * 31.0 / 255.0 + 0.5)


def _calc_lerp6(value: int) -> int:
    """Linear interpolate from 8 bits to 6 bits."""
    return int(value * 63.0 / 255.0 + 0.5)


LERP5 = [_calc_lerp5(value) for value in range(0x100)]
LERP6 = [_calc_lerp6(value) for value in range(0x100)]


def rgb565to888(colors: bytes) -> bytes:
    length = len(colors)
    values = bytearray(length * 3 // 2)
    it = iter(colors)
    i = 0
    for one, two in zip(it, it):
        color = two << 8 | one
        values[i : i + 3] = LERP888[color]
        i += 3
    return bytes(values)


def rgb888to565(colors: bytes) -> bytes:
    length = len(colors)
    values = bytearray(length * 2 // 3)
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


def check_palette(palette_count: int, image_data: bytes) -> bool:
    return all(index < palette_count for index in image_data)


__all__ = ["rgb565to888", "rgb888to565", "check_palette"]
