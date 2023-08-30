AutonoMS Usage
================

After installing the AutonoMS package and the Agilent workflow dependencies, data collection and analysis 
can be run in the manner described in the manuscript by following the steps below: 

.. _rpycRF:

Running rpyc server on RapidFire computer
*******************************************

After installing the AutonoMS package, the rpyc server can be kept running on the RapidFire computer using the command

.. code-block:: shell

    autonoms-rpyc

Note that this command should be launched from the RapidFire computer. The server can be kept running but must be restarted when there are changes to the codebase.

Note on disconnected RapidFire usage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Please see the installation instructions note on installing AutonoMS on a RapidFire computer that is not connected to the internet. If you 
are using such a setup with a shared conda environment, the autonoms-rpyc executable may not run on the RapidFire computer. This will be the case
if the shared drive has a different name on the RapidFire and 6560 computer (e.g. M:\\ vs D:\\ respectively). You can instead 
run the rpyc server on the RapidFire computer using this command run from the top-level AutonoMS directory:

.. code-block:: powershell

    python .\src\autonoms\agilent_methods\rf_rpyc_server.py




Creating a Skyline transition list
************************************

A Skyline csv transition list with target metabolite names, adducts, charges, m/z values, and (optionally) CCS values can be created
using the template provided in the repository located at ``transition_lists/ymdb_transition_list.csv``. This file will determine which metabolite signals 
are scanned for during Skyline data analysis. Note that the CCS values here are for human readers, not Skyline. CCS matching is done in Skyline using the 
.imsdb ion mobility library (described below in the :ref:`imsdb files <imsdb>` section). 

Example Transition list format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+--------------------+----------------------------+-------------------+------------------+------------------+-------------+----------------+-------+
| Molecule List Name |       Precursor Name       | Precursor Formula | Precursor Adduct | Precursor Charge | Product m/z | Product Charge | CCS   |
+====================+============================+===================+==================+==================+=============+================+=======+
|        ymdb        | (2)-Methylglutaric acid-p1 |      C6H10O4      |      [M-H]-      |        -1        |  145.0502   |       -1       | 126.3 |
+--------------------+----------------------------+-------------------+------------------+------------------+-------------+----------------+-------+
|        ymdb        |  (R)-Pantothenic acid-p1   |     C9H17NO5      |      [M+H]+      |        1         |   220.118   |       1        | 129.8 |
+--------------------+----------------------------+-------------------+------------------+------------------+-------------+----------------+-------+

    

Creating a tune ions file (for ion mobility CCS calibration)
*************************************************************

In its current form, AutonoMS expects a tune ion (chemical standards) injection of ions with known CCS values as the 
first injection of every sequence. A sequence can have multiple tune ion injections over the course of the run, but at minimum
must have at least one at the very beginning. Multiple tun ion injections may improve performance. Any set of standards is acceptable
as long as they have known CCS values. Tune ion m/z and CCS values must be provided to AutonoMS to perform CCS calibration. An example
tune ions template file is provided in the repository located at ``transition_lists/agilentTuneRestrictedDeimos_transitionList.csv```. The 
tune ions file follows the same format as the transition list described above:

Sample tune ions format
~~~~~~~~~~~~~~~~~~~~~~~~~

+--------------------+----------------+---------------+------------------+------------------+-------------+----------------+--------+
| Molecule List Name | Precursor Name | Precursor m/z | Precursor Adduct | Precursor Charge | Product m/z | Product Charge |  CCS   |
+====================+================+===============+==================+==================+=============+================+========+
|    tuneIons_pos    |   622.02896    |   622.02896   |      [M+H]+      |        1         |  622.02896  |       1        | 203.1  |
+--------------------+----------------+---------------+------------------+------------------+-------------+----------------+--------+
|    tuneIons_pos    |   922.009798   |  922.009798   |      [M+H]+      |        1         | 922.009798  |       1        | 243.6  |
+--------------------+----------------+---------------+------------------+------------------+-------------+----------------+--------+
|    tuneIons_neg    |   601.978977   |  601.978977   |      [M-H]-      |        -1        | 601.978977  |       -1       | 180.8  |
+--------------------+----------------+---------------+------------------+------------------+-------------+----------------+--------+
|    tuneIons_neg    |  1033.988109   |  1033.988109  |      [M-H]-      |        -1        | 1033.988109 |       -1       | 255.3  |
+--------------------+----------------+---------------+------------------+------------------+-------------+----------------+--------+



Skyline ion mobility library file
************************************
.. _imsdb:

The Skyline .imsdb file contains ion mobility CCS values used in Skyline for ion peak matching. A sample .imsdb file compiled from the 
library of `Yeast Metabolome Database <http://ymdb.ca/>`_ metabolites with CCS values contained in the Bakar lab `CCS database <https://brcwebportal.cos.ncsu.edu/baker/>`_
can be found in the repository located at ``skyline_documents/ymdb.imsdb``. For further information on compiling your own .imsdb library,
please see the Skyline `ion mobility tutorial <https://skyline.ms/wiki/home/software/Skyline/page.view?name=tutorial_ims>`_


Skyline document file
**********************

The Skyline .sky file contains the data processing parameters used by Skyline for peak detection and data processing (unless overwritten at command line call time). 
A sample Skyline document which includes CCS matching at IM resolving power 30 and TOF resolving power 30,000 is located at ``skyline_documents/ymdb_IMres30.sky``.
Note that the accompanying .sky.view, and .skyl files are auxiliary files associated with the given .sky document. Only the .sky file is required to load into AutonoMS. 
For more information on setting up a Skyline document, pelase see the Skyline `small molecule tutorial <https://skyline.ms/wiki/home/software/Skyline/page.view?name=tutorial_small_molecule>`_

Skyline report template
*************************

The Skyline .skyr report template determines the format and data contained in the output tabular file exported by Skyline after peak detection. 
A sample Skyline report template is located in the repository at ``report_templates/MoleculeReportShort.skyr``. This report will produce output with 
the following format:

Sample report output format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+--------------------+--------------------+---------------------------+------------------+------------------------------------+--------------+------------------+------------------------+---------------------------+------------------+------+--------+
| Molecule List Name |   Molecule Name    | Precursor Neutral Formula | Precursor Adduct |           Replicate Name           | Precursor Mz | Precursor Charge | Total Ion Current Area | Collisional Cross Section | Ion Mobility MS1 | Area | Height |
+====================+====================+===========================+==================+====================================+==============+==================+========================+===========================+==================+======+========+
|        ymdb        | 3-Methyladenine-p1 |          C6H7N5           |      [M+H]       | Inj00117-Positive-F1_demultiplexed |  150.077421  |        1         |       5347953.5        |           126.5           |      13.94       | 107  |  79    |
+--------------------+--------------------+---------------------------+------------------+------------------------------------+--------------+------------------+------------------------+---------------------------+------------------+------+--------+
|        ymdb        | 3-Methyladenine-p1 |          C6H7N5           |      [M+H]       | Inj00118-Positive-F2_demultiplexed |  150.077421  |        1         |       5281096.5        |           126.5           |      13.94       |  0   |   0    |
+--------------------+--------------------+---------------------------+------------------+------------------------------------+--------------+------------------+------------------------+---------------------------+------------------+------+--------+

Experiment definition file
************************************

The experiment definition file is a .xlsx file consisting of three sheets. A sample experiment definition file is located in the repostiory at ``experiment_templates/experimentTemplate.xlsx``

The first sheet "samples" contains the sample injection plan and 6560 acquisition method. Note that MS acquisition parameters must be saved into an Agilent .m method file
manually via MassHunter Workstation Data Acquisition. Also note that in BLAZE mode, the Column_Type does not matter but must be set to some value. In normal RapidFire injection
mode, the column type determines which column will be used for solid phase extraction (SPE). 

Sample sheet format
~~~~~~~~~~~~~~~~~~~~

+------+-------------+----------+---------------+------------------+-------------+----------------------------+------------+-------------+--------+
| Well | Description | Sequence | Sample_Number | Replicate_Number | Sample_Type |        6560_Method         | Plate_Type | Column_Type | Notes  |
+======+=============+==========+===============+==================+=============+============================+============+=============+========+
|  B1  |  Tune Mix   | Positive |       1       |        1         |    TUNE     | 2023-03-02_dodd_4bit_POS.m |    P384    |      C      |        |
+------+-------------+----------+---------------+------------------+-------------+----------------------------+------------+-------------+--------+
|  B2  |  IPA Blank  | Positive |       1       |        1         |    BLANK    | 2023-03-02_dodd_4bit_POS.m |    P384    |      C      |        |
+------+-------------+----------+---------------+------------------+-------------+----------------------------+------------+-------------+--------+

The second sheet, "rf_params" determines the RapidFire method parameters for a given experiment. Please see the example sheet for the full list of RapidFire parameters. More detailed parameter
descriptions can be found in the `RapidFire 365 manual <https://www.agilent.com/cs/library/usermanuals/public/G9531-90003_RapidFire365_User.pdf>`_. 


The third sheet, "data_analysis" contains the paths to the desired tune ions, Skyline imsdb, Skyline document, transition list, and Skyline report template files for a given experiment. 


Setting the AutonoMS configuration
*************************************

A configuration .toml file must be provided to AutonoMS runs together with the experiment definition file. The configuration file points AutonoMS to the correct paths for system installed
dependencies such as Agilent MassHunter and PNNL PreProcessor. In addition, it provides AutonoMS with the system configuration including the RapidFire IP address on the local network and 
allows the user to set certain Prefect run paramters such as timeout wait periods for different types of tasks and resource scaling (concurrency) options for different task types. 

A sample configuration file can be found in the repository at ``configs/genesis.toml``. Please note **you must modify these paths for your own system installations**. 

Performing Runs
****************

Once the dependencies, installation, input file preparation, and configurations are set AutonoMS can be run using the following command:

.. code-block:: shell

    autonoms-run -i exp.xlsx -c config.toml -o out_dir

Note that the manual check message can be bypassed by passing the ``-n`` flag to the ``autonoms-run``. 