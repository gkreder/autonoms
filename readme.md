# mocha-ms
Mass Omics and Chemical Hardware Automation MS

# Current pipeline


This repository contains code meant for automating the agilent RapidFire 365 + 6560 IM-QTOF system, both in terms of experimental runs on the hardware as well as the data analysis. Please note it is still under development. 

## agilent_methods

This folder contains newer code that automates experimental runs via pywinauto GUI automation and launches complete workflows including data preprocessing and analysis. Prefect is being used here since this pipeline is being hosted and run on the Windows Desktop hooked up to the Agilent 6560. 

The Agilent RapidFire and 6560 are each individually controlled by their own Windows Desktops that are connected to each other via ethernet. The rf_rpyc_server.py code hosts a rpyc server on the RapidFire computer so that RapidFire utility functions can be called remotely on the RapidFire control computer from the 6560 computer.

The utils_6560.py, utils_rapidFire.py, and utils_plates.py contain the core functions for respectively controlling the instruments and creating instrument files from user-supplied experiment definitions. 

The main workflow is contained in the prefect_workflow.py file though it is still under development. 

## RapidSky

The original code utilities used for the major steps in data preprocessing and analysis via Skyline after experimental runs are completed. Some of these have been replaced by code called directly in the Prefect workflow in agilent_methods since the original pipeline was running on a remote Linux computer. The new pipeline is being directly run on a Windows computer which means that some of the mass spec software can now be run natively instead of wrapped inside Docker. 

---

---


# Nextflow remote pipeline (deprecated)

## 1a - Conversion to MZML (Preprocessing)
``` bash
convertMZML.sh <sampleName.d>
```


## 1b - CCS Calibration (Preprocessing)
``` bash
python CCSCal.py --inMZML <sampleName.mzML> --tuneIonsFile <RapidSky/transition_lists/agilentTuneHighMass_transitionList.csv> --outDir <sampleName.d>
```


## 2 - Data Processing

Unix 
``` bash
docker run -it --rm -e WINEDEBUG=-all -v /dataLocation:/data chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine SkylineCmd --in=RapidSky/skyline_documents/IMRes40.sky --import-transition-list=RapidSky/transition_lists/moi_aggregated_transitionList.csv --import-all-files=/data/d_files_directory/ --report-conflict-resolution=overwrite --report-add=RapidSky/MoleculeReportCustom.skyr --report-name=MetaboliteReportCustom --report-format=tsv --report-file=<outputReport.tsv> --out=<outputSkylineDoc.sky>
```
Unix - Same as above, but with working example filepaths. `.d` files in `sample_d_files` directory in top-level `RapidSky` dir. Output files will be saved in top-level `RapidSky` dir. (Note path to `RapidSky` repo)

```bash
docker run -it --rm -e WINEDEBUG=-all -v /home/filip/RapidSky:/data chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine SkylineCmd --in=skyline_documents/IMRes40.sky --import-transition-list=transition_lists/moi_aggregated_transitionList.csv --import-all-files=/data/sample_d_files/ --report-conflict-resolution=overwrite --report-add=report_templates/MoleculeReportCustom.skyr --report-name=MetaboliteReportCustom --report-format=tsv --report-file=outputReport.tsv --out=outputSkylineDoc.sky
```


Windows (deprecated for now)
``` bash
C:\Users\admin\Desktop\SkylineCmd.exe.lnk --in=D:\gkreder\RapidSky\skyline_documents\IMRes40.sky --import-transition-list=D:\gkreder\RapidSky\transition_lists\moi_aggregated_transitionList.csv --import-all-files=D:\Projects\Default\Data\RapidFire\2023\January\18\004\testSkylineCmd\sample_d_files/   --report-conflict-resolution=overwrite --report-format=tsv --report-add=D:\gkreder\RapidSky\report_templates\MoleculeReportCustom.skyr --report-name=MetaboliteReportCustom --report-file=D:\Projects\Default\Data\RapidFire\2023\January\18\004\testSkylineCmd\testOutWindows.tsv --out=D:\Projects\Default\Data\RapidFire\2023\January\18\004\testSkylineCmd\testOut.sky
```

## Nextflow

Make sure Nextflow is installed, below it is assumed it is executable as `nextflow` from the this directory. It is also assumed a conda environment called `deimos` with the `CCSCal` dependencies is available in `$HOME/miniconda3/envs/deimos`, and the `.d` files are located in a directory called `sample_d_files` in this directory (add instructions on how to pass conda env and `.d` location as parameter). Run pipeline as

``` bash
nextflow ms-pipeline.nf
```
