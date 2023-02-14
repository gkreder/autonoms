nextflow.enable.dsl=2

if ( params.dir == null ) { exit 1, 'Must supply a --dir input specifying input data directory' }
params.outDir = params.dir + "/out_files"
params.files2split = params.dir + "/sequence*.d"
params.calibrate = "sequence1.d"
params.analyse = "sequence2.d"

params.conda = "$HOME/miniconda3/envs/deimos"  
params.methodsDir = "/mnt/backup/RapidFire/methods"

workflow {
  // Channel.fromPath(params.files2split, type: 'dir') | extractSplits | splitText | splitFile | convert2mzml | calibrateCCS | collect | run_processing | view{it}
  Channel.from(params.calibrate) | convert2mzml | calibrateCCS | extractSplits | splitText | splitFile | collect | run_processing | view{it}
}

process extractSplits {
  conda params.conda
  input:
    val dfile
  output:
    stdout

  // if several .d-files in params.dir this will not work... (rm etc)
  shell:
  '''
  # rm -rf !{params.outDir}
  mkdir -p !{params.outDir}
  # chmod -R 777 !{params.outDir}
  # chmod -R 777 !{params.dir}

  docker run --rm -v !{params.outDir}:!{params.outDir} -u root chambm/pwiz-skyline-i-agree-to-the-vendor-licenses /bin/bash -c "rm -rf !{params.outDir}; mkdir -p !{params.outDir}; chmod -R 777 !{params.outDir};"

  python !{baseDir}/RapidSky/splitterExtract.py --skipSeq 1 -l !{params.dir}/RFFileSplitter.log -d !{params.dir}/!{dfile} -b !{params.dir}/RFDatabase.xml -m !{params.methodsDir}
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
  docker run --rm -e WINEDEBUG=-all -v !{params.dir}:/data chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine msconvert !{dfile}
  '''

}

process calibrateCCS {
  conda params.conda
  input:
    val dfile
  output:
    val params.analyse

  shell:
  '''
  df=!{dfile}
  mzfile=${df%.d}.mzML

  python !{baseDir}/RapidSky/CCSCal.py --inMZML !{params.dir}/$mzfile --tuneIonsFile !{baseDir}/transition_lists/agilentTuneHighMass_transitionList.csv --outDir !{params.dir}/!{dfile}
  
  cp !{params.dir}/!{dfile}/AcqData/OverrideImsCal.xml !{params.dir}/!{params.analyse}/AcqData/OverrideImsCal.xml
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
  docker run --rm -e WINEDEBUG=-all -v !{baseDir}:/temp/baseDir -v !{params.outDir}:/temp/outDir chambm/pwiz-skyline-i-agree-to-the-vendor-licenses /bin/bash -c "cp /temp/baseDir/skyline_documents/moiAggregated.imsdb /temp/outDir/; cp /temp/baseDir/skyline_documents/IMRes40.sky /temp/outDir/; cp /temp/baseDir/transition_lists/moi_aggregated_transitionList.csv /temp/outDir/; cp /temp/baseDir/report_templates/MoleculeReportCustom.skyr /temp/outDir/; wine SkylineCmd --in=/temp/outDir/IMRes40.sky --import-transition-list=/temp/outDir/moi_aggregated_transitionList.csv --import-all-files=/temp/outDir/ --report-conflict-resolution=overwrite --report-add=/temp/outDir/MoleculeReportCustom.skyr --report-name=MetaboliteReportCustom --report-format=tsv --report-file=/temp/outDir/outputReport.tsv --out=/temp/outDir/outputSkylineDoc.sky;"
  '''
}
