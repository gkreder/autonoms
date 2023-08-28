Installation and Dependencies
============

TL;DR
************
``mocha-ms`` is installed via setuptools, requiring only python 3.8.* and git.
It is highly recommended to do so in a conda environment or equivalent.
Create a python 3.8 conda environment and make sure it has git, hdf5, lzo, blosc, and pytables:

.. code-block:: shell
    conda create -n mocha-ms python=3.8 git hdf5 lzo blosc pytables

Then clone the ``mocha-ms`` GitHub repostiory:

.. code-block:: shell
    git clone https://github.com/gkreder/mocha-ms.git

Change directories into the mocha-ms repository folder and install:

.. code-block:: shell
    cd mocha-ms
    pip install .

Dependencies
************

``mocha-ms`` has