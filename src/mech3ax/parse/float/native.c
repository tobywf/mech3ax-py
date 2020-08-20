#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <math.h>

PyDoc_STRVAR(euler_to_matrix__doc__, "Convert Euler angles to a rotation matrix (XYZ)");

static PyObject *
euler_to_matrix(PyObject *self, PyObject *args)
{
    float x, y, z;

    if (!PyArg_ParseTuple(args, "fff", &x, &y, &z)) {
        return NULL;
    }

    x = -x;
    y = -y;
    z = -z;

    float sin_x = sinf(x);
    float cos_x = cosf(x);
    float sin_y = sinf(y);
    float cos_y = cosf(y);
    float sin_z = sinf(z);
    float cos_z = cosf(z);

    // optimized m(z) * m(y) * m(x) - this actually doesn't line up with the data!
    float m00 = cos_y * cos_z;
    float m01 = sin_x * sin_y * cos_z - cos_x * sin_z;
    float m02 = cos_x * sin_y * cos_z + sin_x * sin_z;
    float m10 = cos_y * sin_z;
    float m11 = sin_x * sin_y * sin_z + cos_x * cos_z;
    float m12 = cos_x * sin_y * sin_z - sin_x * cos_z;
    float m20 = -sin_y;
    float m21 = sin_x * cos_y;
    float m22 = cos_x * cos_y;

    return Py_BuildValue("fffffffff", m00, m01, m02, m10, m11, m12, m20, m21, m22);
}

static PyMethodDef float_methods[] = {
    {"euler_to_matrix", (PyCFunction)euler_to_matrix, METH_VARARGS, euler_to_matrix__doc__},
    {NULL, NULL, 0, NULL},
};

PyDoc_STRVAR(float_module__doc__, "32-bit IEEE 754 single precision floating point number helpers");

static struct PyModuleDef float_module = {
   PyModuleDef_HEAD_INIT,
   .m_name = "_native",
   .m_doc = float_module__doc__,
   .m_size = -1,
   .m_methods = float_methods,
};

PyMODINIT_FUNC
PyInit__native(void)
{
    PyObject *module = PyModule_Create(&float_module);
    return module;
}
