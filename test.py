import filecmp
from argparse import ArgumentParser
from logging.config import dictConfig
from pathlib import Path

from mech3ax.convert.interp import interp_json_to_zbd, interp_zbd_to_json
from mech3ax.convert.resources import messages_dll_to_json
from mech3ax.convert.sounds import sounds_zbd_to_zip, sounds_zip_to_zbd
from mech3ax.convert.textures import textures_zbd_to_zip, textures_zip_to_zbd
from mech3ax.errors import Mech3Error
from mech3ax.parse.resources import LocaleID


def compare(one: Path, two: Path) -> None:
    if not filecmp.cmp(one, two, shallow=False):
        print("*** MISMATCH ***", one, two)


class Tester:
    def __init__(self, base_path: Path, output_base: Path):
        self.base_path = base_path
        output_base.mkdir(exist_ok=True)
        # self.default = self.base_path / "v1.2-us-post" / "zbd"

        self.versions = sorted(
            (
                (path.name, path / "zbd", output_base / path.name)
                for path in self.base_path.iterdir()
                if path.is_dir() and path.name != "demo"
            ),
            key=lambda value: value[0],
            reverse=True,
        )

        for _, _, output_dir in self.versions:
            output_dir.mkdir(exist_ok=True)

    def test_sounds(self) -> None:
        print("--- SOUNDS ---")
        for name, zbd_dir, output_base in self.versions:
            output_dir = output_base / "sounds"
            output_dir.mkdir(exist_ok=True)

            print(name, "soundsL.zbd")
            input_zbd = zbd_dir / "soundsL.zbd"
            sounds_zbd_to_zip(input_zbd, output_dir / "soundsL.zip")
            output_zbd = output_dir / "soundsL.zbd"
            sounds_zip_to_zbd(output_dir / "soundsL.zip", output_zbd)
            compare(input_zbd, output_zbd)

            print(name, "soundsH.zbd")
            input_zbd = zbd_dir / "soundsH.zbd"
            sounds_zbd_to_zip(input_zbd, output_dir / "soundsH.zip")
            output_zbd = output_dir / "soundsH.zbd"
            sounds_zip_to_zbd(output_dir / "soundsH.zip", output_zbd)
            compare(input_zbd, output_zbd)

    def test_interp(self) -> None:
        print("--- INTERP ---")
        for name, zbd_dir, output_base in self.versions:
            output_dir = output_base / "interp"
            output_dir.mkdir(exist_ok=True)

            print(name, "interp.zbd")
            input_zbd = zbd_dir / "interp.zbd"
            interp_zbd_to_json(input_zbd, output_dir / "interp.json")
            output_zbd = output_dir / "interp.zbd"
            interp_json_to_zbd(output_dir / "interp.json", output_zbd)
            compare(input_zbd, output_zbd)

    def test_resources(self) -> None:
        print("--- RESOURCES ---")
        for name, zbd_dir, output_base in self.versions:
            locale_id = LocaleID.German if "de" in name else LocaleID.English

            print(name, "Mech3Msg.dll", locale_id)
            input_dll = zbd_dir.parent / "Mech3Msg.dll"
            output_json = output_base / "Mech3Msg.json"
            messages_dll_to_json(input_dll, output_json, locale_id)

    def test_textures(self) -> None:
        print("--- INTERP ---")
        for name, zbd_dir, output_base in self.versions:
            output_dir = output_base / "textures"
            output_dir.mkdir(exist_ok=True)

            texture_zbds = list(zbd_dir.rglob("*tex*.zbd")) + [zbd_dir / "rimage.zbd"]
            for input_zbd in sorted(texture_zbds):
                rel_path = input_zbd.relative_to(zbd_dir)
                mission = rel_path.parent.name
                if not mission:
                    zip_name = f"{input_zbd.stem}.zip"
                    zbd_name = f"{input_zbd.stem}.zbd"
                else:
                    zip_name = f"{mission}-{input_zbd.stem}.zip"
                    zbd_name = f"{mission}-{input_zbd.stem}.zbd"

                zip_path = output_dir / zip_name
                output_zbd = output_dir / zbd_name
                print(name, mission, input_zbd.name)
                textures_zbd_to_zip(input_zbd, zip_path)
                try:
                    textures_zip_to_zbd(zip_path, output_zbd)
                except Mech3Error as e:
                    print("*** ERROR ***", e)
                else:
                    compare(input_zbd, output_zbd)


def configure_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "formatters": {
                "simple": {"format": "%(levelname)-8s - %(message)s"},
                "detailed": {
                    "format": "[%(asctime)s] %(levelname)-8s - %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "ERROR",
                    "formatter": "simple",
                    "stream": "ext://sys.stdout",
                },
                "logfile": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "detailed",
                    "filename": "test.log",
                    "encoding": "utf-8",
                    "maxBytes": 10000000,  # 10 MB
                    "backupCount": 1,
                },
            },
            "loggers": {
                "mech3ax": {
                    "level": "DEBUG",
                    "handlers": ["logfile", "console"],
                    "propagate": False,
                },
            },
            # "root": {"level": "WARNING", "handlers": ["console"]},
            "disable_existing_loggers": False,
        }
    )


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "versions_dir", type=lambda value: Path(value).resolve(strict=True)
    )
    parser.add_argument(
        "output_dir", type=lambda value: Path(value).resolve(strict=True)
    )
    args = parser.parse_args()

    configure_logging()
    tester = Tester(args.versions_dir, args.output_dir)
    # tester.test_sounds()
    # tester.test_interp()
    # tester.test_resources()
    # tester.test_textures()


if __name__ == "__main__":
    main()
