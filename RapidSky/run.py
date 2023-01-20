########################################################################
import sys
import os
import argparse
import subprocess
########################################################################
parser = argparse.ArgumentParser()
parser.add_argument('-dt', '--skyline_doc_template', required = True, type = str)
parser.add_argument('-rtf', '--skyline_report_template_file', required = True)
parser.add_argument('-rtn', '--skyline_report_template_name', required = True)
parser.add_argument('-tl', '--transition_list', required = True)
parser.add_argument('-d', '--data_file_dir', required = True)
parser.add_argument('-o', '--report_out_file', required = True)
parser.add_argument('-do', '--skyline_doc_out_file', required = True)
parser.add_argument('-imr', '--ims-library-res', type = float, required = True)
args = parser.parse_args()
########################################################################

isWindows = os.name == 'nt'
def toUnix(p):
    if isWindows:
        pOut = '/' + ':'.join(p.split(':')[1 : ]).replace(os.path.sep, '/')
    else:
        pOut = p
    pOut = p.replace('.', '/data')
    if pOut == '':
        pOut = '/data'
    return(pOut)

mountDrives = []
for fname in [args.skyline_doc_template, args.skyline_report_template_file, args.transition_list, args.data_file_dir, args.report_out_file, args.skyline_doc_out_file]:
    pdir = os.path.abspath(os.path.dirname(fname))
    if pdir not in mountDrives:
        mountDrives.append(pdir)

docker_image_name = "chambm/pwiz-skyline-i-agree-to-the-vendor-licenses"
skylineCmd = f"wine SkylineCmd --dir={toUnix(os.path.dirname(args.skyline_doc_template))} --in={args.skyline_doc_template} --ims-library-res=30 --import-transition-list={args.transition_list} --import-all-files={args.data_file_dir} --report-conflict-resolution=overwrite --report-format=tsv --report-add={args.skyline_report_template_file} --report-name={args.skyline_report_template_name} --report-file={args.report_out_file} --out={args.skyline_doc_out_file}"
dockerCmd = f"docker run --rm -e WINEDEBUG=-all "
for md in mountDrives:
    dockerCmd += f"-v {md}:{toUnix(md)} "
dockerCmd += f"{docker_image_name} "
cmd = dockerCmd + skylineCmd
print(cmd)