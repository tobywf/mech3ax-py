import warnings
from zipfile import ZipFile

from .archive import extract_archive


def sound_archive_to_zip(output_file, base_path, sound_archive="soundsH.zbd"):
    data = (base_path / sound_archive).read_bytes()

    with warnings.catch_warnings(), ZipFile(output_file, "w") as z:
        # some sound files are duplicates, so don't spam users of this library
        warnings.filterwarnings("ignore", category=UserWarning)

        for name, filedata in extract_archive(data):
            z.writestr(name, filedata)

        # include any loose files
        for path in base_path.glob("*.wav"):
            z.writestr(path.name, path.read_bytes())
