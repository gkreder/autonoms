import paramiko

rf_ip = "192.168.254.2"
rf_username = 'admin'
rf_pw ='3000hanover'

ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_client.connect(rf_ip, username = rf_username, password = rf_pw)


conda_path = "C:\\Users\\admin\\miniconda3\\Scripts\\conda.exe"
activate_path = "C:\\Users\\admin\\miniconda3\\Scripts\\activate.bat"
conda_environment = "wingui"
remote_script_path = "\\\\192.168.254.1\\D\\gkreder\\scripts\\rf_local.py"
command = f"{activate_path} {conda_environment} && python {remote_script_path}"
print(f"Running command - {command}\n\n")
# command = "python"
stdin, stdout, stderr = ssh_client.exec_command(command)

print(f"Output: {stdout.read().decode()}")
print(f"Error: {stderr.read().decode()}")

ssh_client.close()