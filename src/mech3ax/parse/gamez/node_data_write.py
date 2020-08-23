from math import copysign
from typing import BinaryIO, cast

from ..float import euler_to_matrix
from .models import IDENTITY_MATRIX, OBJECT3D, Matrix, Object3d


def _apply_zero_signs(signs: int, matrix: Matrix) -> Matrix:
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


def write_node_data_object3d(f: BinaryIO, object3d: Object3d) -> None:
    if object3d.rotation and object3d.translation:
        rot_x, rot_y, rot_z = object3d.rotation
        trans_x, trans_y, trans_z = object3d.translation
        if object3d.matrix:
            # in this case, we have the raw matrix with the correct zero signs
            matrix = object3d.matrix
        else:
            matrix = euler_to_matrix(rot_x, rot_y, rot_z)
            matrix = _apply_zero_signs(object3d.matrix_sign, matrix)
        flag_raw = 32
    else:
        rot_x = rot_y = rot_z = 0.0
        trans_x = trans_y = trans_z = 0.0
        matrix = _apply_zero_signs(object3d.matrix_sign, IDENTITY_MATRIX)
        flag_raw = 40

    data = OBJECT3D.pack(
        flag_raw,
        # opacity
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        rot_x,
        rot_y,
        rot_z,
        # scale
        1.0,
        1.0,
        1.0,
        *matrix,
        trans_x,
        trans_y,
        trans_z,
        b"",
    )
    f.write(data)
