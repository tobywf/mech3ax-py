from math import pi, sqrt, tan
from typing import Callable, Dict, List, Sequence

from mech3ax.errors import (
    Mech3InternalError,
    Mech3ParseError,
    assert_all_zero,
    assert_between,
    assert_eq,
    assert_flag,
    assert_ge,
    assert_gt,
    assert_in,
    assert_ne,
)
from mech3ax.serde import NodeType

from ..anim.light import LightFlag
from ..float import approx_sqrt, euler_to_matrix, force_single_prec
from ..utils import BinReader
from .models import (
    CAMERA,
    DISPLAY,
    IDENTITY_MATRIX,
    LEVEL_OF_DETAIL,
    LIGHT,
    LIGHT_FLAG,
    OBJECT3D,
    PARTITION,
    WINDOW,
    WORLD,
    Camera,
    Display,
    LevelOfDetail,
    Light,
    Matrix,
    NodeData,
    Object3d,
    Partition,
    Window,
    World,
)
from .sign import extract_zero_signs

CLEAR_COLOR = 0.3919999897480011
PI = force_single_prec(pi)

ReadNodeData = Callable[[BinReader], NodeData]
READ_NODE_DATA: Dict[NodeType, ReadNodeData] = {}


def _read_node_data(node_type: NodeType) -> Callable[[ReadNodeData], ReadNodeData]:
    def _wrap(f: ReadNodeData) -> ReadNodeData:
        READ_NODE_DATA[node_type] = f
        return f

    return _wrap


@_read_node_data(NodeType.Empty)
def _read_node_data_empty(_reader: BinReader) -> None:
    raise Mech3InternalError("Empty nodes shouldn't be read")  # pragma: no cover


@_read_node_data(NodeType.Camera)
def _read_node_data_camera(  # pylint: disable=too-many-locals
    reader: BinReader,
) -> Camera:
    (
        world_index,  # 000
        window_index,  # 004
        focus_node_xy,  # 008
        focus_node_xz,  # 012
        flag_raw,  # 016
        trans_x,  # 020
        trans_y,  # 024
        trans_z,  # 028
        rot_x,  # 032
        rot_y,  # 036
        rot_z,  # 040
        zero044,  # 132 zero bytes
        clip_near_z,  # 176
        clip_far_z,  # 180
        zero184,  # 24 zero bytes
        lod_multiplier,  # 208
        lod_inv_sq,  # 212
        fov_h_zoom_factor,  # 216
        fov_v_zoom_factor,  # 220
        fov_h_base,  # 224
        fov_v_base,  # 228
        fov_h,  # 232
        fov_v,  # 236
        fov_h_half,  # 240
        fov_v_half,  # 244
        one248,
        zero252,  # 60 zero bytes
        one312,
        zero316,  # 72 zero bytes
        one388,
        zero392,  # 72 zero bytes
        zero464,
        fov_h_tan_inv,  # 468
        fov_v_tan_inv,  # 472
        stride,
        zone_set,
        unk484,
    ) = reader.read(CAMERA)

    assert_eq("world index", 0, world_index, reader.prev + 0)
    assert_eq("window index", 1, window_index, reader.prev + 4)
    assert_eq("focus node xy", -1, focus_node_xy, reader.prev + 8)
    assert_eq("focus node xz", -1, focus_node_xz, reader.prev + 12)
    assert_eq("flag", 0, flag_raw, reader.prev + 16)

    assert_eq("trans x", 0.0, trans_x, reader.prev + 20)
    assert_eq("trans y", 0.0, trans_y, reader.prev + 24)
    assert_eq("trans z", 0.0, trans_z, reader.prev + 28)

    assert_eq("rot x", 0.0, rot_x, reader.prev + 32)
    assert_eq("rot y", 0.0, rot_y, reader.prev + 36)
    assert_eq("rot z", 0.0, rot_z, reader.prev + 40)

    # WorldTranslate: Vec3
    # WorldRotate: Vec3
    # MtwMatrix: Mat
    # Unk: Vec3
    # ViewVector: Vec3
    # Matrix: Mat
    # AltTranslate: Vec3
    assert_all_zero("field 044", zero044, reader.prev + 44)

    assert_gt("clip near z", 0.0, clip_near_z, reader.prev + 176)
    assert_gt("clip far z", clip_near_z, clip_far_z, reader.prev + 180)

    assert_all_zero("field 184", zero184, reader.prev + 184)

    assert_eq("LOD mul", 1.0, lod_multiplier, reader.prev + 208)
    assert_eq("LOD inv sq", 1.0, lod_inv_sq, reader.prev + 212)

    assert_eq("FOV H zoom factor", 1.0, fov_h_zoom_factor, reader.prev + 216)
    assert_eq("FOV V zoom factor", 1.0, fov_v_zoom_factor, reader.prev + 220)
    assert_gt("FOV H base", 0.0, fov_h_base, reader.prev + 224)
    assert_gt("FOV V base", 0.0, fov_v_base, reader.prev + 228)
    assert_eq("FOV H zoomed", fov_h_base, fov_h, reader.prev + 232)
    assert_eq("FOV V zoomed", fov_v_base, fov_v, reader.prev + 236)
    assert_eq("FOV H half", fov_h / 2.0, fov_h_half, reader.prev + 240)
    assert_eq("FOV V half", fov_v / 2.0, fov_v_half, reader.prev + 244)

    assert_eq("field 248", 1, one248, reader.prev + 248)
    assert_all_zero("field 252", zero252, reader.prev + 252)

    assert_eq("field 312", 1, one312, reader.prev + 312)
    assert_all_zero("field 316", zero316, reader.prev + 316)

    assert_eq("field 388", 1, one388, reader.prev + 388)
    assert_all_zero("field 392", zero392, reader.prev + 392)

    assert_eq("field 464", 0, zero464, reader.prev + 464)

    expected = force_single_prec(1.0 / tan(fov_h_half))
    assert_eq("FOV H tan inv", expected, fov_h_tan_inv, reader.prev + 468)
    expected = force_single_prec(1.0 / tan(fov_v_half))
    assert_eq("FOV V tan inv", expected, fov_v_tan_inv, reader.prev + 472)

    assert_eq("stride", 0, stride, reader.prev + 476)
    assert_eq("zone set", 0, zone_set, reader.prev + 480)
    assert_eq("field 484", -256, unk484, reader.prev + 484)

    return Camera(
        type="Camera", clip=(clip_near_z, clip_far_z), fov=(fov_h_base, fov_v_base)
    )


def _read_partitions(  # pylint: disable=too-many-locals
    reader: BinReader, area_x: Sequence[int], area_y: Sequence[int]
) -> List[List[Partition]]:

    partitions = []
    for y in area_y:
        subpartitions = []
        for x in area_x:
            (
                flag_raw,
                mone04,
                part_x,
                part_y,
                unk16,
                unk20,
                unk24,
                unk28,
                unk32,
                unk36,
                unk40,
                unk44,
                unk48,
                unk52,
                zero56,
                count,  # 58
                ptr,  # 60
                zero64,
                zero68,
            ) = reader.read(PARTITION)

            assert_eq("partition field 00", 0x100, flag_raw, reader.prev + 0)
            assert_eq("partition field 04", -1, mone04, reader.prev + 4)

            assert_eq("partition field 56", 0, zero56, reader.prev + 56)
            assert_eq("partition field 64", 0, zero64, reader.prev + 64)
            assert_eq("partition field 68", 0, zero68, reader.prev + 68)

            assert_eq("partition x", x, part_x, reader.prev + 8)
            assert_eq("partition y", y, part_y, reader.prev + 12)

            assert_eq("partition field 16", x, unk16, reader.prev + 16)
            # unk20
            assert_eq("partition field 24", y - 256, unk24, reader.prev + 24)
            assert_eq("partition field 28", x + 256, unk28, reader.prev + 28)
            # unk32
            assert_eq("partition field 36", y, unk36, reader.prev + 36)

            # this is set through an extremely convoluted calculation starting with:
            #   unk40 = unk16 + (unk28 - unk16) * 0.5
            # which simplifies to:
            #   unk40 = x + 128.0
            assert_eq("partition field 40", x + 128, unk40, reader.prev + 40)

            # this is set through an extremely convoluted calculation starting with:
            #   unk44 = unk20 + (unk32 - unk20) * 0.5
            # ... at least initially, although unk20 and unk32 would be 0.0 because
            # calloc zeros memory. i can get this calculation to work with almost
            # all values, but some are ever so slightly off (lowest bits in the
            # single precision floating point numbers differ), so i suspect this
            # calculation is more complicated.
            # assert_eq("partition field 44", expected, unk44, reader.prev + 44)

            # this is set through an extremely convoluted calculation starting with:
            #   unk48 = unk24 + (unk36 - unk24) * 0.5
            # which simplifies to:
            #   unk48 = y - 128.0
            assert_eq("partition field 48", y - 128, unk48, reader.prev + 48)  # two[2]

            # this is set through an extremely convoluted calculation starting with:
            #   temp1 = (unk28 - unk16) * 0.5
            #   temp2 = (unk32 - unk20) * 0.5
            #   temp3 = (unk36 - unk24) * 0.5
            # which simplifies to:
            #   temp1 = 128.0
            #   (does not simplify without knowing unk32 and unk20)
            #   temp3 = 128.0
            # approx_sqrt automatically converts to single precision
            temp = (unk32 - unk20) * 0.5
            expected = approx_sqrt(128 * 128 + temp * temp + 128 * 128)
            assert_eq("partition field 52", expected, unk52, reader.prev + 52)

            if count:
                assert_ne("partition ptr", 0, ptr, reader.prev + 60)
                nodes = [reader.read_u32() for _ in range(count)]
            else:
                assert_eq("partition ptr", 0, ptr, reader.prev + 60)
                nodes = []

            partition = Partition(
                x=x, y=y, nodes=nodes, unk=(unk20, unk32, unk44), ptr=ptr,
            )
            subpartitions.append(partition)
        partitions.append(subpartitions)

    return partitions


@_read_node_data(NodeType.World)
def _read_node_data_world(  # pylint: disable=too-many-locals,too-many-statements
    reader: BinReader,
) -> World:
    (
        flag_raw,  # 000
        area_partition_used,  # 004
        area_partition_count,  # 008
        area_partition_ptr,  # 012
        fog_state_raw,  # 016
        fog_color_r,  # 020
        fog_color_g,  # 024
        fog_color_b,  # 028
        fog_range_near,  # 032
        fog_range_far,  # 036
        fog_alti_high,  # 040
        fog_alti_low,  # 044
        fog_density,  # 048
        area_left_f,  # 052
        area_bottom_f,  # 056
        area_width,  # 060
        area_height,  # 064
        area_right_f,  # 068
        area_top_f,  # 072
        partition_max_dec_feature_count,  # 076
        virtual_partition,  # 080
        virt_partition_x_min,  # 084
        virt_partition_y_min,  # 088
        virt_partition_x_max,  # 092
        virt_partition_y_max,  # 096
        virt_partition_x_size,  # 100
        virt_partition_y_size,  # 104
        virt_partition_x_half,  # 108
        virt_partition_y_half,  # 112
        virt_partition_x_inv,  # 116
        virt_partition_y_inv,  # 124
        virt_partition_diag,  # 128
        partition_inclusion_tol_low,  # 128
        partition_inclusion_tol_high,  # 132
        virt_partition_x_count,  # 136
        virt_partition_y_count,  # 140
        virt_partition_ptr,  # 144
        one148,
        one152,
        one156,
        children_count,  # 160
        children_ptr,  # 164
        lights_ptr,  # 168
        zero172,
        zero176,
        zero180,
        zero184,
    ) = reader.read(WORLD)

    assert_eq("flag", 0, flag_raw, reader.prev + 0)

    # LINEAR = 1, EXPONENTIAL = 2 (never set)
    assert_eq("fog state", 1, fog_state_raw, reader.prev + 16)
    # not set
    assert_eq("fog color r", 0.0, fog_color_r, reader.prev + 20)
    assert_eq("fog color g", 0.0, fog_color_g, reader.prev + 24)
    assert_eq("fog color b", 0.0, fog_color_b, reader.prev + 28)
    assert_eq("fog range near", 0.0, fog_range_near, reader.prev + 32)
    assert_eq("fog range far", 0.0, fog_range_far, reader.prev + 36)
    assert_eq("fog alti high", 0.0, fog_alti_high, reader.prev + 40)
    assert_eq("fog alti low", 0.0, fog_alti_low, reader.prev + 44)
    assert_eq("fog density", 0.0, fog_density, reader.prev + 48)

    # we need these values to be integers for the partition logic
    area_left = int(area_left_f)
    area_bottom = int(area_bottom_f)
    area_right = int(area_right_f)
    area_top = int(area_top_f)
    assert_eq("area left", area_left, area_left_f, reader.prev + 52)
    assert_eq("area bottom", area_bottom, area_bottom_f, reader.prev + 56)
    assert_eq("area right", area_right, area_right_f, reader.prev + 68)
    assert_eq("area top", area_top, area_top_f, reader.prev + 72)

    # validate rect
    assert_gt("area right", area_left, area_right, reader.prev + 68)
    assert_gt("area bottom", area_top, area_bottom, reader.prev + 72)
    width = area_right - area_left
    height = area_top - area_bottom
    assert_eq("area width", width, area_width, reader.prev + 60)
    assert_eq("area height", height, area_height, reader.prev + 64)

    assert_eq(
        "partition max feat", 16, partition_max_dec_feature_count, reader.prev + 76
    )
    assert_eq("virtual partition", 1, virtual_partition, reader.prev + 80)

    assert_eq("vp x min", 1, virt_partition_x_min, reader.prev + 84)
    assert_eq("vp y min", 1, virt_partition_y_min, reader.prev + 88)

    assert_eq("vp x size", 256.0, virt_partition_x_size, reader.prev + 100)
    assert_eq("vp y size", -256.0, virt_partition_y_size, reader.prev + 104)
    assert_eq("vp x half", 128.0, virt_partition_x_half, reader.prev + 108)
    assert_eq("vp y half", -128.0, virt_partition_y_half, reader.prev + 112)
    assert_eq("vp x inv", 1.0 / 256.0, virt_partition_x_inv, reader.prev + 116)
    assert_eq("vp y inv", 1.0 / -256.0, virt_partition_y_inv, reader.prev + 120)
    # this is sqrt(x_size * x_size + y_size * y_size) * -0.5, but because of the
    # (poor) sqrt approximation used, it comes out as -192.0 instead of -181.0
    assert_eq("vp diagonal", -192.0, virt_partition_diag, reader.prev + 124)

    assert_eq("vp inc tol low", 3, partition_inclusion_tol_low, reader.prev + 128)
    assert_eq("vp inc tol high", 3, partition_inclusion_tol_high, reader.prev + 132)

    area_x = range(area_left, area_right, 256)
    # because the virtual partition y size is negative, this is inverted!
    area_y = range(area_bottom, area_top, -256)

    assert_eq("vp x count", len(area_x), virt_partition_x_count, reader.prev + 136)
    assert_eq("vp y count", len(area_y), virt_partition_y_count, reader.prev + 140)
    assert_eq("ap used", 0, area_partition_used, reader.prev + 4)
    assert_eq(
        "vp x max", virt_partition_x_count - 1, virt_partition_x_max, reader.prev + 92,
    )
    assert_eq(
        "vp y max", virt_partition_y_count - 1, virt_partition_y_max, reader.prev + 96,
    )

    # TODO: why isn't this a perfect fit for T1?
    virt_partition_count = virt_partition_x_count * virt_partition_y_count
    assert_between(
        "ap count",
        virt_partition_count - 1,
        virt_partition_count,
        area_partition_count,
        reader.prev + 8,
    )
    fudge_count = area_partition_count != virt_partition_count
    assert_ne("ap ptr", 0, area_partition_ptr, reader.prev + 12)
    assert_ne("vp ptr", 0, virt_partition_ptr, reader.prev + 144)

    assert_eq("field 148", 1, one148, reader.prev + 148)
    assert_eq("field 152", 1, one152, reader.prev + 152)
    assert_eq("field 156", 1, one156, reader.prev + 156)
    assert_eq("children count", 1, children_count, reader.prev + 160)
    assert_ne("children ptr", 0, children_ptr, reader.prev + 164)
    assert_ne("lights ptr", 0, lights_ptr, reader.prev + 168)
    assert_eq("field 172", 0, zero172, reader.prev + 172)
    assert_eq("field 176", 0, zero176, reader.prev + 176)
    assert_eq("field 180", 0, zero180, reader.prev + 180)
    assert_eq("field 184", 0, zero184, reader.prev + 184)

    # read as a result of children_count
    child = reader.read_u32()
    # read as a result of zero172 (i.e. nothing to do)

    partitions = _read_partitions(reader, area_x, area_y)

    # world nodes always have an action priority of 13

    return World(
        type="World",
        area=(area_left, area_top, area_right, area_bottom),
        partitions=partitions,
        children=[child],
        area_partition_x_count=virt_partition_x_count,
        area_partition_y_count=virt_partition_y_count,
        fudge_count=fudge_count,
        area_partition_ptr=area_partition_ptr,
        virt_partition_ptr=virt_partition_ptr,
        children_ptr=children_ptr,
        lights_ptr=lights_ptr,
    )


@_read_node_data(NodeType.Window)
def _read_node_data_window(reader: BinReader) -> Window:
    (
        origin_x,  # 000
        origin_y,  # 004
        resolution_x,  # 008
        resolution_y,  # 012
        zero016,  # 212 zero bytes
        buffer_index,  # 228
        buffer_ptr,  # 232
        zero236,
        zero240,
        zero244,
    ) = reader.read(WINDOW)

    assert_eq("origin x", 0, origin_x, reader.prev + 0)
    assert_eq("origin y", 0, origin_y, reader.prev + 4)

    assert_eq("resolution x", 320, resolution_x, reader.prev + 8)
    assert_eq("resolution y", 200, resolution_y, reader.prev + 12)

    assert_all_zero("field 016", zero016, reader.prev + 16)

    assert_eq("buffer index", -1, buffer_index, reader.prev + 228)
    assert_eq("buffer ptr", 0, buffer_ptr, reader.prev + 232)

    assert_eq("field 236", 0, zero236, reader.prev + 236)
    assert_eq("field 240", 0, zero240, reader.prev + 240)
    assert_eq("field 244", 0, zero244, reader.prev + 244)

    # window nodes always have an action priority of 14

    return Window(type="Window", resolution=(resolution_x, resolution_y),)


@_read_node_data(NodeType.Display)
def _read_node_data_display(reader: BinReader) -> Display:
    (
        origin_x,
        origin_y,
        resolution_x,
        resolution_y,
        clear_color_r,
        clear_color_g,
        clear_color_b,
    ) = reader.read(DISPLAY)

    # these values are all constants - dump them because they're interesting
    # for engine internals

    assert_eq("origin x", 0, origin_x, reader.prev + 0)
    assert_eq("origin y", 0, origin_y, reader.prev + 4)

    assert_eq("resolution x", 640, resolution_x, reader.prev + 8)
    assert_eq("resolution y", 400, resolution_y, reader.prev + 12)

    assert_eq("clear color r", CLEAR_COLOR, clear_color_r, reader.prev + 16)
    assert_eq("clear color g", CLEAR_COLOR, clear_color_g, reader.prev + 20)
    assert_eq("clear color b", 1.0, clear_color_b, reader.prev + 24)

    # display nodes always have an action priority of 15

    return Display(
        type="Display",
        resolution=(resolution_x, resolution_y),
        clear_color=(clear_color_r, clear_color_g, clear_color_b),
    )


def read_node_data_object3d(  # pylint: disable=too-many-locals
    reader: BinReader,
) -> Object3d:
    (
        flag_raw,  # 000
        opacity,  # 004
        zero008,
        zero012,
        zero016,
        zero020,
        rot_x,  # 024
        rot_y,  # 028
        rot_z,  # 032
        scale_x,  # 036
        scale_y,  # 040
        scale_z,  # 044
        matrix00,  # 048
        matrix01,  # 052
        matrix02,  # 056
        matrix10,  # 060
        matrix11,  # 064
        matrix12,  # 068
        matrix20,  # 072
        matrix21,  # 076
        matrix22,  # 080
        trans_x,  # 084
        trans_y,  # 088
        trans_z,  # 092
        zero096,  # 42 zero bytes
    ) = reader.read(OBJECT3D)

    assert_in("flag", (32, 40), flag_raw, reader.prev + 0)
    assert_eq("opacity", 0.0, opacity, reader.prev + 4)

    assert_eq("field 008", 0.0, zero008, reader.prev + 8)
    assert_eq("field 012", 0.0, zero012, reader.prev + 12)
    assert_eq("field 016", 0.0, zero016, reader.prev + 16)
    assert_eq("field 020", 0.0, zero020, reader.prev + 20)

    assert_eq("scale x", 1.0, scale_x, reader.prev + 36)
    assert_eq("scale y", 1.0, scale_y, reader.prev + 40)
    assert_eq("scale z", 1.0, scale_z, reader.prev + 44)

    assert_all_zero("field 096", zero096, reader.prev + 96)

    def _assert_matrix(expected: Matrix) -> None:
        assert_eq("matrix 00", expected[0], matrix00, reader.prev + 48)
        assert_eq("matrix 01", expected[1], matrix01, reader.prev + 52)
        assert_eq("matrix 02", expected[2], matrix02, reader.prev + 56)
        assert_eq("matrix 10", expected[3], matrix10, reader.prev + 60)
        assert_eq("matrix 11", expected[4], matrix11, reader.prev + 64)
        assert_eq("matrix 12", expected[5], matrix12, reader.prev + 68)
        assert_eq("matrix 20", expected[6], matrix20, reader.prev + 72)
        assert_eq("matrix 21", expected[7], matrix21, reader.prev + 76)
        assert_eq("matrix 22", expected[8], matrix22, reader.prev + 80)

    matrix_sign = extract_zero_signs(
        matrix00,
        matrix01,
        matrix02,
        matrix10,
        matrix11,
        matrix12,
        matrix20,
        matrix21,
        matrix22,
    )

    if flag_raw == 40:
        assert_eq("rot x", 0.0, rot_x, reader.prev + 24)
        assert_eq("rot y", 0.0, rot_y, reader.prev + 28)
        assert_eq("rot z", 0.0, rot_z, reader.prev + 32)

        assert_eq("trans x", 0.0, trans_x, reader.prev + 84)
        assert_eq("trans y", 0.0, trans_y, reader.prev + 88)
        assert_eq("trans z", 0.0, trans_z, reader.prev + 92)

        _assert_matrix(IDENTITY_MATRIX)

        rotation = None
        translation = None
        matrix = None
    else:
        # all values between PI
        assert_between("rot x", -PI, PI, rot_x, reader.prev + 24)
        assert_between("rot y", -PI, PI, rot_y, reader.prev + 28)
        assert_between("rot z", -PI, PI, rot_z, reader.prev + 32)

        rotation = (rot_x, rot_y, rot_z)
        translation = (trans_x, trans_y, trans_z)

        expected = euler_to_matrix(rot_x, rot_y, rot_z)

        # in most cases, the calculated matrix is correct :/
        # for 58 out of 2729 Object3D nodes, this fails though
        try:
            _assert_matrix(expected)
        except Mech3ParseError:
            matrix = (
                matrix00,
                matrix01,
                matrix02,
                matrix10,
                matrix11,
                matrix12,
                matrix20,
                matrix21,
                matrix22,
            )
            matrix_sign = 0
        else:
            matrix = None

    # object 3d nodes always have an action priority of 6

    return Object3d(
        type="Object3D",
        rotation=rotation,
        translation=translation,
        matrix=matrix,
        matrix_sign=matrix_sign,
    )


@_read_node_data(NodeType.Object3D)
def _read_node_data_object3d(reader: BinReader) -> Object3d:
    return read_node_data_object3d(reader)


@_read_node_data(NodeType.LOD)
def _read_node_data_lod(reader: BinReader) -> LevelOfDetail:
    (
        level,  # 00
        range_near_sq,  # 04
        range_far,  # 08
        range_far_sq,  # 12
        zero16,  # 44 zero bytes
        unk60,  # 60
        unk64,  # 64
        one68,  # 68
        zero72,  # 72
        unk76,  # 76
    ) = reader.read(LEVEL_OF_DETAIL)

    assert_in("level", (0, 1), level, reader.prev + 0)

    assert_between(
        "range near sq", 0.0, 1000.0 * 1000.0, range_near_sq, reader.prev + 4,
    )
    range_near = sqrt(range_near_sq)

    assert_ge("range far", 0.0, range_far, reader.prev + 8)
    expected = force_single_prec(range_far * range_far)
    assert_eq("range far sq", expected, range_far_sq, reader.prev + 12)

    assert_all_zero("field 16", zero16, reader.prev + 16)

    # TODO:
    assert_ge("field 60", 0.0, unk60, reader.prev + 60)
    expected = force_single_prec(unk60 * unk60)
    assert_eq("field 64", expected, unk64, reader.prev + 64)

    assert_eq("field 68", 1, one68, reader.prev + 68)
    # TODO:
    assert_in("field 72", (0, 1), zero72, reader.prev + 72)
    if zero72 == 0:
        assert_eq("field 76", 0, unk76, reader.prev + 76)
    else:
        assert_ne("field 76", 0, unk76, reader.prev + 76)

    # object 3d nodes always have an action priority of 6

    return LevelOfDetail(
        type="LOD",
        level=level == 1,
        range=(range_near, range_far),
        unk60=unk60,
        unk76=unk76,
    )


@_read_node_data(NodeType.Light)
def _read_node_data_light(  # pylint: disable=too-many-locals
    reader: BinReader,
) -> Light:
    (
        direction_x,  # 000
        direction_y,  # 004
        direction_z,  # 008
        trans_x,  # 012
        trans_y,  # 016
        trans_z,  # 020
        zero024,  # 112 zero bytes
        one136,
        zero140,
        zero144,
        zero148,
        zero152,
        diffuse,  # 156
        ambient,  # 160
        color_r,  # 164
        color_g,  # 168
        color_b,  # 172
        flag_raw,  # 176
        range_min,  # 180
        range_max,  # 184
        range_min_sq,  # 188
        range_max_sq,  # 192
        range_inv,  # 196
        parent_count,  # 200
        parent_ptr,  # 204
        zero208,
    ) = reader.read(LIGHT)

    # translation is never set
    assert_eq("trans x", 0.0, trans_x, reader.prev + 12)
    assert_eq("trans y", 0.0, trans_y, reader.prev + 16)
    assert_eq("trans z", 0.0, trans_z, reader.prev + 20)

    assert_all_zero("field 024", zero024, reader.prev + 24)

    assert_eq("field 136", 1, one136, reader.prev + 136)
    assert_eq("field 140", 0, zero140, reader.prev + 140)
    assert_eq("field 144", 0, zero144, reader.prev + 144)
    assert_eq("field 148", 0, zero148, reader.prev + 148)
    assert_eq("field 152", 0, zero152, reader.prev + 152)

    assert_between("diffuse", 0.0, 1.0, diffuse, reader.prev + 156)
    assert_between("ambient", 0.0, 1.0, ambient, reader.prev + 160)

    assert_eq("color r", 1.0, color_r, reader.prev + 164)
    assert_eq("color g", 1.0, color_g, reader.prev + 168)
    assert_eq("color b", 1.0, color_b, reader.prev + 172)

    with assert_flag("flag", flag_raw, reader.prev + 176):
        flag = LightFlag.check(flag_raw)

    assert_eq("flag", LIGHT_FLAG, flag, reader.prev + 176)

    assert_gt("range min", 0.0, range_min, reader.prev + 180)
    assert_gt("range max", range_min, range_max, reader.prev + 184)
    expected = range_min * range_min
    assert_eq("range min sq", expected, range_min_sq, reader.prev + 188)
    expected = range_max * range_max
    assert_eq("range max sq", expected, range_max_sq, reader.prev + 192)
    expected = force_single_prec(1.0 / (range_max - range_min))
    assert_eq("range inv", expected, range_inv, reader.prev + 196)

    # if this was ever zero, field 208 wouldn't be read
    assert_eq("parent count", 1, parent_count, reader.prev + 200)
    assert_ne("parent ptr", 0, parent_ptr, reader.prev + 204)
    assert_eq("field 208", 0, zero208, reader.prev + 208)

    # light nodes always have an action priority of 9

    return Light(
        type="Light",
        direction=(direction_x, direction_y, direction_z),
        diffuse=diffuse,
        ambient=ambient,
        color=(color_r, color_g, color_b),
        range=(range_min, range_max),
        parent_ptr=parent_ptr,
    )


assert READ_NODE_DATA.keys() == set(NodeType)
