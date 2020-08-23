from typing import BinaryIO, List, Tuple

from mech3ax.errors import assert_ascii, assert_eq

from ..utils import BinReader
from .models import TEXTURE_INFO, Texture

SUFFIXES = tuple((s, s.decode("ascii"), len(s)) for s in (b"tif", b"TIF", b""))


def _ascii_zterm_suffix(buf: bytes) -> Tuple[str, str]:
    """Return a string from an ASCII-encoded, zero-terminated buffer.

    The first null character is searched for. Data following the terminator
    is verified as the suffix followed by null characters.

    :raises ValueError: If no null character was found in the buffer.
    :raises ValueError: If unexpected characters follow the terminator.
    :raises UnicodeDecodeError: If the string is not ASCII-encoded.
    """
    null_index = buf.find(b"\0")
    if null_index < 0:  # pragma: no cover
        raise ValueError("Null terminator not found")

    # they used a "trick" to encode the texture names: replace the '.' in filenames
    # with a null character. however, some texture names have no suffix.
    # additionally, for long filenames, the suffix is cut off
    for suffix_bytes, suffix_ascii, suffix_len in SUFFIXES:  # pragma: no branch
        compare = bytearray(max(len(buf), null_index + suffix_len))
        compare[: null_index + 1] = buf[: null_index + 1]
        compare[null_index + 1 : null_index + suffix_len + 1] = suffix_bytes

        if buf == bytes(compare[: len(buf)]):
            return (buf[:null_index].decode("ascii"), suffix_ascii)

    raise ValueError("No match for suffixes")  # pragma: no cover


def read_textures(reader: BinReader, count: int) -> List[Texture]:
    textures = []
    for _ in range(count):
        zero00, zero04, texture_raw, used, index, mone36 = reader.read(TEXTURE_INFO)
        # not sure. a pointer to the previous texture in the global array? or a
        # pointer to the texture?
        assert_eq("field 00", 0, zero00, reader.prev + 0)
        # a non-zero value here causes additional dynamic code to be called
        assert_eq("field 04", 0, zero04, reader.prev + 4)
        with assert_ascii("texture", texture_raw, reader.prev + 8):
            texture, suffix = _ascii_zterm_suffix(texture_raw)
        # 2 if the texture is used, 0 if the texture is unused
        # 1 or 3 if the texture is being processed (deallocated?)
        assert_eq("used", 2, used, reader.prev + 28)
        # stores the texture's index in the global texture array
        assert_eq("index", 0, index, reader.prev + 32)
        # not sure. a pointer to the next texture in the global array? or
        # something to do with mipmaps?
        assert_eq("field 32", -1, mone36, reader.prev + 36)
        textures.append(Texture(name=texture, suffix=suffix))

    return textures


def write_textures(f: BinaryIO, textures: List[Texture]) -> None:
    for texture in textures:
        name_raw = b"\0".join(
            [texture.name.encode("ascii"), texture.suffix.encode("ascii")]
        )
        f.write(TEXTURE_INFO.pack(0, 0, name_raw, 2, 0, -1))


def size_textures(count: int) -> int:
    return TEXTURE_INFO.size * count
