Installation
=============

AutonoMS Package Install
**************************
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

    autonoms-run

To run the Agilent RapidFire-6560 workflow, you have additional dependencies installed and configured (see Dependencies section)


Agilent Dependencies
*********************

``autonoms`` has the following core Python dependencies:

* numpy
* scipy
* rpyc
* pandas
* prefect
* pywinauto (for Agilent RF-6560 instrument control on Windows)

Additionally, for running the Agilent RapidFire-6560 workflow, the following dependencies must be installed manually:

* Agilent MassHunter Workstation Data Acquisition (version >= 11.0)
* Pacific Northwest National Laboratory (PNNL) PreProcessor (version >= 3.0)
* Agilent RapidFire UI (version >= 6.1.1.2114)
* MSConvert (version >= 3.0.22173) available via ProteoWizard
* Skyline (version >= 22.2.0.351)

