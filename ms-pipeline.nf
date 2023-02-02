nextflow.enable.dsl=2

// params.dfiles_dir = "$baseDir/sample_d_files/"
// params.dfiles = params.dfiles_dir + "*.d"
// params.conda = "$HOME/miniconda3/envs/deimos"
if ( params.dir == null ) { exit 1, 'Must supply a --dir input specifying input data directory' }
params.outDir = params.dir
params.dfiles = params.dir + "/*.d"
params.conda = "$HOME/miniconda3/envs/deimos"  

workflow {
  // Channel.fromPath(params.dfiles, type: 'dir') | convert2mzml | calibrateCCS | collect | run_processing | view{it}
  Channel.fromPath(params.dfiles, type: 'dir') | convert2mzml | calibrateCCS | run_processing | view{it}
  // Channel.fromPath(params.dfiles, type: 'dir') | convertCalibrate | collect | run_processing | view{it}
}

process convert2mzml {
  input:
    val dfile
  output:
    val dfile

  shell:
  '''
  file=$(basename !{dfile})
  docker run --rm -e WINEDEBUG=-all -v !{params.outDir}:/data chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine msconvert $file
  '''

}

// combines mzml conversion and calibration to one process, seems like channel
// waits for all instances of process to complete before starting next -
// if so, could make sense to do it like this
process convertCalibrate {
  conda params.conda
  input:
    path dfile
  output:
    path dfile

  // remove mzml file after calibration?
  shell:
  '''
  df=!{dfile}

  docker run --rm -e WINEDEBUG=-all -v !{params.dfiles_dir}:/data chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine msconvert $df

  mzfile=${df%.d}.mzML

  python !{baseDir}/RapidSky/CCSCal.py --inMZML !{params.dfiles_dir}/$mzfile --tuneIonsFile !{baseDir}/transition_lists/agilentTuneHighMass_transitionList.csv --outDir !{params.dfiles_dir}/!{dfile}
  '''
}

process calibrateCCS {
  conda params.conda
  input:
    path dfile
  output:
    val dfile

  shell:
  '''
  df=!{dfile}
  mzfile=${df%.d}.mzML

  python !{baseDir}/RapidSky/CCSCal.py --inMZML !{params.outDir}/$mzfile --tuneIonsFile !{baseDir}/transition_lists/agilentTuneHighMass_transitionList.csv --outDir !{params.outDir}/!{dfile}

  rm -f !{params.outDir}/$mzfile
  '''
}

// run processing on all .d files in .d directory
process run_processing {
  input:
    val x
  output:
    val x

  shell:
  '''
  docker run --rm -e WINEDEBUG=-all -v !{baseDir}:/data/baseDir -v !{params.outDir}:/data/outDir chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine SkylineCmd --in=/data/baseDir/skyline_documents/IMRes40.sky --import-transition-list=/data/baseDir/transition_lists/moi_aggregated_transitionList.csv --import-all-files=/data/outDir/ --report-conflict-resolution=overwrite --report-add=/data/baseDir/report_templates/MoleculeReportCustom.skyr --report-name=MetaboliteReportCustom --report-format=tsv --report-file=/data/outDir/outputReport.tsv --out=/data/outDir/outputSkylineDoc.sky
  '''
}
