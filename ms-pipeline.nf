nextflow.enable.dsl=2

params.dfiles_dir = "$baseDir/sample_d_files/"
params.dfiles = params.dfiles_dir + "*.d"
params.conda = "$HOME/miniconda3/envs/deimos"
params.mzfile = "/home/filip/RapidSky/sample_d_files/s1.mzml"

workflow {
  Channel.fromPath(params.dfiles, type: 'dir') | convertCalibrate | collect | run_processing | view{it}
}

// run docker command to convert to .mzML 
process convert2mzml {
  input:
    path dfile
  output:
    path dfile

  shell:
  '''
  docker run --rm -e WINEDEBUG=-all -v !{params.dfiles_dir}:/data chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine msconvert !{dfile} 
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

// calibrate CCS using .mzML file, save results in origninal .d dir
process calibrateCCS {
  conda params.conda
  
  input:
    path dfile
  output:
    path dfile

  // remove mzml file after calibration?
  shell:
  '''
  df=!{dfile}
  mzfile=${df%.d}.mzML

  python !{baseDir}/RapidSky/CCSCal.py --inMZML !{params.dfiles_dir}/$mzfile --tuneIonsFile !{baseDir}/transition_lists/agilentTuneHighMass_transitionList.csv --outDir !{params.dfiles_dir}/!{dfile}
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
  echo !{x}

  docker run --rm -e WINEDEBUG=-all -v !{baseDir}:/data chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine SkylineCmd --in=skyline_documents/IMRes40.sky --import-transition-list=transition_lists/moi_aggregated_transitionList.csv --import-all-files=/data/sample_d_files/ --report-conflict-resolution=overwrite --report-add=report_templates/MoleculeReportCustom.skyr --report-name=MetaboliteReportCustom --report-format=tsv --report-file=outputReport.tsv --out=outputSkylineDoc.sky
  '''

}
