import warnings
from struct import Struct
from zipfile import ZipFile

from .utils import ascii_zero

SOUND_FOOTER = Struct("<2I")
SOUND_RECORD = Struct("<2I64s76x")


def _extract_sounds(data):
    offset = len(data) - SOUND_FOOTER.size
    _, count = SOUND_FOOTER.unpack_from(data, offset)
    for _ in range(count):
        offset -= SOUND_RECORD.size  # walk the table backwards
        start, length, name = SOUND_RECORD.unpack_from(data, offset)
        name = ascii_zero(name)
        yield name, data[start : start + length]


def sound_archive_to_zip(output_file, base_path, sound_archive="soundsH.zbd"):
    with (base_path / sound_archive).open("rb") as f:
        data = f.read()

    with warnings.catch_warnings(), ZipFile(output_file, "w") as z:
        # some sound files are duplicates, so don't spam users of this library
        warnings.filterwarnings("ignore", category=UserWarning)

        for name, sound in _extract_sounds(data):
            z.writestr(name, sound)

        # include any loose files
        for path in base_path.glob("*.wav"):
            with path.open("rb") as f:
                z.writestr(path.name, f.read())
