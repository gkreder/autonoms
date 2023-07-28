from prefect import flow, task, get_run_logger, pause_flow_run
import utils_plates as pu
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
import pandas as pd
import argparse

################################################################################################
# Tasks
################################################################################################

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

@task(tags = ["instrument_run"], timeout_seconds = 100000000)
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
        msu.run_calibration_B(ms_cal_method, output_calibration_file, manual_stop = True)
    else:
        print('TEST MODE')
        # with open(output_calibration_file, 'w') as f:
            # print(f"test of {ms_cal_method}", file = f)
    print(f'Calibration for method {ms_cal_method} ran and saved to {output_calibration_file}')
    # print(ms_cal_method)
    return(output_calibration_file)
 


@task(tags = ['pnnl'])
def demultiplex(d_file, pnnl_exe_path, overwrite = True, test = False, demux_MA = 3, demux_mInt = 20, demux_min_percent = 97):
    d_file_prefix = os.path.basename(d_file).lower().replace(".d", "")
    d_file_dir = os.path.dirname(d_file)
    temp_out_dir = os.path.join(d_file_dir, f"{d_file_prefix}_temp_pnnl")
    os.makedirs(temp_out_dir, exist_ok = True)
    cmd = f'''{pnnl_exe_path} -demux=True -demuxMA={demux_MA} -demuxSignal={demux_min_percent} -mInt={demux_mInt} -frameComp=1 -compMode=Every -overwrite={overwrite} -out={temp_out_dir} -dataset="{d_file}"'''
    print(f"demultiplexing {d_file}")
    print(cmd)
    opref = os.path.splitext(d_file)[0]
    oname_final = opref + "_demultiplexed.d"
    if test:
        print('testing...not running command')
        return(oname_final)
    os.system(cmd)
    pnnl_out_files = glob.glob(os.path.join(temp_out_dir, "*.d"))
    newest_pnnl_file = max(pnnl_out_files, key = os.path.getmtime)
    oname = os.path.join(d_file_dir, os.path.basename(newest_pnnl_file))
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
    return(ccs_override_string)


@task(tags = ['pnnl'])
def copy_ccs_calibration(uncalibrated_d_file, calibrated_d_file):
    print(f"Copying ccs calibration file from {calibrated_d_file} to {uncalibrated_d_file}")
    ccs_cal_file = os.path.join(calibrated_d_file, "AcqData", "OverrideImsCal.xml")
    copy_dir = os.path.join(uncalibrated_d_file, "AcqData")
    shutil.copy2(ccs_cal_file, copy_dir)

@task
def remote_call(function_name, *args, **kwargs):
    conn = rpyc.connect("192.168.254.2", 18861)
    remote_function = conn.root.call_function
    result = remote_function(function_name, *args ,**kwargs)
    # fn = conn.teleport(rfu.initialize_app)
    # result = fn()
    conn.close()
    return(result)

@task(timeout_seconds = 100000, tags = ["instrument_run"])
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
    print("Starting mh_rf connection...")
    print(start_mh_rf_path)
    print("")
    subprocess.call([start_mh_rf_path], shell = True)

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

@task
def rm_tree(fname):
    shutil.rmtree(fname)
    return(fname)

@task
def nearest_tune(df_sequence, well_file):
    last_tune_well = None  # Initially there's no TUNE well
    pairs = []  # List to store the result pairs
    # Iterate over rows
    for idx, row in df_sequence.iterrows():
        # If this row is a TUNE row, update last_tune_well
        if row['Sample_Type'] == 'TUNE':
            last_tune_well = row['Well']
        # Otherwise, if there's been a TUNE well before this row, add a pair to the list
        else:
            if last_tune_well is None:
                sys.exit(f"Error - couldnt find a tune well for well {row['Well']}")
            pairs.append((row['Well'], last_tune_well))
    pairs = [tuple(well_file[y] for y in x) for x in pairs]
    # pairs = list(zip(*pairs))
    return pairs


##################################################################################################
# Flows
##################################################################################################

@flow(task_runner = SequentialTaskRunner(), name = "rf_post_run_calibration")
def rf_post_run_calibration(sequence_dir, demultiplexed_files, input_excel_file, tuneIons_file, msconvert_exe):
    sequence_name = os.path.basename(sequence_dir)
    print(f"Running post run calibration on sequence {sequence_name}")
    print(demultiplexed_files)
    df = pd.read_excel(input_excel_file)
    df = pd.DataFrame(df[df['Sequence'] == sequence_name])
    df_tune = df[df['Sample_Type'] == "TUNE"]
    print("")
    print(df_tune)
    print("")
    file_well = {x : os.path.basename(x).split('-')[-1].split('_')[0] for x in demultiplexed_files}
    well_file = {v : k for (k, v) in file_well.items()}
    tune_injection_files = df_tune["Well"].apply(lambda x : well_file[x]).values
    print(f"converting {tune_injection_files}")
    tune_mzmls = msconvert.map(tune_injection_files, msconvert_exe)
    print(f"tune_mzmls = {tune_mzmls}")
    tune_override_strings = ccs_calibration.map(tune_mzmls, tune_injection_files, tuneIons_file, wait_for = [tune_mzmls])
    copy_pairs = nearest_tune(df, well_file)
    uncalibrated_files, calibrated_files = zip(*copy_pairs)
    print(f"got copy pairs {copy_pairs}")
    copy_ccs_calibration.map(uncalibrated_files, calibrated_files)
    return(copy_pairs)

@flow(task_runner=SequentialTaskRunner(), name = "rfbat_prep", timeout_seconds = 100000000)
def rfbat_prep(input_excel_file, output_dir, msconvert_exe, tuneIons_file, cal_runtime = 45, test = False):
    # print(get_client())
    client = get_client()
    client.create_concurrency_limit(tag = "instrument_run", concurrency_limit = 1)
    client.create_concurrency_limit(tag = "pnnl", concurrency_limit = 4)
    sequence_files = create_rf_sequences.submit(input_excel_file, output_dir)
    return(sequence_files)   

@flow(task_runner = SequentialTaskRunner(), name = "rf_plate_run", timeout_seconds = 10000)
def rf_plate_run(sequence_dir, rfbat_file, rfcfg_file, start_mh_rf_path, rapid_fire_data_dir, test = False, path_convert = {'D:\\' : "M:\\"}):
    client = get_client()
    client.create_concurrency_limit(tag = "instrument_run", concurrency_limit = 1)
    client.create_concurrency_limit(tag = "pnnl", concurrency_limit = 4)
    rf_ip = "192.168.254.2"
    rf_function = "remote_run_rfbat"
    # sequence_dir_rf = sequence_dir
    rfbat_file_rf = rfbat_file
    rfcfg_file_rf = rfcfg_file
    for old_s, new_s in path_convert.items():
        # sequence_dir_rf = sequence_dir_rf.replace(old_s, new_s)
        rfbat_file_rf = rfbat_file_rf.replace(old_s, new_s)
        rfcfg_file_rf = rfcfg_file_rf.replace(old_s, new_s)
    result = start_rf_ms_connection.submit(start_mh_rf_path)
    result.wait()
    result = rf_call.submit(rf_ip, rf_function, test = test, rfcfg_file = rfcfg_file_rf, rfbat_file = rfbat_file_rf, rf_base_data_dir = rapid_fire_data_dir, timeout_seconds = 10000)
    result.wait()    
    return(result)

# task(tags = ['instrument_run'])
# def rf_split(rf_data_dir, test = False):
#     rf_ip = "192.168.254.2"
#     rf_function = "remote_file_split"
#     result = rf_call.submit(rf_ip, rf_function, test = test, data_dir = rf_data_dir, timeout_seconds = 10000)
#     result.wait()
#     return(0)

@flow(task_runner = SequentialTaskRunner(), name = "rf_post_run_process")
def rf_post_run_process(sequence_dir, rapid_fire_data_dir, mh_splitter_exe, pnnl_exe):
    client = get_client()
    client.create_concurrency_limit(tag = "instrument_run", concurrency_limit = 1)
    sequence_name = os.path.basename(sequence_dir)
    latest_dir = pu.find_latest_dir(rapid_fire_data_dir, sequence_name = sequence_name)
    latest_dir_rf = latest_dir.replace("D:\\", "M:\\")
    rf_ip = "192.168.254.2"
    remote_file_split_result = rf_call.submit(rf_ip, "remote_file_split", data_dir = latest_dir_rf, timeout_seconds = 100000).wait().result()
    # result.wait().result()
    splitter_file = os.path.join(latest_dir, "RFFileSplitter.log")
    rfdb_file = os.path.join(latest_dir, "RFDatabase.xml")
    sequence_file = os.path.join(latest_dir, "sequence1.d")
    sequence_file_moved = os.path.join(sequence_dir, "sequence1.d")
    for rf_file in ['batch.log', 'batch.rftime', 'platemap.tofmap.txt', 'RFDatabase.xml']:
        original_file = os.path.join(latest_dir, rf_file)
        # copy_file = os.path.join(sequence_dir, rf_file)
        # sys.exit((os.path.exists(original_file), original_file, copy_file))
        shutil.copy2(original_file, sequence_dir)
    if os.path.exists(sequence_file_moved):
        shutil.rmtree(sequence_file_moved)
    shutil.copytree(sequence_file, sequence_file_moved)
    splits = get_splits(splitter_file, rfdb_file, sequence_file)
    injections_dir = os.path.join(sequence_dir, 'injections')
    os.makedirs(injections_dir, exist_ok = True)
    # print(splitter_file, rfdb_file, sequence_file)
    split_d_files = split_d_file.map(splits, latest_dir, injections_dir, mh_splitter_exe)
    demultiplexed_files = demultiplex.map(split_d_files, pnnl_exe)
    _ = rm_tree.map(split_d_files)
    sequence_name = os.path.basename(sequence_dir)
    return(demultiplexed_files)



@flow(task_runner = SequentialTaskRunner(), name = "skyline_analysis")
def skyline(sequence_dir, skyline_exe, sky_imsdb_file, sky_document_file, transition_list_file, sky_report_file):
    skyline_dir = os.path.join(sequence_dir, "skyline_files")
    os.makedirs(skyline_dir, exist_ok = True)
    
    injection_dir = os.path.join(sequence_dir, 'injections')

    # Copy files and reassign variables
    shutil.copy2(sky_imsdb_file, skyline_dir)
    sky_imsdb_file = os.path.join(skyline_dir, os.path.basename(sky_imsdb_file))

    shutil.copy2(sky_document_file, skyline_dir)
    sky_document_file = os.path.join(skyline_dir, os.path.basename(sky_document_file))

    shutil.copy2(transition_list_file, skyline_dir)
    transition_list_file = os.path.join(skyline_dir, os.path.basename(transition_list_file))

    shutil.copy2(sky_report_file, skyline_dir)
    sky_report_file = os.path.join(skyline_dir, os.path.basename(sky_report_file))

    output_report_file = os.path.join(sequence_dir, "output_report.tsv")
    output_sky_file = os.path.join(sequence_dir, "skyline_results.sky")
    # print(skyline_exe)
    # sys.stdout.flush()
    # print('\n\n\n')
    arg_list = [skyline_exe, f"--in={sky_document_file}", 
                f"--import-transition-list={transition_list_file}",
                f"--import-all-files={injection_dir}",
                f"--report-conflict-resolution=overwrite",
                f"--report-add={sky_report_file}",
                f"--report-name=MetaboliteReportShort",
                f"--report-format=tsv",
                f"--report-file={output_report_file}",
                f"--out={output_sky_file}"
                ]
    cmd = " ".join(arg_list)
    print(f"Running skyline command {cmd}")
    subprocess.call(arg_list, shell = True)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_excel_file', required = True)
    parser.add_argument('--output_dir', required = True)
    parser.add_argument('--test', action = "store_true")
    args = parser.parse_args()
    args.input_excel_file = os.path.abspath(args.input_excel_file)
    args.output_dir = os.path.abspath(args.output_dir)


    args.pnnl_path = '''C:\\"Program Files"\\PNNL-Preprocessor\\PNNL-PreProcessor.exe'''
    args.start_mh_rf_path = os.path.join("C:\\Agilent", "RapidFire Communicator", "RFMassHunter_NET", "bin", "Start_MassHunter_S.bat")
    args.rapid_fire_data_dir = "D:\\Projects\\Default\\Data\\RapidFire"
    args.mh_splitter_exe = "D:\\gkreder\\RapidFire_bin\\MHFileSplitter.exe"
    args.msconvert_exe = os.path.join("C:\\Users\\admin\\AppData\\Local\\Apps", "ProteoWizard 3.0.22173.4a1045d 64-bit", "msconvert.exe")
    args.tuneIons_file = "D:\\gkreder\\RapidSky\\transition_lists\\agilentTuneRestrictedDeimos_transitionList.csv"
    args.skyline_exe = "C:\\Users\\admin\\Desktop\\SkylineCmd.exe.lnk"
    args.sky_imsdb_file = "D:\\gkreder\\RapidSky\\skyline_documents\\ymdb.imsdb"
    args.sky_document_file = "D:\\gkreder\\RapidSky\\skyline_documents\\ymdb_IMres30.sky"
    args.transition_list_file = "D:\\gkreder\\RapidSky\\transition_lists\\ymdb_transition_list.csv"
    args.sky_report_file = "D:\\gkreder\\RapidSky\\report_templates\\MoleculeReportShort.skyr"
    return(args)



@flow(task_runner = SequentialTaskRunner())
def test_seqs(sequence_dir, rfbat_file, rfcfg_file, rfmap_file):
    print(sequence_dir, rfbat_file, rfcfg_file, rfmap_file)

@flow(task_runner = SequentialTaskRunner())
def main_flow(args):
    test = args.test
    check_string = '''Running in live mode. Please ensure
    (1) MH Acq is set to autoLayout
    (2) RF Vacuum pump is turned on
    (3) The tune splitter is set to calibrant B inlet
    (4) You have tuned the 6560 
    
    Press Enter when ready...
    '''
    if not test:
        input(check_string)
    
    cal_runtime = 15
    sequence_files = rfbat_prep(args.input_excel_file, args.output_dir, args.msconvert_exe, args.tuneIons_file, cal_runtime = cal_runtime, test = test).result()
    rf_data_dirs = []
    for sequence_dir, rfbat_file, rfcfg_file, rfmap_file in sequence_files:
        sequence_rf_data_dir = rf_plate_run(sequence_dir, rfbat_file, rfcfg_file, args.start_mh_rf_path, args.rapid_fire_data_dir, test = test).result()
        rf_data_dirs.append(sequence_rf_data_dir)
    for i_seq, (sequence_dir, rfbat_file, rfcfg_file, rfmap_file) in enumerate(sequence_files):
        # rf_data_dir = rf_data_dirs[i_seq]
        # res = rf_split(rf_data_dir)
        # res.wait()
        demultiplexed_files = rf_post_run_process(sequence_dir, args.rapid_fire_data_dir, args.mh_splitter_exe, args.pnnl_path)
        copy_ccs_pairs = rf_post_run_calibration(sequence_dir, demultiplexed_files, args.input_excel_file, args.tuneIons_file, args.msconvert_exe)
        # skyline_res = skyline(sequence_dir, skyline_exe, sky_imsdb_file, sky_document_file, transition_list_file, sky_report_file, wait_for = [copy_ccs_pairs])
        skyline_res = skyline(sequence_dir, args.skyline_exe, args.sky_imsdb_file, args.sky_document_file, args.transition_list_file, args.sky_report_file)
if __name__ == "__main__":
    args = get_args()
    main_flow(args)
    



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


# @flow(task_runner = SequentialTaskRunner(), name = "rf_test_workflow")
# def rf_test_workflow():
#     rf_ip = "192.168.254.2"
#     rf_function = "remote_run_rfbat"
#     rf_call.submit(rf_ip, rf_function, rfbat_file = "M:\\Projects\\Default\\Data\\Rapidfire\\batches\\RapidFireMaintenance.rfbat").wait(10000)