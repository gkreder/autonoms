# Activate the conda environment
$envPath = "C:\Users\admin\miniconda3\Scripts\activate.bat"
$condaEnv = "wingui"
cmd.exe /c "call `"$envPath`" `"$condaEnv`" && python \\192.168.254.1\D\gkreder\scripts\rf_workflows.py touch_app"