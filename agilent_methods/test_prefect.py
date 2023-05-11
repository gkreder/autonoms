from prefect import flow, task, get_run_logger, pause_flow_run
import plate_map as pu
import utils_6560 as msu
import utils_rapidFire as rfu
import os
import glob
import shutil
from prefect.client import get_client
import asyncio
from prefect.task_runners import SequentialTaskRunner
import rpyc
import sys
import subprocess
import time
from datetime import datetime
from RapidSky.splitterExtract import get_splits
from RapidSky.CCSCal import ccs_cal


@task
def create_rf_sequences(input_excel_file, output_dir):
    sequence_files = pu.create_sequences(input_excel_file, output_dir)
    out_files = []
    rfbat_files = []
    sequence_dirs = []
    for sequence_name, rfbat_filename, rfmap_filename, rfcfg_filename in sequence_files:
        sequence_dir = os.path.join(output_dir, sequence_name)
        os.makedirs(sequence_dir, exist_ok = True)
        for fname in [rfbat_filename, rfmap_filename, rfcfg_filename]:
            bname = os.path.basename(fname)
            oname = os.path.join(sequence_dir, bname)
            os.replace(fname, oname)
        rfbat_filename_full = os.path.join(sequence_dir, os.path.basename(rfbat_filename)) 
        rfcfg_filename_full = os.path.join(sequence_dir, os.path.basename(rfcfg_filename)) 
        rfmap_filename_full = os.path.join(sequence_dir, os.path.basename(rfmap_filename)) 
        rfbat_files.append(rfbat_filename_full)
        sequence_dirs.append(sequence_dir)
        out_files.append((sequence_dir, rfbat_filename_full, rfcfg_filename_full, rfmap_filename_full))
    # rfbat_files = glob.glob(f"{output_dir}/*.rfbat")
    # return((rfbat_files, sequence_dirs))
    return(out_files)

@task(tags = ["instrument_run"])
def run_calibration(seq_files_tuple, output_dir, test = False):
    # sequence_name = os.path.basename(rfbat_file).replace('.rfbat', '')
    # sequence_dir = os.path.join(output_dir, sequence_name) 
    sequence_dir = seq_files_tuple[0]
    sequence_name = os.path.basename(sequence_dir)
    rfbat_file = seq_files_tuple[1]
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
    opref = os.path.splitext(d_file)[0]
    oname_final = opref + "_demultiplexed.d"
    for fname in [oname, oname_final]:
        if os.path.exists(fname):
            if overwrite:
                shutil.rmtree(fname)
            else:
                sys.exist(f"Erorr - the file {fname} exists, please set ovewrite = True to force overwrite")    
    shutil.move(newest_pnnl_file, oname)
    shutil.rmtree(temp_out_dir)
    if os.path.exists(oname_final):
        shutil.rmtree(oname_final)
    os.rename(oname, oname_final)
    return(oname_final)



@task(tags = ['pnnl'])
def ccs_calibration(mzml_file, d_file, tuneIons_file):
    print(f"Running CCS calibration on file {mzml_file} with output file {d_file}")
    print(f"tune ions file is {tuneIons_file}")
    ccs_override_string = ccs_cal(mzml_file, tuneIons_file)
    print(f"Override String = {ccs_override_string}")
    with open(os.path.join(d_file, "AcqData", 'OverrideImsCal.xml'), 'w') as f:
            print(ccs_override_string, file = f)


@task(tags = ['pnnl'])
def copy_ccs_calibration(uncalibrated_d_file, calibrated_d_file):
    print(f"Copying ccs calibration file from {calibrated_d_file} to {uncalibrated_d_file}")
    ccs_cal_file = os.path.join(calibrated_d_file, "AcqData", "OverrideImsCal.xml")
    copy_dir = os.path.join(uncalibrated_d_file, "AcqData")
    shutil.copy2(ccs_cal_file, copy_dir)



@flow(task_runner=SequentialTaskRunner(), name = "rfbat_prep")
def rfbat_prep(input_excel_file, output_dir, msconvert_exe, tuneIons_file, test = False):
    # print(get_client())
    client = get_client()
    client.create_concurrency_limit(tag = "instrument_run", concurrency_limit = 1)
    client.create_concurrency_limit(tag = "pnnl", concurrency_limit = 4)
    sequence_files = create_rf_sequences.submit(input_excel_file, output_dir)
    # REMEMBER to uncomment these!
    output_calibration_files = run_calibration.map(sequence_files, output_dir, test = test)
    demultiplexed_calibration_files = demultiplex.map(output_calibration_files, pnnl_path, test = False)
    calibration_mzmls = msconvert.map(demultiplexed_calibration_files, msconvert_exe)
    ccs_calibration.map(calibration_mzmls, demultiplexed_calibration_files, tuneIons_file)
    return(sequence_files)


    

@task
def remote_call(function_name, *args, **kwargs):
    conn = rpyc.connect("192.168.254.2", 18861)
    remote_function = conn.root.call_function
    result = remote_function(function_name, *args ,**kwargs)
    # fn = conn.teleport(rfu.initialize_app)
    # result = fn()
    conn.close()
    return(result)

@flow(task_runner = SequentialTaskRunner(), name = "rf_test_workflow")
def rf_test_workflow():
    rf_ip = "192.168.254.2"
    rf_function = "remote_run_rfbat"
    rf_call.submit(rf_ip, rf_function, rfbat_file = "M:\\Projects\\Default\\Data\\Rapidfire\\batches\\RapidFireMaintenance.rfbat").wait(10000)


@task(timeout_seconds = 10000, tags = ["instrument_run"])
def rf_call(rf_ip, rf_function, rf_port = 18861, *args,  **kwargs):
    rpyc_configs = {"sync_request_timeout" : 10000}
    connection = rpyc.connect(rf_ip, rf_port, config = rpyc_configs)
    try:
        rf_service = connection.root
        result = rf_service.call_function(rf_function, *args, **kwargs)
        return(result)
    finally:
        connection.close()  



 

@task
def start_rf_ms_connection(start_mh_rf_path):
    subprocess.call([start_mh_rf_path])




@flow(task_runner = SequentialTaskRunner(), name = "rf_plate_run", timeout_seconds = 1000000)
def rf_plate_run(sequence_dir, rfbat_file, rfcfg_file, start_mh_rf_path, test = False, path_convert = {'D:\\' : "M:\\"}):
    # rfbat_files = create_rf_sequences.submit(input_excel_file, output_dir)
    # output_calibration_files = run_calibration.map(rfbat_files, output_dir, test = test)
    client = get_client()
    client.create_concurrency_limit(tag = "instrument_run", concurrency_limit = 1)
    client.create_concurrency_limit(tag = "pnnl", concurrency_limit = 4)
    rf_ip = "192.168.254.2"
    rf_function = "remote_run_rfbat"
    sequence_dir_rf = sequence_dir
    rfbat_file_rf = rfbat_file
    rfcfg_file_rf = rfcfg_file
    for old_s, new_s in path_convert.items():
        sequence_dir_rf = sequence_dir_rf
        rfbat_file_rf = rfbat_file_rf.replace(old_s, new_s)
        rfcfg_file_rf = rfcfg_file_rf.replace(old_s, new_s)
    result = start_rf_ms_connection.submit(start_mh_rf_path)
    result.wait()
    result = rf_call.submit(rf_ip, rf_function, test = test, rfcfg_file = rfcfg_file_rf, rfbat_file = rfbat_file_rf)
    result.wait()    
    return(result)

@task(tags = ['pnnl'])
def split_d_file(split_tuple, raw_data_dir, out_dir, mh_splitter_exe):
    in_d_file_base, out_d_file_base, start_time, end_time = split_tuple
    print(split_tuple)
    in_d_file = os.path.join(raw_data_dir, in_d_file_base)
    out_d_file = os.path.join(out_dir, out_d_file_base)
    out_log_file = os.path.join(out_dir, "splitter_log.txt")
    arg_list = [mh_splitter_exe, in_d_file, out_d_file, f"{start_time}", f"{end_time}", "0", "0", out_log_file]
    print(arg_list)
    subprocess.call(arg_list)
    return(out_d_file)

@task(tags = ['pnnl'])
def msconvert(d_file, msconvert_exe):
    out_dir = os.path.dirname(d_file)
    out_file = os.path.splitext(d_file)[0] + ".mzML"
    arg_list = [msconvert_exe, d_file, "-o", out_dir]
    print(arg_list)
    subprocess.call(arg_list)
    return(out_file)

@flow
def copy_ms_files(sequence_dir, rapid_fire_data_dir, mh_splitter_exe, pnnl_exe, msconvert_exe):
    latest_dir = pu.find_latest_dir(rapid_fire_data_dir)
    splitter_file = os.path.join(latest_dir, "RFFileSplitter.log")
    rfdb_file = os.path.join(latest_dir, "RFDatabase.xml")
    sequence_file = os.path.join(latest_dir, "sequence1.d")
    splits = get_splits(splitter_file, rfdb_file, sequence_file)
    # print(splitter_file, rfdb_file, sequence_file)
    split_d_files = split_d_file.map(splits, latest_dir, sequence_dir, mh_splitter_exe)
    demultiplexed_files = demultiplex.map(split_d_files, pnnl_exe)
    # msconvert.map(demultiplexed_files, msconvert_exe)
    sequence_name = os.path.basename(sequence_dir)
    calibration_d_file = os.path.join(sequence_dir, sequence_name + "_IM_calibration_demultiplexed.d")
    copy_ccs_calibration.map(demultiplexed_files, calibration_d_file)

rf_username = 'admin'
rf_pw ='3000hanover'
rf_condaActivate_path = "C:\\Users\\admin\\miniconda3\\Scripts\\activate.bat"
rf_conda_envName = "wingui"


# input_excel_file = '/Users/reder/OneDrive/right-bourbon/pilot_yeast_2/experimentTemplate.xlsx'
# input_excel_file = "D:\\gkreder\\RapidSky\\agilent_methods\\experimentTemplate.xlsx"
input_excel_file = "D:\\gkreder\\RapidSky\\agilent_methods\\experimentTemplate_short.xlsx"
output_dir = 'D:\\gkreder\\scripts\\output'
pnnl_path = '''C:\\"Program Files"\\PNNL-Preprocessor\\PNNL-PreProcessor.exe'''
start_mh_rf_path = os.path.join("C:", "Agilent", "RapidFire Communicator", "RFMassHunter_NET", "bin", "Start_MassHunter_S.bat")
rapid_fire_data_dir = "D:\\Projects\\Default\\Data\\RapidFire"
mh_splitter_exe = "D:\\gkreder\\RapidFire_bin\\MHFileSplitter.exe"
msconvert_exe = os.path.join("C:\\Users\\admin\\AppData\\Local\\Apps", "ProteoWizard 3.0.22173.4a1045d 64-bit", "msconvert.exe")
tuneIons_file = "D:\\gkreder\\RapidSky\\transition_lists\\agilentTuneRestrictedDeimos_transitionList.csv"




if __name__ == "__main__":
    sequence_files = rfbat_prep(input_excel_file, output_dir, msconvert_exe, tuneIons_file, test = True).result()
    for sequence_dir, rfbat_file, rfcfg_file, rfmap_file in sequence_files:
        if "positive" not in sequence_dir.lower():
            continue
        # print(sequence_dir, rfbat_file, rfcfg_file, rfmap_file)
        # rf_plate_run(sequence_dir, rfbat_file, rfcfg_file, start_mh_rf_path, test = False)
        copy_ms_files(sequence_dir, rapid_fire_data_dir, mh_splitter_exe, pnnl_path, msconvert_exe)
        break



# Currently unused, for possible usage of PsExec for remote starting of the rpyc server
# @task
# def psexec(psexec_path, remote_ip, remote_username, remote_password, command, **kwargs):
#     # psexec_path = "C:\\PsTools\\PsExec.exe"
#     # run_psexec_task = RunPsExec(psexec_path, rf_ip, rf_username, rf_pw, remote_script_path)
#     # run_psexec_result = run_psexec_task()
#     # command = f"cmd.exe /c \"{rf_condaActivate_path} {rf_conda_envName} && python {remote_script_path}\""
#     # psexec(psexec_path, rf_ip, rf_username, rf_pw, command)
#     # psexec_command = f"{psexec_path} \\\\{remote_ip} -u {remote_username} -p {remote_password} -accepteula -h -nobanner {command}"
#     psexec_command = f"{psexec_path} \\\\{remote_ip} -d -i 1 -accepteula -h -nobanner {command}"
#     print("psexec_command:")
#     print(psexec_command)
#     print("")
#     os.system(psexec_command)