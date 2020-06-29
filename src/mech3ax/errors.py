from typing import Container, Type, TypeVar, Union

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


def assert_eq(
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


def assert_in(
    name: str,
    expected: Container[T],
    actual: T,
    location: Union[int, str],
    error_class: Type[Mech3Error] = Mech3ParseError,
) -> None:
    if actual not in expected:
        raise error_class(
            f"Expected {name} to be one of {expected!r}, but was {actual!r} (at {location})"
        )
