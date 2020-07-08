#define PY_SSIZE_T_CLEAN
#include <Python.h>

static uint32_t LERP888[0x10000];
static uint8_t LERP5[0x100];
static uint8_t LERP6[0x100];

PyDoc_STRVAR(rgb565to888__doc__, "Unpack RGB565 bytes (LE) to RGB888 bytes");

static PyObject *
rgb565to888(PyObject *self, PyObject *args)
{
    Py_ssize_t src_len = 0;
    const uint8_t *src = NULL;

    if (!PyArg_ParseTuple(args, "y#", &src, &src_len)) {
        return NULL;
    }

    Py_ssize_t dst_len = src_len * 3 / 2;
    uint8_t *dst = (uint8_t *)malloc(dst_len);

    for (int i = 0, j = 0; i < src_len; i += 2, j += 3) {
        // little-endian GGGBBBBB RRRRRGGG
        uint16_t color565 = (src[i + 1] << 8) | (src[i + 0]);
        uint32_t color888 = LERP888[color565];

        dst[j + 0] = (color888 >> 16) & 0xFF;
        dst[j + 1] = (color888 >> 8) & 0xFF;
        dst[j + 2] = (color888 >> 0) & 0xFF;
    }

    PyObject *result = PyBytes_FromStringAndSize((char *)dst, dst_len);
    free(dst);
    return result;
}

PyDoc_STRVAR(rgb888to565__doc__, "Pack RGB888 bytes into RGB565 bytes (LE)");

static PyObject *
rgb888to565(PyObject *self, PyObject *args)
{
    Py_ssize_t src_len = 0;
    const uint8_t *src = NULL;

    if (!PyArg_ParseTuple(args, "y#", &src, &src_len)) {
        return NULL;
    }

    Py_ssize_t dst_len = src_len * 2 / 3;
    uint8_t *dst = (uint8_t *)malloc(dst_len);

    for (int i = 0, j = 0; i < src_len; i += 3, j += 2) {
        uint8_t red = LERP5[src[i + 0]];
        uint8_t green = LERP6[src[i + 1]];
        uint8_t blue = LERP5[src[i + 2]];

        // little-endian GGGBBBBB RRRRRGGG
        dst[j + 0] = ((green << 5) & 0xFF) | (blue);
        dst[j + 1] = (red << 3) | ((green >> 3) & 0xFF);
    }

    PyObject *result = PyBytes_FromStringAndSize((char *)dst, dst_len);
    free(dst);
    return result;
}

PyDoc_STRVAR(check_palette__doc__, "Check all pixels are valid for the palette size");

static PyObject *
check_palette(PyObject *self, PyObject *args)
{
    Py_ssize_t src_len = 0;
    const uint8_t *src = NULL;
    uint16_t palette_count = 0;

    if (!PyArg_ParseTuple(args, "hy#", &palette_count, &src, &src_len)) {
        return NULL;
    }

    for (int i = 0; i < src_len; i++) {
        if (src[i] >= palette_count) {
            Py_RETURN_FALSE;
        }
    }

    Py_RETURN_TRUE;
}

static PyMethodDef color_methods[] = {
    {"rgb565to888", (PyCFunction)rgb565to888, METH_VARARGS, rgb565to888__doc__},
    {"rgb888to565", (PyCFunction)rgb888to565, METH_VARARGS, rgb888to565__doc__},
    {"check_palette", (PyCFunction)check_palette, METH_VARARGS, check_palette__doc__},
    {NULL, NULL, 0, NULL},
};

PyDoc_STRVAR(color_module__doc__, "Speed-up color conversions");

static struct PyModuleDef color_module = {
   PyModuleDef_HEAD_INIT,
   .m_name = "_native",
   .m_doc = color_module__doc__,
   .m_size = -1,
   .m_methods = color_methods,
};

static void
init_lerp888_table(void) {
    for (uint32_t i = 0; i < 0x10000; i++) {
        uint8_t red_bits = (i >> 11) & 0x1f;
        uint8_t red_lerp = (uint8_t)(red_bits * 255.0f / 31.0f + 0.5f);

        uint8_t green_bits = (i >> 5) & 0x3f;
        uint8_t green_lerp = (uint8_t)(green_bits * 255.0f / 63.0f + 0.5f);

        uint8_t blue_bits = (i >> 0) & 0x1f;
        uint8_t blue_lerp = (uint8_t)(blue_bits * 255.0f / 31.0f + 0.5f);

        LERP888[i] = (red_lerp << 16) | (green_lerp << 8) | (blue_lerp << 0);
    }
}

static void
init_lerp565_table(void) {
    for (uint32_t i = 0; i < 0x100; i++) {
        LERP5[i] = (int)(i * 31.0f / 255.0f + 0.5f);
        LERP6[i] = (int)(i * 63.0f / 255.0f + 0.5f);
    }
}

PyMODINIT_FUNC
PyInit__native(void)
{
    init_lerp888_table();
    init_lerp565_table();

    PyObject *module = PyModule_Create(&color_module);
    return module;
}
