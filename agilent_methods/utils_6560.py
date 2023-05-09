import os
import sys
import time
if sys.platform.startswith('win'):
    # Import pywin libraries if we're running on windows
    from pywinauto import Application
    from pywinauto import Desktop
import re
import argparse
import shutil



def initialize_app(search_str = "Agilent MassHunter Workstation Data Acquisition", backend = 'uia'):
    app = Application(backend = backend).connect(title_re = f".*{search_str}")
    window = app.window(title_re = f".*{search_str}")
    if not window:
        print(f"Could not find window with title '{window_title}'")
        sys.exit(1)
    return(app, window)


def open_ms_method(window, method_name):

    open_method = window.child_window(auto_id = "openMethodBtn")
    open_method.set_focus()
    open_method.click_input()

    filename_input = window.child_window(auto_id = "txtFileName")
    filename_input.set_focus()
    filename_input.set_edit_text("")
    filename_input.type_keys(method_name)

    open_button = window.child_window(auto_id = "btnOpenSaveFile")
    open_button.set_focus()
    open_button.click_input()


def set_calibration_output(window, sample_name, out_d_file_name):
    sample_name_box = window.child_window(auto_id = "txtSampleName")
    sample_name_box.set_focus()
    sample_name_box.set_edit_text("")
    # sample_name.type_keys("")
    sample_name_box.type_keys(sample_name)

    output_name = window.child_window(auto_id = "txtSampleDataFileName")
    output_name.set_focus()
    output_name.set_edit_text("")
    output_name.type_keys(out_d_file_name)

    output_path = window.child_window(auto_id = "txtSampleDataPath")
    output_path.set_focus()
    # output_path.set_value("D:\Projects\Default\Data\6560\IM_Calibration")

    # Can change this later to just move the output file to the desired output directory
    op = output_path.legacy_properties()['Value']
    return(os.path.join(op, out_d_file_name))

    # if (os.path.join("D:", "\\Projects", "Default", "Data", "6560", "IM_calibration") != v):
        # sys.exit(f"Error - please set the output directory path to match expected IM_calibration output folder")
    # print(output_path.legacy_properties()['Value'] == '''D:\Projects\Default\Data\6560\IM_calibration''') # D:\Projects\Default\Data\6560\IM_calibration
    # sys.exit(output_path)


def get_instrument_state(window):
    state_colors = {"idle" : '#FF75C335', 'not ready' : "#FFFFBA00", "run" : "#FF4780EA", "prerun" : '#FF5F4AC9'}
    colors_state = {v : k for k,v in state_colors.items()}
    status_bar = window.child_window(auto_id = "AutomationId.StatusBar.StateLabel")
    status_color = status_bar.legacy_properties()["Value"]
    if status_color not in colors_state.keys():
        sys.exit(f"Error - couldnt find a state color for status color {status_color}")
    current_state = colors_state[status_color]
    return(current_state)

def wait_for_state(window, state, timeout_seconds):
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
    sample_run_pane = window.child_window(auto_id = "toolStrip1")
    run_button = sample_run_pane.child_window(title = "Run")
    run_button.set_focus()
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
        overwrite_button.set_focus()
        overwrite_button.click_input()

def stop_sample_run(window):
    sample_run_pane = window.child_window(auto_id = "toolStrip1")
    stop_button = sample_run_pane.child_window(title = "Stop")
    stop_button.set_focus()
    stop_button.click_input()
    time.sleep(5)

    # "User stopped the run" message
    ok_button = window.child_window(auto_id = "btnOK")
    start_time = time.time()
    while (not ok_button.exists()) and (time.time() - start_time) < 10:
        time.sleep(1)
    if ok_button.exists():
        ok_button.set_focus()
        ok_button.click_input()

def move_file(filename, output_name):
    # output_name = os.path.join(output_dir, os.path.basename(filename))
    # print(f"Moving file {filename} to {output_name}")
    os.rename(filename, output_name)
    # shutil.move(filename, output_name)


# output_d_file can be the entire path
def run_calibration_B(ms_method_name, output_d_filename_full, sample_name = "CalB", runtime = 45, overwrite = True, timeout_seconds = 180):
    app, window = initialize_app()
    if os.path.exists(output_d_filename_full):
        if overwrite:
            print(f"file {output_d_filename_full} exists, removing to overwrite")
            os.chmod(output_d_filename_full, 0o777)
            shutil.rmtree(output_d_filename_full)
            # os.remove(output_d_filename_full)
        else:
            sys.exit(f"file {output_d_filename_full} exists, please set overwrite to True and re-run to continue")

    open_ms_method(window, ms_method_name)
    output_d_file_base = os.path.basename(output_d_filename_full)
    agilent_output_file = set_calibration_output(window, sample_name, output_d_file_base)
    wait_for_state(window, "idle", timeout_seconds = timeout_seconds)
    start_sample_run(window, overwrite = overwrite)
    wait_for_state(window, "run", timeout_seconds = timeout_seconds)
    time.sleep(runtime) # Run has started, wait 45 seconds
    stop_sample_run(window)
    wait_for_state(window, 'idle', timeout_seconds = 500)
    if agilent_output_file != output_d_filename_full:
        move_file(agilent_output_file, output_d_filename_full)



#  run_calibration_B("2023-03-02_dodd_4Bit_POS_calB.m", os.path.join("D:\\", "gkreder", "2023-03-02_dodd_4Bit_POS_calB.d"))