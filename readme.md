Unix 
``` bash
docker run -it --rm -e WINEDEBUG=-all -v /Users/reder/OneDrive:/Users/reder/OneDrive chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine SkylineCmd --in=/Users/reder/RapidSky/skyline_documents/IMRes40.sky --import-transition-list=/Users/reder/OneDrive/convex-landing/moi_aggregated_transitionList.csv --import-all-files=/Users/reder/OneDrive/convex-landing/sample_d_files/ --report-conflict-resolution=overwrite --report-add=/Users/reder/OneDrive/convex-landing/MoleculeReportCustom.skyr --report-name=MetaboliteReportCustom --report-format=tsv --report-file=testOut.tsv --out=testOut.sky
```

Windows
``` bash
C:\Users\admin\Desktop\SkylineCmd.exe.lnk --in=D:\gkreder\RapidSky\skyline_documents\IMRes40.sky --import-transition-list=D:\gkreder\RapidSky\transition_lists\moi_aggregated_transitionList.csv --import-all-files=D:\Projects\Default\Data\RapidFire\2023\January\18\004\testSkylineCmd\sample_d_files/   --report-conflict-resolution=overwrite --report-format=tsv --report-add=D:\gkreder\RapidSky\report_templates\MoleculeReportCustom.skyr --report-name=MetaboliteReportCustom --report-file=D:\Projects\Default\Data\RapidFire\2023\January\18\004\testSkylineCmd\testOutWindows.tsv --out=D:\Projects\Default\Data\RapidFire\2023\January\18\004\testSkylineCmd\testOut.sky
```