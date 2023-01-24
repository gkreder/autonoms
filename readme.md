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

Windows (deprecated for now)
``` bash
C:\Users\admin\Desktop\SkylineCmd.exe.lnk --in=D:\gkreder\RapidSky\skyline_documents\IMRes40.sky --import-transition-list=D:\gkreder\RapidSky\transition_lists\moi_aggregated_transitionList.csv --import-all-files=D:\Projects\Default\Data\RapidFire\2023\January\18\004\testSkylineCmd\sample_d_files/   --report-conflict-resolution=overwrite --report-format=tsv --report-add=D:\gkreder\RapidSky\report_templates\MoleculeReportCustom.skyr --report-name=MetaboliteReportCustom --report-file=D:\Projects\Default\Data\RapidFire\2023\January\18\004\testSkylineCmd\testOutWindows.tsv --out=D:\Projects\Default\Data\RapidFire\2023\January\18\004\testSkylineCmd\testOut.sky
```