###########################################################
# Wrapper methods around the RF util functions for remote
# calls
###########################################################
import sys
import os
import re
import argparse
import shutil
import glob
import argparse
from utils_rapidFire import *

###########################################################
parser = argparse.ArgumentParser()
parser.add_argument("function", help = "Name of the function to be called")
parser.add_argument("--rfbat_file", help = ".rfbat file path")
args = parser.parse_args()


###########################################################


def startup():
    app, window = initialize_app()
    open_log_view(window, app)

def rf_maintenance_run(rfbat_file):
    app, window = startup()    
    set_run_mode(window, "Sequences")
    check_vac_pressure(window)
    load_rf_batch(rfbat_file)
    press_start_button(window)

def touch_app():
    app, window = initialize_app()
    open_log_view(window, app)
    window.set_focus()


if __name__ == "__main__":
    if args.function == "rf_maintenance_run":
        if not args.rfbat_file:
            sys.exit(f"Error - please provide an rfbat file")
        rf_maintenance_run(args.rfbat_file)
    elif args.function == "touch_app":
        touch_app()
    else:
        sys.exit(f"Please provide a valid rf_workflow function name")

