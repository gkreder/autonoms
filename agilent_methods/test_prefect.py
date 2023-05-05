from prefect import flow, task, get_run_logger
import plate_map as pu
# from plate_map import create_sequences
import os
import glob
import shutil
import utils_6560 as msu
from prefect.client import get_client
import prefect.cli
import asyncio
from prefect.task_runners import SequentialTaskRunner
# from utilities import AN_IMPORTED_MESSAGE



# input_excel_file = '/Users/reder/OneDrive/right-bourbon/pilot_yeast_2/experimentTemplate.xlsx'
input_excel_file = "D:\\gkreder\\RapidSky\\agilent_methods\\experimentTemplate.xlsx"
output_dir = 'output'
pnnl_path = '''C:\\"Program Files"\\PNNL-Preprocessor\\PNNL-PreProcessor.exe'''

@task
def create_rf_sequences(input_excel_file, output_dir):
    sequence_files = pu.create_sequences(input_excel_file, output_dir)
    rfbat_files = []
    for sequence_name, rfbat_filename, rfmap_filename, rfcfg_filename in sequence_files:
        sequence_dir = os.path.join(output_dir, sequence_name)
        os.makedirs(sequence_dir, exist_ok = True)
        for fname in [rfbat_filename, rfmap_filename, rfcfg_filename]:
            bname = os.path.basename(fname)
            oname = os.path.join(sequence_dir, bname)
            os.replace(fname, oname)
        rfbat_files.append(os.path.join(sequence_dir, os.path.basename(rfbat_filename)))
    # rfbat_files = glob.glob(f"{output_dir}/*.rfbat")
    return(rfbat_files)

@task(tags = ["instrument_run"])
def run_calibration(rfbat_file, output_dir, test = False):
    sequence_name = os.path.basename(rfbat_file).replace('.rfbat', '')
    sequence_dir = os.path.join(output_dir, sequence_name) 
    output_calibration_file = os.path.join(sequence_dir, f"{sequence_name}_IM_calibration.d")
    ms_cal_method = pu.get_cal_method_rfbat(rfbat_file)
    if not test:
        mh_app, mh_window = msu.initialize_app()
        msu.run_calibration_B(ms_cal_method, output_calibration_file)
    else:
        print('TEST MODE')
        # with open(output_calibration_file, 'w') as f:
            # print(f"test of {ms_cal_method}", file = f)
    print(f'Calibration for method {ms_cal_method} ran and saved to {output_calibration_file}')
    # print(ms_cal_method)
    return(output_calibration_file)
 


@task(tags = ['pnnl'])
def demultiplex(d_file, pnnl_exe_path, overwrite = True, test = False, pnnl_MA = 3, pnnl_mInt = 20):
    d_file_prefix = os.path.basename(d_file).lower().replace(".d", "")
    d_file_dir = os.path.dirname(d_file)
    temp_out_dir = os.path.join(d_file_dir, f"{d_file_prefix}_temp_pnnl")
    os.makedirs(temp_out_dir, exist_ok = True)
    cmd = f'''{pnnl_exe_path} -demux=True -demuxMA={pnnl_MA} -mInt={pnnl_mInt} -overwrite={overwrite} -out={temp_out_dir} -dataset="{d_file}"'''
    print(f"demultiplexing {d_file}")
    print(cmd)
    if test:
        print('testing...not running command')
        return(d_file)
    os.system(cmd)
    pnnl_out_files = glob.glob(os.path.join(temp_out_dir, "*.d"))
    newest_pnnl_file = max(pnnl_out_files, key = os.path.getmtime)
    oname = os.path.join(d_file_dir, os.path.basename(newest_pnnl_file))
    if overwrite:
        os.replace(newest_pnnl_file, oname)
    else:
        shutil.move(newest_pnnl_file, oname)
    shutil.rmtree(temp_out_dir)
    return(d_file)






@flow(task_runner=SequentialTaskRunner(), name = "rfbat_workflow")
def rfbat_workflow(input_excel_file, output_dir, test = False):
    # print(get_client())
    client = get_client()
    client.create_concurrency_limit(tag = "instrument_run", concurrency_limit = 1)
    client.create_concurrency_limit(tag = "pnnl", concurrency_limit = 4)
    rfbat_files = create_rf_sequences.submit(input_excel_file, output_dir)
    output_calibration_files = run_calibration.map(rfbat_files, output_dir, test = test)
    demultiplexed_files = demultiplex.map(output_calibration_files, pnnl_path, test = False)
    

if __name__ == "__main__":
    rfbat_workflow(input_excel_file, output_dir, test = True)
    # rfbat_workflow.run()
    # rfbat_workflow(input_excel_file, output_dir, test = True)
    # asyncio.run(rfbat_workflow(input_excel_file, output_dir, test = True))

# rfbat_workflow(input_excel_file, output_dir)
