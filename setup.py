"""MechWarrior3 Asset Extractor"""
import re
from pathlib import Path

from setuptools import find_packages, setup

HERE = Path(__file__).resolve(strict=True).parent


def read(*parts):
    return HERE.joinpath(*parts).open("r", encoding="utf-8").read()


# https://packaging.python.org/guides/single-sourcing-package-version/
def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name="mech3ax",
    description=__doc__,
    long_description=read("README.rst"),
    version=find_version("src", "mech3ax", "__init__.py"),
    author="Toby Fleming",
    author_email="tobywf@users.noreply.github.com",
    url="https://github.com/tobywf/mech3ax",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=True,
    python_requires=">=3.7",
    # remember to update .pre-commit-config.yaml with new requirements
    install_requires=["Pillow==6.2.1", "pefile==2019.4.18"],
    classifiers=(
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ),
)
