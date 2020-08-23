from math import copysign
from typing import cast

from .models import Matrix

assert (
    copysign(1.0, -0.0) < 0.0
), "Running on a platform that doesn't support signed zeros"


def extract_zero_signs(*values: float) -> int:
    """Extract the zero sign from floats (i.e. if the value is 0.0 or -0.0).

    This is required for complete binary accuracy, since in Python, ``0.0 == -0.0``.
    So when we compare against the calculated matrix or identity matrix, the
    zero sign will be ignored. This function saves them for writing.
    """
    signs = 0
    for i, value in enumerate(values):
        bit = 1 << i
        if value == 0.0 and copysign(1.0, value) < 0.0:
            signs |= bit
    return signs


def apply_zero_signs(signs: int, matrix: Matrix) -> Matrix:
    """Apply the zero sign to floats (i.e. if the value is 0.0 or -0.0).

    This is required for complete binary accuracy, since in Python, ``0.0 == -0.0``.
    So when we compare against the calculated matrix or identity matrix, the
    zero sign will be ignored. This function applies them from reading.
    """
    values = []
    for i, value in enumerate(matrix):
        bit = 1 << i
        if value == 0.0:
            has_sign = copysign(1.0, value) < 0.0
            has_bit = (signs & bit) == bit
            if has_sign != has_bit:
                value *= -1.0
        values.append(value)
    return cast(Matrix, tuple(values))
