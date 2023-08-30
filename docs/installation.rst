Installation
=============

.. _autonoms-install:

AutonoMS Package Install
**************************


``autonoms`` is installed via setuptools, requiring python 3.8.*, git, hdf5, lzo, blosc, and pytables.
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

Note that to run the Agilent RapidFire-6560 workflow, you must have additional third-party dependencies installed and configured (:ref:`instructions <agilent-config>`)


For Disconnected RapidFire Computer
*************************************

The standard Agilent hardware installation of the RapidFire may involve a RapidFire computer that is disconnected from the internet
(and connected solely to the MS control desktop via ethernet). This makes installing and running code dependencies trickier on the RapidFire computer.

For purposes of using AutonoMS for the RapidFire - 6560 workflow described in the manuscript, it is recommended to connect your RapidFire computer to the internet
if possible. If this is not possible, then the following steps are recommended for installing and deploying AutonoMS.

Install (mini)conda to the shared RapidFire - 6560 networked drive (NOT the local 6560 drive). Follow the standard AutonoMS
:ref:`installation instructions <autonoms-install>` above on the 6560 computer (assumed to be connected to the internet). 

Now we want to utilize the same conda installation and environment on the RapidFire computer. Note that this is not a recommended practice in general 
but serves as a convenient workaround in this case. On the RapidFire computer, open a PowerShell instance and navigate to the Scripts folder inside conda environment 
directory for example ``M:\miniconda3\envs\autonoms\Scripts``. From there run the command:

.. code-block:: powershell

    .\conda.exe init

to give powershell access to the 6560 installation of conda. Restart PowerShell and activate the AutonoMS environment which should now have access to all the necessary dependencies.
As noted in the :ref:`usage <rpycRF>` section, running the rpyc server in this configuration requires using a Python script call rather than the built in ``autonoms-rpyc`` function.





