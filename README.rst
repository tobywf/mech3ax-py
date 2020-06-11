MechWarrior 3 Asset Extractor
=============================

MechWarrior 3 Asset Extractor (``mech3ax``) is a library and some scripts to extract assets from the 1998 MechWarrior 3 game to modern formats. `There is a companion project <https://github.com/tobywf/mech3re>`_ where I describe the reverse engineering of these assets, and how to extract other, semi-automatable assets such as ambient music and video files.

Obviously, this is an unofficial fan effort and not connected to the developers or publishers.

.. image:: .github/mech_annihilator_run.gif
   :target: https://imgur.com/a/H5pB1Vd

Currently supported
-------------------

- Various versions of the MechWarror 3 base game, including US versions 1.0, 1.1, 1.2, Gold Edition and German version 1.0 and 1.2 (patched). If you are in possession of any other versions, especially the French versions, please get in touch! (The expansion, Pirate's Moon, is `not yet supported <pm_issue_>`_.)
- Sound files (``soundsL.zbd``, ``soundsH.zbd``, and loose files installed by patches)
- All texture and image files (``rimage.zbd``, ``rmechtex*.zbd``, ``rtexture*.zbd``, ``texture*.zbd``)
- All messages extracted from ``Mech3Msg.dll``
- 'mech models from ``mechlib.zbd``, as well as the material index
- Animations (``motion.zbd``) can be extracted and applied to models. This works pretty well, but `some limbs have incorrect translations/locational data <https://github.com/tobywf/mech3ax/issues/2>`_
- Game engine files (``reader*.zbd``) can be dumped to JSON
- Interpreter files (``interp.zbd``) can be dumped to JSON

Not supported (yet):

- ``gamez.zbd`` files
- Files from the demo version aren't 100% supported yet, some of the model data have different headers (``mechlib.zbd``)
- The Pirate's Moon expansions (`GitHub issue <pm_issue_>`_)

Additionally, there is a stand-alone script that can convert extracted models to a ``.blend`` file for the 3D creation suite `Blender`_. Please see `Blender script`_ further down.

.. _Blender: https://www.blender.org/
.. _pm_issue: https://github.com/tobywf/mech3ax/issues/1

How to use
----------

**You will need a copy of the game. Do not ask me for an (illegal) copy.**

Python 3.7 or higher is required.

The various library functions can be used to write a script to extract game assets, or this can be done in an interactive session (in which case, `IPython`_ is highly recommended). I chose this approach, because depending on your installation method, the location of the files will differ. The code also works on macOS or Linux, so you can install the game in a virtual machine, and process the assets outside of it.

I realise not everybody will know Python, so I have included an example script (``example.py``). The first and only argument is the install location of MechWarrior 3 (containing ``Mech3.exe``). This script is only an example, and completely unsupported. If you run into issues using it, please don't raise an issue until you are sure it's an issue with the underlying library.

A virtual environment is recommended:

.. code-block:: console

    $ python3 -m venv env
    $ source env/bin/activate
    $ pip install .
    $ python3 example.py "<install location here>"

.. _IPython: https://ipython.org/

Blender script
--------------

Blender 2.80 or higher is required. Blender's APIs do change, so you may need to use a version closely matching that one. It will definitely *not* work with versions below 2.80, but if you have success running it with newer versions, let me know so I can update this read-me.

This is a bit tricky to get running, because of the dependencies. Assuming Blender is installed, and you have extracted the models and material index to ``mechlib/``, and ``rmechtex.zbd`` to ``mechtex/``, you can run the script like so:

.. code-block:: console

    $ blender \
        --background \
        --factory-startup \
        --python model2blend.py \
        -- mechlib/mech_annihilator.json mechtex/

This also assumes the Blender executable can be found. Your install location may vary, but here's some general instructions. For macOS (and Linux), this can be achieved by an alias in your shell's profile, e.g. ``.bashrc``:

.. code-block:: bash

    alias blender="/Applications/Blender.app/Contents/MacOS/Blender"

For Windows/PowerShell, you can add an alias to the appropriate ``profile.ps1``:

.. code-block:: powershell

    New-Alias blender "C:\Program Files\Blender Foundation\Blender\blender.exe"

(The syntax for invoking the script will also be slightly different using PowerShell)

License
-------

MechWarrior 3 Asset Extractor is GPLv3 licensed. Please see ``LICENSE``.

Development
-----------

Python 3.7+ is required. Dependency management is done via `poetry`_.

.. _poetry: https://python-poetry.org/

`pre-commit`_ is also required. It installs all dependencies necessary for linting and testing. And once installed, it will run when you commit.

.. _pre-commit: https://pre-commit.com/

.. code-block:: console

    $ pre-commit install

It can also be run at any point (without committing changes):

.. code-block:: console

    $ pre-commit run --all-files
