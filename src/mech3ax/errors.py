from typing import Type, TypeVar, Union

T = TypeVar("T")


class Mech3Error(Exception):
    """Base error for all errors in the library."""


class Mech3InternalError(Mech3Error):
    """An unexpected, internal error - usually related to a dependency"""


class Mech3ParseError(Mech3Error):
    """An error when parsing data."""


class Mech3ArchiveError(Mech3ParseError):
    """An error when parsing a ZArchive."""


class Mech3TextureError(Mech3Error):
    """An error when writing a texture."""


def assert_value_plain(
    name: str, expected: T, actual: T, error_class: Type[Mech3Error] = Mech3ParseError
) -> None:
    if actual != expected:
        raise error_class(f"Expected {name} to be {expected!r}, but was {actual!r}")


def assert_value(
    name: str,
    expected: T,
    actual: T,
    location: Union[int, str],
    error_class: Type[Mech3Error] = Mech3ParseError,
) -> None:
    if actual != expected:
        raise error_class(
            f"Expected {name} to be {expected!r}, but was {actual!r} (at {location})"
        )
