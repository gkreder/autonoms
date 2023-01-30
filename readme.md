# 1a - Conversion to MZML (Preprocessing)
``` bash
convertMZML.sh <sampleName.d>
```


# 1b - CCS Calibration (Preprocessing)
``` bash
python CCSCal.py --inMZML <sampleName.mzML> --tuneIonsFile <RapidSky/transition_lists/agilentTuneHighMass_transitionList.csv> --outDir <sampleName.d>
```


# 2 - Data Processing

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

# Nextflow
Make sure Nextflow is installed, below it is assumed it is executable as `nextflow` from the this directory. It is also assumed a conda environment called `deimos` with the `CCSCal` dependencies is available in `$HOME/miniconda3/envs/deimos`, and the `.d` files are located in a directory called `sample_d_files` in this directory (add instructions on how to pass conda env and `.d` location as parameter). Run pipeline as

``` bash
nextflow ms-pipeline.nf
```
