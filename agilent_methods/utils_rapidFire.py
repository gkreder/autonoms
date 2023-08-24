################################################################################################
# gk@reder.io
################################################################################################
import sys
import os
import time
if sys.platform.startswith('win'):
    # Import only if running on Windows
    from pywinauto import Application
    from pywinauto import Desktop
    from pywinauto.controls.uia_controls import UIAElementInfo
import re
import shutil
################################################################################################
# Functions for individual actions in the RapidFire UI
################################################################################################
def initialize_app(search_str = "RapidFire :"):
    """Finds the (open) RapidFire UI application and returns its handles

    :param search_str: Identifying application text to search for, defaults to "RapidFire :"
    :type search_str: str, optional
    :return: Respectively the pywinauto application and pywinauto window corresponding to RapidFire UI
    :rtype: tuple
    """
    app = Application(backend = 'uia').connect(title_re = f".*RapidFire : .*")
    window = app.window(title_re = f".*{search_str}.*")
    if not window:
        sys.exit("error - couldnt find RapidFire ui window")
    return(app, window)

def load_rf_method(window, rfcfg_file):
    """Loads a RF method (.rfcfg)

    :param window: pywinauto window corresponding to the RapidFire UI
    :type window: `pywinauto.application.Application`
    """
    # e.g. rfcfg_file = M:\\Projects\\Default\\Data\\Rapidfire\\methods\\BLAZE_B-C_5000_125.rfcfg
    file_menu_item = window.child_window(title ="File", control_type = "MenuItem")
    file_menu_item.set_focus()
    file_menu_item.click_input()

    load_rf_method = window.child_window(title = "Load RF Method", control_type = "MenuItem")
    load_rf_method.set_focus()
    load_rf_method.click_input()

    file_name_input = window.child_window(title_re = f".*File name:", class_name = "Edit")
    file_name_input.set_focus()
    file_name_input.set_edit_text("")
    file_name_input.type_keys(f"{rfcfg_file}")
    open_button = window.child_window(title = "Open", class_name = "Button")
    open_button.set_focus()
    open_button.click_input()

def load_rf_batch(window, rfbat_file):
    """Loads a RF Batch (.rfbat)

    :param window: pywinauto window corresponding to the RapidFire UI
    :type window: `pywinauto.application.Application`
    :param rfbat_file: Path to .rfbat file (on RapidFire drive)
    :type rfbat_file: str
    """
    # e.g. rfbat_file = '''M:\\Projects\\Default\\Data\\Rapidfire\\batches\\RapidFireMaintenance.rfbat'''
    file_menu_item = window.child_window(title ="File", control_type = "MenuItem")
    file_menu_item.set_focus()
    file_menu_item.click_input()


    load_rf_batch = [x for x in file_menu_item.descendants() if "Load RF Batch" in x.window_text()][0]
    load_rf_batch.set_focus()
    load_rf_batch.click_input()

    file_name_input = window.child_window(title_re = f".*File name:", class_name = "Edit")
    file_name_input.set_focus()
    file_name_input.set_edit_text("")
    file_name_input.type_keys(f"{rfbat_file}")
    open_button = window.child_window(title = "Open", class_name = "Button")
    open_button.set_focus()
    open_button.click_input()


def check_vac_pressure(window, level_check = -50):
    """Ensures the RF pump vacuum pressure is below a certain threshold level (meaning that the pump is on and functioning)

    :param window: pywinauto window corresponding to the RapidFire UI
    :type window: `pywinauto.application.WindowSpecification`
    :param level_check: Pressure level (in kPa) above which error gets thrown (-60 kPa or below means pump is in good condition), defaults to -50
    :type level_check: float, optional
    """
    vac_text = window.child_window(auto_id = "vacTxt")
    vac_pressure = float(vac_text.get_value())
    if vac_pressure > level_check:
        sys.exit(f'Vacuum pressure is {vac_pressure}, is the vacuum on?')


def open_log_view(window, app):
    """Opens the RapidFire System Log window

    :param window: pywinauto window corresponding to RapidFire UI
    :type window: `pywinauto.application.WindowSpecification`
    :param app: pywinauto application corresponding to RapidFire UI
    :type app: `pywinauto.application.Application`
    :return: The pywinauto window object corresponding to the RF log window
    :rtype: `pywinauto.Application.WindowSpecification`
    """
    system_tools_menu = window.child_window(title = "System Tools", control_type = "MenuItem")
    system_tools_menu.set_focus()
    system_tools_menu.click_input()
    view_log_button = [x for x in system_tools_menu.descendants() if "View Log" in x.window_text()][0]
    view_log_button.set_focus()
    view_log_button.click_input()
    time.sleep(1)
    log_window = app.window(title_re = f".*RapidFire Log.*")
    return(log_window)

def set_run_mode(window, mode):
    """Sets the RF run mode (between plates and sequences)

    :param window: pywinauto window corresponding to RapidFire UI
    :type window: `pywinauto.Application.WindowSpecification`
    :mode: Desired run mode
    :type mode: str
    """
    mode_d = {'Sequences' : "admeModeBtn", "Plates" : "htsModeBtn"}
    if mode not in mode_d.keys():
        sys.exit(f"error - mode {mode} not found in available modes")
    radio = window.child_window(auto_id = mode_d[mode])
    radio.set_focus()

def press_start_button(window):
    """Presses the start (run) button

    :param window: pywinauto window corresponding to RapidFire UI
    :type window: `pywinauto.Application.WindowSpecification`
    """
    run_button = window.child_window(auto_id = "runBtn")
    run_button.set_focus()
    run_button.click_input()

def start_run(window, app, plate_timeout = 180):
    """Sets the RF run mode (between plates and sequences)
       
    :param window: pywinauto window corresponding to RapidFire UI
    :type window: `pywinauto.application.WindowSpecification`
    :param app: pywinauto application corresponding to RapidFire UI
    :type app: `pywinauto.application.Application`
    :param plate_timeout: Seconds to wait for plate run window to appear before erroring, defaults to 180
    :type plate_timeout: float, optional
    """
    check_vac_pressure(window)
    press_start_button(window)
    plate_window = app.window(auto_id = "NewPlatePrompt")
    try:
        # Wait for the plate selection window to become visible
        plate_window.wait('visible', timeout = plate_timeout)  
    except TimeoutError:
        sys.exit(f"Error - The plate run window did not appear within {timeout} seconds.")
    plate_window.set_focus()
    play_button = plate_window.child_window(auto_id = "playBtn")
    play_button.set_focus()
    play_button.click_input()


def stop_run(window):
    """Stops a run 

    :param window: pywinauto window corresponding to RapidFire UI
    :type window: `pywinauto.application.WindowSpecification`
    """
    # Press the stop run botton and confirm run abortion
    stop_button = window.child_window(auto_id = "stopBtn")
    stop_button.set_focus()
    stop_button.click_input()
    time.sleep(1)
    yes_button = window.child_window(auto_id = "button1")
    yes_button.set_focus()
    yes_button.click_input()


def get_rf_output_dir(rf_cfg_file):
    """Checks the RapidFire output directory for a given RF configuration file
        
    :param rf_cfg_file: Path to RF configuration file
    :type rf_cfg_file: str
    :return: Path to the RF data output directory
    :rtype: str
    """
    with open(rf_cfg_file, 'r') as f:
        lines = f.read()
    sd = [x for x in re.findall(r'.*SHARED_DATA_DIRECTORY.*', lines) if not x.startswith('//')]
    if len(sd) != 1:
        sys.exit(f'Error - couldnt find a singular SHARED_DATA_DIRECTORY in config file {rf_cfg_file}')
    sd = sd[0].split('=')[-1].strip().replace(';', '').split('"')[1].replace('"', '')
    return(sd)

def find_latest_dir(base_path, sequence_name = None, start_year = 2021, path_convert = None):
    """Gets the latest directory in the RapidFire data file tree

    :param base_path: Path to base RapidFire data directory
    :type base_bath: str
    :sequence_name: If provided, only check output directories containing data from RF sequence with given name, defaults to None
    :type sequence_name: str
    :param start_year: Starting year to look for in the RapidFire file tree, defaults to 2021
    :type start_year: int
    :param path_convert: If provided a dictionary of pathname swaps between the 6560 and RF computers on the shared drive
    :type path_convert: dict
    :return: Path to the latest-modified directory in the RF data file tree
    :rtype: str
    """
    if path_convert:
        for old_s, new_s in path_convert.items():
            base_path = base_path.replace(old_s, new_s)

    base_path = Path(base_path)
    latest_dir = None
    latest_date = None

    months = ['January', 'February', 'March', 'April', 'May', 'June', 
              'July', 'August', 'September', 'October', 'November', 'December']


    for year in range(start_year, datetime.datetime.now().year+1):  # Adjust the range as needed
        for month in range(0, 12):  # All possible months
            for day in range(1, 32):  # All possible days
                try:
                    dir_path = base_path / str(year) / months[month] / str(day)
                    if dir_path.exists() and dir_path.is_dir():
                        dir_date = datetime.datetime(year, month, day)
                        # Get a list of all directories in the date_path
                        dir_list = [os.path.join(dir_path, d) for d in os.listdir(dir_path) if os.path.isdir(os.path.join(dir_path, d))]
                        
                        # Sort the directories by creation time
                        dir_list.sort(key=lambda d: os.path.getmtime(d), reverse=True)
                        if sequence_name:
                            dir_list_temp = []
                            for dir_temp in dir_list:
                                # print(dir_temp)
                                rfdb_file = os.path.join(dir_temp, "RFDatabase.xml")
                                if not os.path.exists(rfdb_file):
                                    continue
                                with open(rfdb_file, 'r') as f:
                                    lines = f.read()
                                if f"Barcode>{sequence_name}<" in lines:
                                    dir_list_temp.append(dir_temp)
                            dir_list = dir_list_temp
                        if len(dir_list) > 0:
                            dir_newest = dir_list[0]
                            mtime = os.path.getmtime(dir_newest)
                            dir_modified = mtime
                            if latest_date is None or dir_modified > latest_date:
                                latest_dir = dir_newest
                                latest_date = mtime
                except ValueError:
                    # Ignore invalid dates, like February 30
                    pass
    return latest_dir

def copy_last_run_output(out_dir, rf_cfg_file, overwrite = True):
    """Copies the newest RF run data to a new directory

    :param out_dir: Path to output directory
    :type out_dir: str
    :param rf_cfg_file: Path to RF configuration file
    :type rf_cfg_file: str
    :param overwrite: Overwrite existing files, defaults to True
    :type overwrite: bool, optional
    """
    rf_data_dir = get_rf_output_dir(rf_cfg_file)
    rf_sequence_data_dir = find_latest_dir(rf_data_dir, path_convert = {"D:\\" : "M:\\"})

    if os.path.exists(out_dir):
        if overwrite:
            print(f"{out_dir} exists, removing to overwrite")
            os.chmod(out_dir, 0o777)
            shutil.rmtree(out_dir)
        else:
            sys.exit(f'{out_dir} exists, please set overwrite = True to overwrite')
    print(rf_sequence_data_dir)
    print(out_dir)
    # os.chmod(rf_data_dir, 0o777)
    shutil.copytree(rf_sequence_data_dir, out_dir)


def open_splitter_view(window, app):
    """Opens the file splitter dialogue in the RF UI

    :param window: pywinauto window corresponding to RapidFire UI
    :type window: `pywinauto.application.WindowSpecification`
    :param app: pywinauto application corresponding to RapidFire UI
    :type app: `pywinauto.application.Application`
    :return: pywinauto window corresponding to the file splitter dialogue
    :rtype: `pywinauto.application.WindowSpecification`
    """
    file_menu_item = window.child_window(title = "File", control_type = "MenuItem")
    file_menu_item.set_focus()
    file_menu_item.click_input()

    open_splitter_button = [x for x in file_menu_item.descendants() if "Convert MS Data" in x.window_text()][0]
    open_splitter_button.set_focus()
    open_splitter_button.click_input()
    time.sleep(1)

    splitter_window = [x for x in app.windows() if "Convert MS Data" in x.texts()][0]
    return(splitter_window)

def set_splitter_autoconvert(splitter_window, state):
    """Sets the file splitter dialogue state for the auto conversion option

    :param splitter_window: pywinauto window corresponding to the file splitter dialogue
    :type splitter_window: `pywinauto.application.WindowSpecification`
    :param state: desired auto conversion setting
    :type state: bool
    """
    if state not in [True, False]:
        sys.exit(f"Error unrecognized auto split state {state}")
    state = int(state)
    autoconvert_button = [x for x in splitter_window.children() if x.automation_id() == "autoConvertCheckBox"][0]
    if autoconvert_button.get_toggle_state() != state:
        autoconvert_button.toggle()
    return(0)


def run_split(splitter_window, split_dir, multiple_injections = True):
    """Runs file splitting through the file splitter dialogue

    :param splitter_window: pywinauto window corresponding to the file splitter dialogue
    :type splitter_window: `pywinauto.application.WindowSpecification`
    :param split_dir: Path to directory containing RF sequence output to split. Output split files will be placed here as well
    :type split_dir: str
    :param multiple_injections: Run multiple splits at once in parallel, defaults to True
    :type multiple_injections: bool, optional
    """

    data_path_box = [x for x in splitter_window.children() if x.automation_id() == "dataPathTextBox"][0]
    data_path_box.set_focus()
    data_path_box.set_edit_text("")
    data_path_box.type_keys(f"{split_dir}")

    output_path_box = [x for x in splitter_window.children() if x.automation_id() == "exportPathTextBox"][0]
    output_path_box.set_focus()
    output_path_box.set_edit_text("")
    output_path_box.type_keys(f"{split_dir}")

    if multiple_injections:
        multiple_inj_button = [x for x in splitter_window.children() if "multipleInj" in x.automation_id()][0]
        if multiple_inj_button.get_toggle_state() == 0:
            multiple_inj_button.toggle()

    convert_button = [x for x in splitter_window.children() if x.automation_id() == "exportButton"][0]
    convert_button.set_focus()
    convert_button.click_input()
    return(0)

################################################################################################
# Multi-step workflows
################################################################################################
def remote_run_rfbat(test = False, *args, **kwargs):
    """Runs a sequence on the RF

        :param test: Run in test mode, defaults to False
        :type test: bool, optional
        :param **rf_base_data_dir: Path to RF base data dir
        :type  **rf_base_data_dir: str
        :param **rfcfg_file: Path to RF .rfcfg method file
        :type **rfcfg_file: str
        :param **rfbat_file: Path to RF .rfbat batch file
        :type **rfbat_file: str
        :param **timeout_seconds: Seconds to wait before erroring
        :type **timeout_seconds: float
        :return: Path to directory containing run output files
        :rtype: str
    """
    print(f"Checking the rf data dir {kwargs['rf_base_data_dir']}...")
    rf_base_data_dir = kwargs['rf_base_data_dir']
    data_dir = find_latest_dir(rf_base_data_dir, path_convert = {'D:\\' : "M:\\"})
    if test:
        return(data_dir)
    # Must give it a rfbat_file
    app, window = initialize_app()
    open_log_view(window, app)
    splitter_window = open_splitter_view(window, app)
    set_splitter_autoconvert(splitter_window, False)
    set_run_mode(window, "Sequences")
    load_rf_method(window, kwargs['rfcfg_file'])
    load_rf_batch(window, kwargs['rfbat_file'])
    if not test:
        check_vac_pressure(window)
        start_run(window, app)
    print(f"Monitoring the batch.log file in directory {data_dir}...")
    log_file = os.path.join(data_dir, "batch.log")
    start_time = time.time()
    log_lines = ""
    print("Waiting for batch.log file to appear...")
    while not os.path.exists(log_file) and ( (time.time() - start_time) < kwargs['timeout_seconds']):
        time.sleep(1)
    print(f"...monitoring batch.log file...")
    while ("batch.log closed" not in log_lines) and ( (time.time() - start_time) < kwargs['timeout_seconds']):
        with open(log_file, 'r') as f:
            log_lines = f.read()
        time.sleep(1)
    return(data_dir)

def remote_file_split(test = False, *args, **kwargs):
    """Runs file splitting through the file splitter dialogue

    :param test: Run in test mode, defaults to False
    :type test: bool, optional
    :param **data_dir: Path to RF directory containing run output files
    :type **data_dir: str
    :param **timeout_seconds: Seconds to wait before erroring
    :type **timeout_seconds: float
    """
    data_dir = kwargs['data_dir']
    app, window = initialize_app()
    splitter_window = open_splitter_view(window, app)
    set_splitter_autoconvert(splitter_window, False)
    run_split(splitter_window, split_dir = data_dir)
    progress_text = [x for x in splitter_window.children() if x.automation_id() == "exportProgressLabel"][0]
    print(f"Waiting fo rfile splitting to start...")
    start_time = time.time()
    while ( "plate" not in [x.lower() for x in progress_text.texts()] ) and ( "Completed Successfully" not in progress_text.texts() ) and ( (time.time() - start_time) < kwargs['timeout_seconds']):
        time.sleep(1)
    print(f"..monitoring splitter progress...")
    while ( "Completed Successfully" not in progress_text.texts() ) and ( (time.time() - start_time) < kwargs['timeout_seconds']):
        time.sleep(1)
    return(0)
    

