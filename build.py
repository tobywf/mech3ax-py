from distutils.core import Extension

color_speedup = Extension(
    "mech3ax.parse.colors._native", ["src/mech3ax/parse/colors/native.c"], language="c",
)

float_helpers = Extension(
    "mech3ax.parse.float._native", ["src/mech3ax/parse/float/native.c"], language="c",
)


def build(setup_kwargs):
    setup_kwargs["ext_modules"] = [color_speedup, float_helpers]
