from math import cos, sin
from struct import pack, unpack
from typing import Tuple, cast

Matrix = Tuple[float, float, float, float, float, float, float, float, float]


def euler_to_matrix(x: float, y: float, z: float) -> Matrix:
    sin_x = sin(-x)
    cos_x = cos(-x)
    sin_y = sin(-y)
    cos_y = cos(-y)
    sin_z = sin(-z)
    cos_z = cos(-z)

    full_prec = (
        cos_z * cos_y,
        cos_z * sin_y * sin_x - sin_z * cos_x,
        cos_z * sin_y * cos_x + sin_z * sin_x,
        sin_z * cos_y,
        sin_z * sin_y * sin_x + cos_z * cos_x,
        sin_z * sin_y * cos_x - cos_z * sin_x,
        -sin_y,
        cos_y * sin_x,
        cos_y * cos_x,
    )

    return cast(Matrix, unpack("9f", pack("9f", *full_prec)))
