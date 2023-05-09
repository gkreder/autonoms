nextflow.enable.dsl=2

params.input_excel_file = '/Users/reder/OneDrive/right-bourbon/pilot_yeast_2/experimentTemplate.xlsx'
params.output_dir = 'output'

workflow {
    input_excel_file = file(params.input_excel_file)

    Channel
        .fromPath(input_excel_file)
        .set { excel_ch }

    create_rf_sequences(excel_ch)
        .collect()
        .set { rfbat_files_ch }

    run_calibration(rfbat_files_ch.flatten())
}

process create_rf_sequences {
    input:
    file excel_file

    output:
    path "results/*.rfbat", emit: rfbat_files

    script:
    """
    #!/usr/bin/env python


    import os
    from plate_map import create_sequences
    create_sequences('${excel_file}', '${params.output_dir}')
    os.system("mkdir -p results")
    os.system("cp ${params.output_dir}/* results/")
    """
}

process run_calibration {
    input:
    file rfbat_file

    output:
    path "calibration_results/*"

    script:
    """
    #!/usr/bin/env python
    import sys
    import os

    rfbat_prefix = "${rfbat_file}".split('.')[0]
    os.system(f'mkdir -p {rfbat_prefix}')
    os.system(f"cp ${rfbat_file} {rfbat_prefix}/")
    os.system("mkdir -p calibration_results")
    os.system(f"cp ${rfbat_file} calibration_results/")
    """
}
