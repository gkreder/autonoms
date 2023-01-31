nextflow.enable.dsl=2

params.dir = "$baseDir/sample_d_files"
params.outDir = params.dir + "/split_files"
params.files2split = params.dir + "/*.d"
params.conda = "$HOME/miniconda3/envs/deimos"

workflow {
  // Channel.fromPath(params.files2split, type: 'dir') | extractSplits | splitText | splitFile | view{it}

  // Channel.fromPath(params.outDir + "*.d", type: 'dir') | convertCalibrate | collect | run_processing | view{it}
  // Channel.fromPath(params.files2split, type: 'dir') | extractSplits | splitText | splitFile | convertCalibrate | collect | run_processing | view{it}
  Channel.fromPath(params.files2split, type: 'dir') | extractSplits | splitText | splitFile | convert2mzml | calibrateCCS | collect | run_processing | view{it}
}

process extractSplits {
  conda params.conda
  input:
    path dfile
  output:
    stdout
  // now all outDir is completely removed, should we just remove .d-files we actually create?? also how can we do in Dockerfile so we don't need to give 777 permissions?

  // rm -rf -f !{params.outDir} && mkdir !{params.outDir}
  // chmod 777 !{params.outDir}/
  shell:
  '''

  python !{baseDir}/RapidSky/splitterExtract.py -l !{params.dir}/RFFileSplitter.log -d !{params.dir}/!{dfile} -b !{params.dir}/RFDatabase.xml -m !{params.dir}/methods
  '''
}

process splitFile {
  input:
    val inTuple
  output:
    stdout

  shell:
  '''
  IFS=' '
  read -a strarr <<< "!{inTuple}"
  inFile=${strarr[0]}
  outFile=${strarr[1]}
  start=${strarr[2]}
  end=${strarr[3]}

  outDir="$(basename "!{params.outDir}")"
  logFile=${outFile%.d}.log
  
  chmod 777 -R !{params.outDir}

  docker run -v !{params.dir}:/data splitter /bin/bash -c "wine /home/xclient/.wine/drive_c/splitter/MHFileSplitter.exe $inFile $outDir/$outFile $start $end 0 0 $outDir/$logFile; chmod 777 $outDir/$outFile"
  
  echo $outFile
  '''
  // docker run -v !{params.dir}:/data splitter wine /home/xclient/.wine/drive_c/splitter/MHFileSplitter.exe $inFile $outDir/$outFile $start $end 0 0 $outDir/$logFile
  // docker run -v !{params.dir}:/data splitter chmod 777 $outDir/$outFile
  // echo $outFile
  // chmod 777 !{params.outDir}/$outFile
}

process convert2mzml {
  input:
    val dfile
  output:
    val dfile

  shell:
  '''
  docker run --rm -e WINEDEBUG=-all -v !{params.outDir}:/data chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine msconvert !{dfile}
  '''

}

process calibrateCCS {
  conda params.conda
  input:
    val dfile
  output:
    val dfile

  shell:
  '''
  df=!{dfile}
  mzfile=${df%.d}.mzML

  python !{baseDir}/RapidSky/CCSCal.py --inMZML !{params.outDir}/$mzfile --tuneIonsFile !{baseDir}/transition_lists/agilentTuneHighMass_transitionList.csv --outDir !{params.outDir}/!{dfile}
  '''
}


process convertCalibrate {
  conda params.conda
  input:
    val dfile
  output:
    path dfile

  // remove mzml file after calibration?
  shell:
  '''
  df=!{dfile}

  docker run --rm -e WINEDEBUG=-all -v !{params.outDir}:/data chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine msconvert $df

  mzfile=${df%.d}.mzML

  python !{baseDir}/RapidSky/CCSCal.py --inMZML !{params.outDir}/$mzfile --tuneIonsFile !{baseDir}/transition_lists/agilentTuneHighMass_transitionList.csv --outDir !{params.outDir}/!{dfile}
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
  docker run --rm -e WINEDEBUG=-all -v !{baseDir}:/data -v !{params.dir}:/data/data chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine SkylineCmd --in=skyline_documents/IMRes40.sky --import-transition-list=transition_lists/moi_aggregated_transitionList.csv --import-all-files=/data/data/split_files/ --report-conflict-resolution=overwrite --report-add=report_templates/MoleculeReportCustom.skyr --report-name=MetaboliteReportCustom --report-format=tsv --report-file=/data/data/split_files/outputReport.tsv --out=/data/data/split_files/outputSkylineDoc.sky
  '''

}
