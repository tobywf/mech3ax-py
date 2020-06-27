import json
from logging.config import dictConfig
from pathlib import Path
from typing import Any, Optional


def json_dump(path: Path, obj: Any, sort_keys: bool = False) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=sort_keys)


def path_exists(arg: str) -> Path:
    return Path(arg).resolve(strict=True)


def dir_exists(arg: str) -> Path:
    path = Path(arg)
    return path.parent.resolve(strict=True) / path.name


def output_resolve(input_path: Path, output_path: Optional[Path], suffix: str) -> Path:
    filename = input_path.with_suffix(suffix).name
    if not output_path:
        return Path.cwd() / filename
    if not output_path.name or output_path.is_dir():
        return output_path / filename
    return output_path


def configure_debug_logging(verbosity: str = "DEBUG") -> None:
    dictConfig(
        {
            "version": 1,
            "formatters": {
                "detailed": {
                    "format": "[%(asctime)s] %(levelname)-8s - %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "formatter": "detailed",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "mech3ax": {
                    "level": verbosity,
                    "handlers": ["console"],
                    "propagate": False,
                },
            },
            "root": {"level": "ERROR", "handlers": ["console"]},
            "disable_existing_loggers": False,
        }
    )
