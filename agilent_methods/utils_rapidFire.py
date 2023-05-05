import sys
import os
import time
if sys.platform.startswith('win'):
    from pywinauto import Application
    from pywinauto import Desktop
    from pywinauto.controls.uia_controls import UIAElementInfo
import re
import argparse
import shutil
import glob


def initialize_app(start_str = "RapidFire :"):
    app = Application(backend = 'uia').connect(title_re = f".*RapidFire : .*")
    window = app.window(title_re = f".*RapidFire : .*")
    if not window:
        sys.exit("error - couldnt find RapidFire ui window")
    return(app, window)

def load_rf_method(window, rfcfg_file):
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
    vac_text = window.child_window(auto_id = "vacTxt")
    vac_pressure = float(vac_text.get_value())
    if vac_pressure > level_check:
        sys.exit(f'Vacuum pressure is {vac_pressure}, is the vacuum on?')


def open_log_view(window, app):
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
    mode_d = {'Sequences' : "admeModeBtn", "Plates" : "htsModeBtn"}
    if mode not in mode_d.keys():
        sys.exit(f"error - mode {mode} not found in available modes")
    radio = window.child_window(auto_id = mode_d[mode])
    radio.set_focus()
    # radio.click_input() # just setting focus activates the radio button

def press_start_button(window):
    # Press the start run button
    run_button = window.child_window(auto_id = "runBtn")
    run_button.set_focus()
    run_button.click_input()

def start_run(window, app, plate_timeout = 180):
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
    # Press the stop run botton and confirm run abortion
    stop_button = window.child_window(auto_id = "stopBtn")
    stop_button.set_focus()
    stop_button.click_input()
    time.sleep(1)
    yes_button = window.child_window(auto_id = "button1")
    yes_button.set_focus()
    yes_button.click_input()


def get_rf_output_dir(rf_cfg_file):
    with open(rf_cfg_file, 'r') as f:
        lines = f.read()
    sd = [x for x in re.findall(r'.*SHARED_DATA_DIRECTORY.*', lines) if not x.startswith('//')]
    if len(sd) != 1:
        sys.exit(f'Error - couldnt find a singular SHARED_DATA_DIRECTORY in config file {rf_cfg_file}')
    sd = sd[0].split('=')[-1].strip().replace(';', '').split('"')[1].replace('"', '')
    return(sd)


def find_newest_rftime_dir(base_dir, min_depth = 4, max_depth=4):
    newest_rftime = None
    newest_rftime_path = None

    for depth in range(min_depth, max_depth + 1):
        pattern = os.path.join(base_dir, *('*' * depth), 'batch.rftime')
        for rftime_path in glob.glob(pattern):
            # Skip directories that end with ".d"
            if any(part.endswith('.d') for part in rftime_path.split(os.sep)):
                continue

            # Get the modification time of the file
            rftime_mtime = os.path.getmtime(rftime_path)

            # Check if this is the newest rftime file found so far
            if newest_rftime is None or rftime_mtime > newest_rftime:
                newest_rftime = rftime_mtime
                newest_rftime_path = rftime_path
    
    if not newest_rftime: # still equals None
        sys.exit(f'Error - I couldnt find any batch.rftime files in {base_dir} at depths {min_depth}-{max_depth}')
    newest_dir = os.path.dirname(newest_rftime_path)
    return(newest_dir)


def find_latest_data_dir(rf_cfg_file):
    rf_data_dir = get_rf_output_dir(rf_cfg_file)
    newest_dir = find_newest_rftime_dir(rf_data_dir)
    return(newest_dir)


def copy_last_run_output(out_dir, rf_cfg_file, overwrite = True):
    rf_data_dir = find_latest_data_dir(rf_cfg_file)
    if os.path.exists(out_dir):
        if overwrite:
            print(f"{out_dir} exists, removing to overwrite")
            os.chmod(out_dir, 0o777)
            shutil.rmtree(out_dir)
        else:
            sys.exit(f'{out_dir} exists, please set overwrite = True to overwrite')
    print(rf_data_dir)
    print(out_dir)
    # os.chmod(rf_data_dir, 0o777)
    shutil.copytree(rf_data_dir, out_dir)


##################################################
# Needs more work as the uia backend likely can't 
# access properties that will update pump 
# inidcator (or the checkbox)
##################################################
# def get_pump_status(window, pump_number):
#     if pump_number not in [1,2,3,4]:
#         sys.exit(f"Error - pump_number must be an integer 1-4")
#     indicator = window.child_window(auto_id = f"pump{pump_number}Ind")
#     indicator.set_focus()
#     print(dir(indicator))
#     print(vars(indicator))
#     print(indicator.dump_tree())
#     # rect = indicator.rectangle()
#     # x = ( rect.right - rect.left ) / 2
#     # y = ( rect.bottom - rect.top ) / 2
#     # screenshot = pyautogui.screenshot()
#     # pixel_color = screenshot.getpixel((x, y))
#     # print(pixel_color)


# app, window = initialize_app()
# window.set_focus()



# rf_cfg_file = '''C:\\Agilent\\RapidFire\\FIA_configs\\RapidFire.cfg'''
# output_data_dir = find_latest_data_dir(rf_cfg_file)


# copy_last_run_output('''M:\\test_output''', rf_cfg_file)

