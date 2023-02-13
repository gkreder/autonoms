nextflow.enable.dsl=2

if ( params.dir == null ) { exit 1, 'Must supply a --dir input specifying input data directory' }
params.outDir = params.dir + "/out_files"
params.files2split = params.dir + "/*.d"
params.conda = "$HOME/miniconda3/envs/deimos"  

workflow {
  // Channel.fromPath(params.files2split, type: 'dir') | extractSplits | splitText | splitFile | convert2mzml | calibrateCCS | collect | run_processing | view{it}
  Channel.fromPath(params.files2split, type: 'dir') | convert2mzml | calibrateCCS | extractSplits | splitText | splitFile | collect | run_processing | view{it}
}

process extractSplits {
  conda params.conda
  input:
    path dfile
  output:
    stdout

  // if several .d-files in params.dir this will not work... (rm etc)
  shell:
  '''
  rm -rf !{params.outDir}
  mkdir -p !{params.outDir}
  chmod -R 777 !{params.outDir}
  chmod -R 777 !{params.dir}

  python !{baseDir}/RapidSky/splitterExtract.py -l !{params.dir}/RFFileSplitter.log -d !{params.dir}/!{dfile} -b !{params.dir}/RFDatabase.xml -m !{params.dir}/methods
  '''
}

process splitFile {
  input:
    val inTuple
  output:
    stdout

  // removes outdir, should we do it? or just remove .d-files, mzml etc if there are any?
  shell:
  '''
  IFS=' '
  read -a strarr <<< "!{inTuple}"
  inFile=${strarr[0]}
  outFile=${strarr[1]}
  start=${strarr[2]}
  end=${strarr[3]}

  logFile=${outFile%.d}.log

  docker run --rm -v !{params.dir}:/data/baseDir -v !{params.outDir}:/data/outDir splitter /bin/bash -c "wine /home/xclient/.wine/drive_c/splitter/MHFileSplitter.exe /data/baseDir/$inFile /data/outDir/$outFile $start $end 0 0 /data/outDir/$logFile; chmod a+wrx /data/outDir/$logFile; chmod -R a+wrx /data/outDir/$outFile;"

  echo $outFile
  '''
}

process convert2mzml {
  input:
    val dfile
  output:
    val dfile

  shell:
  '''
  file=$(basename !{dfile})
  docker run --rm -e WINEDEBUG=-all -v !{params.dir}:/data chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine msconvert $file
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
  df=$(basename !{dfile})
  mzfile=${df%.d}.mzML

  python !{baseDir}/RapidSky/CCSCal.py --inMZML !{params.dir}/$mzfile --tuneIonsFile !{baseDir}/transition_lists/agilentTuneHighMass_transitionList.csv --outDir !{params.dir}/$df

  rm -f !{params.dir}/$mzfile
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