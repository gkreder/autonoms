################################################################################################
# gk@reder.io
################################################################################################
import os
import glob
import toml
import shutil
import rpyc
import sys
import subprocess
import pandas as pd
import argparse
from prefect import flow, task
from prefect.client import get_client
from prefect.task_runners import SequentialTaskRunner
import agilent_methods.utils_plates as pu
import agilent_methods.utils_6560 as msu
from agilent_methods.splitterExtract import get_splits
from agilent_methods.CCSCal import ccs_cal
################################################################################################
# Prefect Tasks
################################################################################################
@task
def create_rf_sequences(input_excel_file, output_dir):
    """Creates instrument files and output directories given experiment definition file

    :param input_excel_file: Input .xlsx file following experiment definition template
    :type input_excel_file: str
    :param output_dir: Desired top output directory
    :type output_dir: str
    :return: A list of tuples where each tuple corresponds to a sequence in the original input_excel_file
    :rtype: list
    """
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
    return(out_files)

@task(tags = ["instrument_run"], timeout_seconds = 100000000)
def run_6560_calibrant(seq_files_tuple, test = False):
    """Runs a Calibrant line (bottle B) run on the 6560 and saves the output

    :param seq_files_tuple: A tuple for a given experimental sequence consisting of (sequence_dir, rfbat_filename_full, rfcfg_filename_full, rfmap_filename_full)
    :type seq_files_tuple: tuple
    :param test: Run in test mode, defaults to False
    :type test: bool, optional
    :return: Path to the resulting .d file produced from calibrant run
    :rtype: str
    """
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
    print(f'Calibration for method {ms_cal_method} ran and saved to {output_calibration_file}')
    return(output_calibration_file)
 

@task(tags = ['preprocessing'])
def demultiplex(d_file, pnnl_exe_path, overwrite = True, test = False, demux_MA = 3, demux_mInt = 20, demux_min_percent = 97):
    """Runs IM-MS .d file demultiplexing using PNNL Preprocessor
    
    :param d_file: Path to input multiplexed .d file
    :type d_file: str
    :param pnnl_exe_path: Local path to PNNL Preprocessor executable
    :type pnnl_exe_path: str
    :param overwrite: Overwrite existing demultiplexed output, defaults to True
    :type overwrite: bool, optional
    :param test: Run in test mode, defaults to False
    :type test: bool, optional
    :param demux_MA: Corresponds to PNNL -demuxMA flag, demultiplexing frame moving average window (must be positive odd number), defaults to 3
    :type demux_MA: int, optional
    :demux_mInt: Corresponds to PNNL -mInt flag, Minimum intensity threshold for smoothing (must be >= 0), defaults to 20
    :type demux_mInt: int, optional
    :param demux_min_percent: Corresponds to PNNL -demuxSignal flag, minimum percentage of signal points required for inclusion in demultiplexed data (must be within range [50-100]), defaults to 97
    :type demux_min_percent: float, optional
    :return: Path to the resulting demultiplexed .d file
    :rtype: str
    """
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

@task(tags = ['preprocessing'])
def ccs_calibration(mzml_file, d_file, tuneIons_file):
    """Run CCS calibration given input standards ion file (.mzML), data file (.d), and known CCS values of standards

    :param mzml_file: Path to .mzML IM-MS file containing standards to calibrate with
    :type mzml_file: str
    :param d_file: Path to .d file containing experimental injection to CCS calibrate
    :type d_file: str
    :param tuneIons_file: Path to .csv file containing standards' m/z values and CCS values
    :type tuneIons_file: str
    :return: The string content of the xml IM-MS CCS calibration file required for .d file calibration
    :rtype: str
    """
    print(f"Running CCS calibration on file {mzml_file} with output file {d_file}")
    print(f"tune ions file is {tuneIons_file}")
    ccs_override_string = ccs_cal(mzml_file, tuneIons_file)
    print(f"Override String = {ccs_override_string}")
    with open(os.path.join(d_file, "AcqData", 'OverrideImsCal.xml'), 'w') as f:
            print(ccs_override_string, file = f)
    return(ccs_override_string)


@task(tags = ['preprocessing'])
def copy_ccs_calibration(uncalibrated_d_file, calibrated_d_file):
    """Copies the CCS calibration file from one .d file to another
    
    :param uncalibrated_d_file: Path to .d file to be calibrated
    :type uncalibrated_d_file: str
    :param calibrated_d_file: Path to .d file containing IM-MS calibration file
    :type calibrated_d_file: str
    """
    print(f"Copying ccs calibration file from {calibrated_d_file} to {uncalibrated_d_file}")
    ccs_cal_file = os.path.join(calibrated_d_file, "AcqData", "OverrideImsCal.xml")
    copy_dir = os.path.join(uncalibrated_d_file, "AcqData")
    shutil.copy2(ccs_cal_file, copy_dir)

# @task
# def remote_call(function_name, *args, **kwargs):
#     conn = rpyc.connect("192.168.254.2", 18861)
#     remote_function = conn.root.call_function
#     result = remote_function(function_name, *args ,**kwargs)
#     conn.close()
#     return(result)

@task(timeout_seconds = 100000, tags = ["instrument_run"])
def rf_call(rf_ip, rf_function, rf_port = 18861, *args,  **kwargs):
    """Calls a function from the utils_rapidFire module using the rpyc server running on the RapidFire computer. 
    Function is executed on the RapidFire computer itself. Function arguments are passed through *args and **kwargs

    :param rf_ip: IP address of the RapidFire computer on the local network
    :type rf_ip: str
    :param rf_function: Name of function from utils_rapidFire to call. Function arguments passed through *args and **kwargs
    :type rf_function: str
    :param rf_port: Port number on which the rpyc server is accessible, defaults to 18861 
    :type rf_port: int, optional
    :result: Result from function call
    :rtype: object
    """
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
    """Ensures the 6560 and RapidFire are connected to each other for data acquisition using the Agilent connection executable

    :param start_mh_rf_path: Path to Agilent 6560-RF connection executable
    :type start_mh_rf_path: str
    """
    print("Starting mh_rf connection...")
    print(start_mh_rf_path)
    print("")
    subprocess.call([start_mh_rf_path], shell = True)

@task(tags = ['preprocessing'])
def split_d_file(split_tuple, raw_data_dir, out_dir, mh_splitter_exe):
    """Splits a .d file from an entire RF-6560 sequence run and produces a .d file correspoding to the specified injection times

    :param split_tuple: Tuple containing the basename of the sequence .d file, desired output .d file name, and start/end times
    :type split_tuple: tuple
    :param raw_data_dir: Path to directory containing sequence .d file
    :type raw_data_dir: str
    :param out_dir: Path to split file output directory
    :type out_dir: str
    :param mh_splitter_exe: Path to Agilent file splitter utility executable
    :type mh_splitter_exe: str
    :return: Path to split .d file
    :rtype: str
    """
    in_d_file_base, out_d_file_base, start_time, end_time = split_tuple
    print(split_tuple)
    in_d_file = os.path.join(raw_data_dir, in_d_file_base)
    out_d_file = os.path.join(out_dir, out_d_file_base)
    out_log_file = os.path.join(out_dir, "splitter_log.txt")
    arg_list = [mh_splitter_exe, in_d_file, out_d_file, f"{start_time}", f"{end_time}", "0", "0", out_log_file]
    print(arg_list)
    subprocess.call(arg_list)
    return(out_d_file)

@task(tags = ['preprocessing'])
def msconvert(d_file, msconvert_exe):
    """Splits a .d file from an entire RF-6560 sequence run and produces a .d file corresponding to the specified injection times

    :param split_tuple: Tuple containing the basename of the sequence .d file, desired output .d file name, and start/end times
    :type split_tuple: tuple
    :param raw_data_dir: Path to directory containing sequence .d file
    :type raw_data_dir: str
    :param out_dir: Path to split file output directory
    :type out_dir: str
    :param mh_splitter_exe: Path to Agilent file splitter utility executable
    :type mh_splitter_exe: str
    :return: Path to split .d file
    :rtype: str
    """
    out_dir = os.path.dirname(d_file)
    out_file = os.path.splitext(d_file)[0] + ".mzML"
    arg_list = [msconvert_exe, d_file, "-o", out_dir]
    print(arg_list)
    subprocess.call(arg_list)
    return(out_file)

@task
def rm_tree(fname):
    """Utility function for removing multiple files in parallel via Prefect

    :param fname: Path to filename to delete
    :type fname: str
    :return: Path of deleted file
    :rtype: str
    """
    shutil.rmtree(fname)
    return(fname)

@task
def nearest_tune(df_sequence, well_file):
    """In a given experimental sequence, assign each non-TUNE sample row to its nearest TUNE injection for the purposes of CCS calibration. 
    Currently, nearest TUNE must occur before a given injection and the first injection of every sequence must be a TUNE injection.

    :param df_sequence: DataFrame corresponding to an experimental sequence
    :type df_sequence: `pandas.core.frame.DataFrame`
    :param well_file: Dictionary containing pairs well : output-filename for each well in the experimental sequence
    :type well_file: dict
    :return: List of tuples where each tuple matches an output injection filename to its nearest TUNE well
    :rtype: list
    """
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
    return pairs

##################################################################################################
# Prefect Flows
##################################################################################################
@flow(task_runner = SequentialTaskRunner(), name = "rf_post_run_calibration")
def rf_post_run_calibration(sequence_dir, demultiplexed_files, input_excel_file, tuneIons_file, msconvert_exe):
    """For an experimental sequence, runs the CCS calibration for each injection in the sequence
            
    :param sequence_dir: Path to sequence output directory
    :type sequence_dir: str
    :param demultiplexed_files: List of demultiplexed filenames
    :type demultiplexed_files: list
    :param input_excel_file: Path to experiment definition .xlsx file
    :type input_excel_file: str
    :param tuneIons_file: Path to .csv file containing standards' m/z values and CCS values
    :type tuneIons_file: str
    :param msconvert_exe: Path to msconvert executable
    :type msconvert_exe: str
    :return: List of tuples where each tuple matches an output calibrated injection filename to its nearest TUNE well
    :rtype: list
    """
    sequence_name = os.path.basename(sequence_dir)
    print(f"Running post run calibration on sequence {sequence_name}")
    print(demultiplexed_files)
    df = pd.read_excel(input_excel_file)
    df = pd.DataFrame(df[df['Sequence'] == sequence_name])
    df_tune = df[df['Sample_Type'] == "TUNE"]
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
def rfbat_prep(input_excel_file, output_dir):
    """Creates instrument files and sequence directories given an input experiment definition file.

    :param input_excel_file: Path to experiment definition .xlsx file
    :type input_excel_file: str
    :param output_dir: Desired top output directory
    :type output_dir: str
    :return: A list of tuples where each tuple corresponds files for a sequence in the original input_excel_file
    :rtype: list
    """
    # client = get_client()
    # client.create_concurrency_limit(tag = "instrument_run", concurrency_limit = 1)
    # client.create_concurrency_limit(tag = "preprocessing", concurrency_limit = 4)
    sequence_files = create_rf_sequences.submit(input_excel_file, output_dir)
    return(sequence_files)   

@flow(task_runner = SequentialTaskRunner(), name = "rf_plate_run", timeout_seconds = 10000)
def rf_plate_run(rfbat_file, rfcfg_file, start_mh_rf_path, rapid_fire_data_dir, test = False, path_convert = {'D:\\' : "M:\\"}, rf_ip = "192.168.254.2"):
    """Runs a RapidFire-6560 run for given sequence given its instrument files

    :param rfbat_file: Path to sequence .rfbat RapidFire file
    :type rfbat_file: str
    :param rfcfg_file: Path to sequence .rfcfg RapidFire file
    :type rfcfg_file: str
    :param start_mh_rf_path: Path to Agilent 6560-RF connection executable
    :type start_mh_rf_path: str
    :param rapid_fire_data_dir: Path to top-level directory where RapidFire is configured to output data
    :type rapid_fire_data_dir: str
    :param test: Run in test mode, defaults to False
    :type test: bool, optional
    :param path_convert: A dictionary of file path replacements between the 6560 and RapidFire shared drive (e.g. {"D:" : "M:"} means D: on 6560 corresponds to M: on RapidFire), defaults to {'D:\\' : "M:\\"}
    :type path_convert: dict, optional
    :param rf_ip: RapidFire IP address on local network, defaults to "192.168.254.2"
    :type rf_ip: str, optional
    :result: Result from RapidFire remote_run_rfbat function call
    :rtype: object
    """
    client = get_client()
    client.create_concurrency_limit(tag = "instrument_run", concurrency_limit = 1)
    client.create_concurrency_limit(tag = "preprocessing", concurrency_limit = 4)
    rf_function = "remote_run_rfbat"
    rfbat_file_rf = rfbat_file
    rfcfg_file_rf = rfcfg_file
    for old_s, new_s in path_convert.items():
        rfbat_file_rf = rfbat_file_rf.replace(old_s, new_s)
        rfcfg_file_rf = rfcfg_file_rf.replace(old_s, new_s)
    result = start_rf_ms_connection.submit(start_mh_rf_path)
    result.wait()
    result = rf_call.submit(rf_ip, rf_function, test = test, rfcfg_file = rfcfg_file_rf, rfbat_file = rfbat_file_rf, rf_base_data_dir = rapid_fire_data_dir, timeout_seconds = 10000)
    result.wait()    
    return(result)

@flow(task_runner = SequentialTaskRunner(), name = "rf_post_run_process")
def rf_post_run_process(sequence_dir, rapid_fire_data_dir, mh_splitter_exe, pnnl_exe, path_convert = {'D:\\' : "M:\\"}, rf_ip = "192.168.254.2"):
    """Runs post-acquisition file splitting and demultiplexing

    :param sequence_dir: Path to sequence directory
    :type sequence_dir: str
    :param rapid_fire_data_dir: Path to top-level directory where RapidFire is configured to output data
    :type rapid_fire_data_dir: str
    :param mh_splitter_exe: Path to Agilent file splitter utility executable
    :type mh_splitter_exe: str
    :param pnnl_exe: Local path to PNNL Preprocessor executable
    :type pnnl_exe: str
    :param path_convert: A dictionary of file path replacements between the 6560 and RapidFire shared drive (e.g. {"D:" : "M:"} means D: on 6560 corresponds to M: on RapidFire), defaults to {'D:\\' : "M:\\"}
    :type path_convert: dict, optional
    :param rf_ip: RapidFire IP address on local network, defaults to "192.168.254.2"
    :type rf_ip: str, optional
    :return: File paths of output split demultiplexed files
    :rtype: list
    """
    client = get_client()
    client.create_concurrency_limit(tag = "instrument_run", concurrency_limit = 1)
    sequence_name = os.path.basename(sequence_dir)
    latest_dir = pu.find_latest_dir(rapid_fire_data_dir, sequence_name = sequence_name)
    latest_dir_rf = latest_dir
    for old_s, new_s in path_convert.items():
        latest_dir_rf = latest_dir_rf.replace(old_s, new_s)
    # latest_dir_rf = latest_dir.replace("D:\\", "M:\\")
    remote_file_split_result = rf_call.submit(rf_ip, "remote_file_split", data_dir = latest_dir_rf, timeout_seconds = 100000).wait().result()
    splitter_file = os.path.join(latest_dir, "RFFileSplitter.log")
    rfdb_file = os.path.join(latest_dir, "RFDatabase.xml")
    sequence_file = os.path.join(latest_dir, "sequence1.d")
    sequence_file_moved = os.path.join(sequence_dir, "sequence1.d")
    for rf_file in ['batch.log', 'batch.rftime', 'platemap.tofmap.txt', 'RFDatabase.xml']:
        original_file = os.path.join(latest_dir, rf_file)
        shutil.copy2(original_file, sequence_dir)
    if os.path.exists(sequence_file_moved):
        shutil.rmtree(sequence_file_moved)
    shutil.copytree(sequence_file, sequence_file_moved)
    splits = get_splits(splitter_file, rfdb_file, sequence_file)
    injections_dir = os.path.join(sequence_dir, 'injections')
    os.makedirs(injections_dir, exist_ok = True)
    split_d_files = split_d_file.map(splits, latest_dir, injections_dir, mh_splitter_exe)
    demultiplexed_files = demultiplex.map(split_d_files, pnnl_exe)
    _ = rm_tree.map(split_d_files)
    sequence_name = os.path.basename(sequence_dir)
    return(demultiplexed_files)



@flow(task_runner = SequentialTaskRunner(), name = "skyline_analysis")
def skyline(sequence_dir, skyline_exe, sky_imsdb_file, sky_document_file, transition_list_file, sky_report_file):
    """Runs Skyline data analysis

    :param sequence_dir: Path to sequence directory
    :type sequence_dir: str
    :param skyline_exe: Path to Skyline command line executable
    :type skyline_exe: str
    :param sky_imsdb_file: Path to Skyline ion mobility database (.imsdb) file
    :type sky_imsdb_file: str
    :param sky_document_file: Path to Skyline template document (.sky) file
    :type sky_document_file: str
    :param transition_list_file: Path to target metabolite transition list file
    :type transition_list_file: str
    :param sky_report_file: Path to Skyline report output template (.skyr) file
    :type sky_report_file: str
    """
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
    """Helper function for initializing arguments on command line invocation
    :return: Parameter arguments
    :rtype: Namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_excel_file', required = True)
    parser.add_argument('--configs_toml', required = True)
    parser.add_argument('--output_dir', required = True)
    parser.add_argument('--test', action = "store_true")
    args = parser.parse_args()
    args.input_excel_file = os.path.abspath(args.input_excel_file)
    args.output_dir = os.path.abspath(args.output_dir)

    # Get executable locations from toml config file and data analysis parameters from experiment file
    execs_d = toml.load(args.configs_toml)
    df_analysis = pd.read_excel(args.input_excel_file, sheet_name = "data_analysis")
    analysis_d = df_analysis.set_index("Parameter")["Value"].to_dict()
    for k, v in {**execs_d, **analysis_d}.items():
        setattr(args, k, v)

    return(args)

@flow(task_runner = SequentialTaskRunner())
def main_flow(args):
    """The main workflow, calling the various sub-flows for running preparing files, running experiments, processing data, then performing analysis.
    Sequences are run experimentally in the order in which they appear in the input experiment definition file. Data from all sequences is collected before
    any data processing. 

    :param args: main flow arguments
    :type args: Namespace
    """
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
    sequence_files = rfbat_prep(args.input_excel_file, args.output_dir).result()
    rf_data_dirs = []
    for sequence_dir, rfbat_file, rfcfg_file, rfmap_file in sequence_files:
        sequence_rf_data_dir = rf_plate_run(rfbat_file, rfcfg_file, args.start_mh_rf_path, args.rapid_fire_data_dir, test = test).result()
        rf_data_dirs.append(sequence_rf_data_dir)
    for i_seq, (sequence_dir, rfbat_file, rfcfg_file, rfmap_file) in enumerate(sequence_files):
        demultiplexed_files = rf_post_run_process(sequence_dir, args.rapid_fire_data_dir, args.mh_splitter_exe, args.pnnl_path)
        copy_ccs_pairs = rf_post_run_calibration(sequence_dir, demultiplexed_files, args.input_excel_file, args.tuneIons_file, args.msconvert_exe)
        skyline_res = skyline(sequence_dir, args.skyline_exe, args.sky_imsdb_file, args.sky_document_file, args.transition_list_file, args.sky_report_file)

if __name__ == "__main__":
    args = get_args()
    main_flow(args)
     