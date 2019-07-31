MechWarrior 3 Asset Extractor
=============================

MechWarrior 3 Asset Extractor (``mech3ax``) is a library and some scripts to extract assets from the 1998 MechWarrior 3 game to modern formats. There is a companion project where I describe the reverse engineering of these assets, and how to extract other, semi-automatable assets such as ambient music and video files.

Obviously it is an unofficial fan effort and not connected to the developers or publishers.

How to use
----------

**You will need a copy of the game. Do not ask me for an illegal copy.**

The various library functions can be used to write a script to extract game assets, or this can be done in an interactive session (in which case, `IPython`_ is highly recommended). I haven't provided one, as depending on your installation method, the location of the files will differ. The code also works on macOS or Linux, so you can install the game in a virtual machine, and process the assets outside of it.

Currently supported:

- Various versions of the MechWarror 3 base game, including US versions 1.0, 1.1, 1.2, Gold Edition and German version 1.0 and 1.2 (patched). If you are in possession of any other versions, especially the French versions, please get in touch! (The expansion, Pirate's Moon, is not supported.)
- Sound files (``soundsL.zbd``, ``soundsH.zbd``)
- All texture and image ``.zbd`` files

.. _IPython: https://ipython.org/

License
-------

MechWarrior 3 Asset Extractor is GPLv3 licensed. Please see ``LICENSE``.

Development
-----------

Python 3.7+ is required. A virtual environment is highly recommended. Simply clone and install in "editable mode" (``--editable``, ``-e``):

.. code-block:: console

    $ python3 -m venv env
    $ source env/bin/activate
    $ pip install -e .

`pre-commit`_ is required. It will install all dependencies necessary for linting and testing:

.. code-block:: console

    $ pre-commit install

It can also be run without committing:

.. code-block:: console

    $ pre-commit run --all-files

.. _pre-commit: https://pre-commit.com/
