Installation
=============

TL;DR
************
``autonoms`` is installed via setuptools, requiring only python 3.8.*, git, hdf5, lzo, blosc, and pytables.
It is highly recommended to do so in a conda environment or equivalent.
Create a python 3.8 conda environment with the required libraries:

.. code-block:: shell

    conda create -n autonoms python=3.8 git hdf5 lzo blosc pytables

Then clone the ``autonoms`` GitHub repostiory:

.. code-block:: shell

    git clone https://github.com/gkreder/autonoms.git

Change directories into the mocha-ms repository folder and install:

.. code-block:: shell

    cd autonoms
    pip install .


Ensure the package installed by running

.. code-block:: shell

    mochams-run


Dependencies
************

``autonoms`` has the following Dependencies: