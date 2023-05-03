import time
from pywinauto import Application
from pywinauto import Desktop
import sys
import os
import re
import argparse
import shutil



def get_window(start_str = "RapidFire :"):
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


def open_log_view(window):
    system_tools_menu = window.child_window(title = "System Tools", control_type = "MenuItem")
    system_tools_menu.set_focus()
    system_tools_menu.click_input()
    view_log_button = [x for x in system_tools_menu.descendants() if "View Log" in x.window_text()][0]
    view_log_button.set_focus()
    view_log_button.click_input()



app, window = get_window()
window.set_focus()


# Press the start run button
# run_button = window.child_window(auto_id = "runBtn")
# run_button.set_focus()
# run_button.click_input()

# Press the stop run botton and confirm run abortion
# stop_button = window.child_window(auto_id = "stopBtn")
# stop_button.set_focus()
# stop_button.click_input()
# time.sleep(1)
# yes_button = window.child_window(auto_id = "button1")
# yes_button.set_focus()
# yes_button.click_input()



# windows = Desktop(backend = 'uia').windows()
# for w in windows:
#     print(w.window_text())
# import pywinauto
# from pywinauto.uia_element_info import UIAElementInfo
# from pywinauto.controls.uiawrapper import UIAWrapper
# all_elements = pywinauto.findwindows.find_elements(title_re = f".*File", top_level_only = False)
# print(all_elements)
# he = pywinauto.findwindows.find_elements(title_re=f".*File &name:*", top_level_only = False)[0]
# uia_element_info = UIAElementInfo(he.handle)
# control_wrapper = UIAWrapper(uia_element_info)
# control_wrapper.set_focus()



