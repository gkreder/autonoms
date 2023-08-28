################################################################################################
# gk@reder.io
################################################################################################
import os
import sys
import time
if sys.platform.startswith('win'):
    # Import pywin libraries if we're running on windows
    from pywinauto import Application
    from pywinauto import Desktop
import shutil

################################################################################################
# Functions for individual actions in the MassHunter Data Acquisition Program
################################################################################################
def initialize_app(search_str = "Agilent MassHunter Workstation Data Acquisition", backend = 'uia'):
    """Finds the (open) MassHunter Acquisition application and returns its handles

    :param search_str: Identifying application text to search for, defaults to "Agilent MassHunter Workstation Data Acquisition"
    :type search_str: str, optional
    :param backend: pywinauto backend to use, defaults to "uia"
    :type backend: str, optional
    :return: Respectively the pywinauto application and pywinauto window corresponding to MassHunter Workstation Data Acquisition
    :rtype: tuple
    """
    app = Application(backend = backend).connect(title_re = f".*{search_str}")
    window = app.window(title_re = f".*{search_str}")
    if not window:
        print(f"Could not find window with title '{window_title}'")
        sys.exit(1)
    return(app, window)


def open_ms_method(window, method_name):
    """Loads an MS acquisition method by name

    :param window: pywinauto window corresponding to MassHunter Workstation Data Acquisition
    :type window: `pywinauto.application.WindowSpecification`
    :param method_name: Acquisition method name
    :type method_name: str
    """

    open_method = window.child_window(auto_id = "openMethodBtn")
    # open_method.set_focus()
    open_method.click_input()

    filename_input = window.child_window(auto_id = "txtFileName")
    # filename_input.set_focus()
    filename_input.set_edit_text("")
    filename_input.type_keys(method_name)

    open_button = window.child_window(auto_id = "btnOpenSaveFile")
    # open_button.set_focus()
    open_button.click_input()


def set_calibration_output(window, sample_name, out_d_file_name):
    """Sets the output filename of a single-sample instrument run

    :param window: pywinauto window corresponding to MassHunter Workstation Data Acquisition
    :type window: `pywinauto.application.WindowSpecification`
    :param sample_name: Output metadata sample name
    :type sample_name: str
    :param out_d_file_name: Output .d file name
    :type out_d_file_name: str
    :return: Full path to the output .d file
    :rtype: str
    """
    sample_name_box = window.child_window(auto_id = "txtSampleName")
    # sample_name_box.set_focus()
    sample_name_box.set_edit_text("")
    sample_name_box.type_keys(sample_name)

    output_name = window.child_window(auto_id = "txtSampleDataFileName")
    # output_name.set_focus()
    output_name.set_edit_text("")
    output_name.type_keys(out_d_file_name)

    output_path = window.child_window(auto_id = "txtSampleDataPath")
    # output_path.set_focus()

    # Can change this later to just move the output file to the desired output directory
    op = output_path.legacy_properties()['Value']
    out_path = os.path.join(op, out_d_file_name)
    return(op)


def get_instrument_state(window):
    """Function for monitoring the 6560 instrument state in the main MH Data Acquisition Window

    :param window: pywinauto window corresponding to MassHunter Workstation Data Acquisition
    :type window: `pywinauto.application.WindowSpecification`
    :return: Instrument state
    :rtype: str
    """
    state_colors = {"idle" : '#FF75C335', 'not ready' : "#FFFFBA00", "run" : "#FF4780EA", "prerun" : '#FF5F4AC9'}
    colors_state = {v : k for k,v in state_colors.items()}
    status_bar = window.child_window(auto_id = "AutomationId.StatusBar.StateLabel")
    status_color = status_bar.legacy_properties()["Value"]
    if status_color not in colors_state.keys():
        sys.exit(f"Error - couldnt find a state color for status color {status_color}")
    current_state = colors_state[status_color]
    return(current_state)

def wait_for_state(window, state, timeout_seconds):
    """Waits for 6560 to reach a given state by monitoring the main MH Data Acquisition window

    :param window: pywinauto window corresponding to MassHunter Workstation Data Acquisition
    :type window: `pywinauto.application.WindowSpecification`
    :param state: Desired state (one of ["idle", "not read", "run", "prerun"])
    :type state: str
    :param timeout_seconds: Seconds to wait for instrument to reach state before erroring
    :type timeout_seconds: float
    """
    # Green (idle) = '#FF75C335'
    # Yellow (not ready) = "#FFFFBA00"
    # Blue (run) = "#FF4780EA"
    # Purple (prerun) = '#FF5F4AC9'
    start_time = time.time()
    current_state = "(initializing state check)"
    reached_state = (current_state == state)
    while (time.time() - start_time < timeout_seconds) and not reached_state:
        time.sleep(1)
        new_state = get_instrument_state(window)
        if new_state != current_state:
            print(f"Waiting for state {state}....Instrument currently in state {new_state}")
        current_state = new_state
        reached_state = (current_state == state)
    if not reached_state:
        sys.exit(f"Error - instrument timed out reaching state {state} after {timeout_seconds} seconds")
    print(f"Instrument reached state {state}")

def start_sample_run(window, overwrite = True):
    """Starts a single sample run

    :param window: pywinauto window corresponding to MassHunter Workstation Data Acquisition
    :type window: `pywinauto.application.WindowSpecification`
    :param overwite: Overwrite existing output file, defaults to True
    :type overwite: bool, optional
    """
    sample_run_pane = window.child_window(auto_id = "toolStrip1")
    run_button = sample_run_pane.child_window(title = "Run")
    # run_button.set_focus()
    run_button.click_input()

    check_overwrite_text = "Starting the run will overwrite the existing data file. Do you want to continue?"
    continued = True
    if (window.child_window(auto_id =  "txtBlockMessageText").exists()):
        if overwrite:
            overwrite_button = window.child_window(auto_id = "btnYes")
        else:
            overwrite_button = window.child_window(auto_id = "btnNo")
            continued = False
            print(f"Existing output file name and overwrite was set to False - aborting")
        # overwrite_button.set_focus()
        overwrite_button.click_input()

def stop_sample_run(window):
    """Stops a running single sample run

    :param window: pywinauto window corresponding to MassHunter Workstation Data Acquisition
    :type window: `pywinauto.application.WindowSpecification`
    """
    sample_run_pane = window.child_window(auto_id = "toolStrip1")
    stop_button = sample_run_pane.child_window(title = "Stop")
    # stop_button.set_focus()
    stop_button.click_input()
    time.sleep(5)

    # "User stopped the run" message
    ok_button = window.child_window(auto_id = "btnOK")
    start_time = time.time()
    while (not ok_button.exists()) and (time.time() - start_time) < 10:
        time.sleep(1)
    if ok_button.exists():
        # ok_button.set_focus()
        ok_button.click_input()


def run_calibration_B(ms_method_name, output_d_filename_full, sample_name = "CalB", runtime = 30, manual_stop = True, overwrite = True, timeout_seconds = 900):
    """Runs calibrant line B using the specified MS method acquisition parameters and saves the output

    :param ms_method_name: Path to .m file for the MS acquisition method
    :type ms_method_name: str
    :param output_d_filename_full: Path to output .d file
    :type output_d_filename_full: str
    :param sample_name: Sample name in metadata entry, defaults to "CalB"
    :type sample_name: str, optional
    :param runtime: Acquisition time (in seconds), defaults to 30
    :type runtime: float, optional
    :param manual_stop: If true, leave to the user to close dialog boxes after run has stopped, defaults to True
    :type manual_stop: bool, optional
    :param overwrite: If true, overwrite existing output file, defaults to True
    :type overwrite: bool, optional
    :param timeout_seconds: Allowed wait time for instrument to reach ready and idle states, defaults to 900
    :type timeout_seconds: float, optional
    """
    app, window = initialize_app()
    if os.path.exists(output_d_filename_full):
        if overwrite:
            print(f"file {output_d_filename_full} exists, removing to overwrite")
            os.chmod(output_d_filename_full, 0o777)
            shutil.rmtree(output_d_filename_full)
        else:
            sys.exit(f"file {output_d_filename_full} exists, please set overwrite to True and re-run to continue")

    open_ms_method(window, ms_method_name)
    output_d_file_base = os.path.basename(output_d_filename_full)
    agilent_output_file = set_calibration_output(window, sample_name, output_d_file_base)
    reset_button = window.child_window(auto_id = "resetMethodBtn")
    # reset_button.set_focus()
    reset_button.click_input()
    yes_button = window.child_window(auto_id = "btnYes")
    start_time = time.time()
    while (not yes_button.exists()) and (time.time()- start_time) < 15:
        time.sleep(1)
    if yes_button.exists():
        # yes_button.set_focus()
        yes_button.click_input()
    wait_for_state(window, "idle", timeout_seconds = timeout_seconds)
    start_sample_run(window, overwrite = overwrite)
    wait_for_state(window, "run", timeout_seconds = timeout_seconds)
    if manual_stop:
        time.sleep(runtime) # Run has started
        stop_sample_run(window)
    else:
        # "Run Completed" message box
        ok_button = window.child_window(auto_id = "btnOK")
        start_time = time.time()
        while (not ok_button.exists()) and (time.time() - start_time) < 15:
            time.sleep(1)
        if ok_button.exists():
            # ok_button.set_focus()
            ok_button.click_input()
        wait_for_state(window, "idle", timeout_seconds = timeout_seconds)

    wait_for_state(window, 'idle', timeout_seconds = timeout_seconds)
    if agilent_output_file != output_d_filename_full:
        os.rename(agilent_output_file, output_d_filename_full)
