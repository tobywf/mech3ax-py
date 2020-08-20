import logging
import warnings
from struct import pack, unpack
from typing import TYPE_CHECKING

LOG = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .fallback import euler_to_matrix
else:
    try:
        from ._native import euler_to_matrix
    except ImportError:
        MSG = "C extension could not be imported, comparisons may fail"
        warnings.warn(MSG)
        LOG.warning(MSG)
        from .fallback import euler_to_matrix


def force_single_prec(value: float) -> float:
    """Force a Python float (really a 64-bit IEEE 754 double precision floating
    point number on most machines) to the value it would have as a 32-bit IEEE
    754 single precision floating point number.

    This could work on any machine, as ``struct`` explicitly packs floats as
    IEEE 754 formats "regardless of the floating-point format used by the
    platform".
    """
    (value,) = unpack("f", pack("f", value))
    return value


__all__ = ["force_single_prec", "euler_to_matrix"]
