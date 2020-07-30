from contextlib import contextmanager
from typing import Any, Container, Iterator, Type, TypeVar, Union

from typing_extensions import Protocol

T = TypeVar("T", bound="Comparable")


class Comparable(Protocol):
    def __lt__(self: T, other: T) -> bool:
        pass

    def __le__(self: T, other: T) -> bool:
        pass

    def __gt__(self: T, other: T) -> bool:
        pass

    def __ge__(self: T, other: T) -> bool:
        pass


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


class Mech3MaterialError(Mech3Error):
    """An error when writing a texture."""


def _assert_base(  # pylint: disable=too-many-arguments
    result: bool,
    operator: str,
    name: str,
    expected: Any,
    actual: Any,
    location: Union[int, str],
    error_class: Type[Mech3Error] = Mech3ParseError,
) -> None:
    if not result:
        raise error_class(f"{name}: {actual!r} {operator} {expected!r} (at {location})")


def assert_eq(
    name: str,
    expected: T,
    actual: T,
    location: Union[int, str],
    error_class: Type[Mech3Error] = Mech3ParseError,
) -> None:
    result = actual == expected
    _assert_base(result, "==", name, expected, actual, location, error_class)


def assert_ne(
    name: str,
    expected: T,
    actual: T,
    location: Union[int, str],
    error_class: Type[Mech3Error] = Mech3ParseError,
) -> None:
    result = actual != expected
    _assert_base(result, "!=", name, expected, actual, location, error_class)


def assert_lt(
    name: str,
    expected: T,
    actual: T,
    location: Union[int, str],
    error_class: Type[Mech3Error] = Mech3ParseError,
) -> None:
    result = actual < expected
    _assert_base(result, "<", name, expected, actual, location, error_class)


def assert_le(
    name: str,
    expected: T,
    actual: T,
    location: Union[int, str],
    error_class: Type[Mech3Error] = Mech3ParseError,
) -> None:
    result = actual <= expected
    _assert_base(result, "<=", name, expected, actual, location, error_class)


def assert_gt(
    name: str,
    expected: T,
    actual: T,
    location: Union[int, str],
    error_class: Type[Mech3Error] = Mech3ParseError,
) -> None:
    result = actual > expected
    _assert_base(result, ">", name, expected, actual, location, error_class)


def assert_ge(
    name: str,
    expected: T,
    actual: T,
    location: Union[int, str],
    error_class: Type[Mech3Error] = Mech3ParseError,
) -> None:
    result = actual >= expected
    _assert_base(result, ">=", name, expected, actual, location, error_class)


def assert_in(
    name: str,
    expected: Container[T],
    actual: T,
    location: Union[int, str],
    error_class: Type[Mech3Error] = Mech3ParseError,
) -> None:
    result = actual in expected
    _assert_base(result, "in", name, expected, actual, location, error_class)


def assert_between(  # pylint: disable=too-many-arguments
    name: str,
    expected_low: T,
    expected_high: T,
    actual: T,
    location: Union[int, str],
    error_class: Type[Mech3Error] = Mech3ParseError,
) -> None:
    if expected_low > actual or actual > expected_high:
        raise error_class(
            f"{name}: {expected_low!r} <= {actual!r} <= {expected_high!r} (at {location})"
        )


@contextmanager
def assert_ascii(
    name: str,
    actual: bytes,
    location: Union[int, str],
    error_class: Type[Mech3Error] = Mech3ParseError,
) -> Iterator[None]:
    try:
        yield
    except UnicodeDecodeError:
        raise error_class(f"{name}: {actual!r} is not ASCII (at {location})")
