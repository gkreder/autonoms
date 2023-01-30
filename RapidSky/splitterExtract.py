#!/usr/bin/env python
####################################################################################
import sys
import os
import re
import xmltodict
import argparse
####################################################################################
parser = argparse.ArgumentParser()
parser.add_argument('--splitterLog', '-l', required = True)
parser.add_argument('--dFile', '-d', required = True)
parser.add_argument('--RFDB', '-b', required = True)
parser.add_argument('--methodsDir', '-m', required = True)
args = parser.parse_args()
####################################################################################
with open(args.RFDB, 'r') as f:
    d = xmltodict.parse(f.read())
with open(args.splitterLog, 'r') as f:
    logLines = f.read()
with open(os.path.join(args.dFile, "AcqData", 'MSTS.xml'), 'r') as f:
    mstsD = xmltodict.parse(f.read())['TimeSegments']['TimeSegment']


scanLength = ( ( float(mstsD['EndTime']) - float(mstsD['StartTime']) ) / float(mstsD['NumOfScans']) ) * 60 # Scan Length in Seconds
sampleInfoD = d['RFDatabase']['Plates']['Plate']['Injections']['SampleInfo']

def getSampleInfo(s):
    s = s['Field']
    s = {x['Name'] : x['Value'] for x in s}
    if 'DELAY' in s['Plate Position']:
        return(None, None, None)
    outSuf = f"Inj{int(s['Injection']):05}-{s['Barcode']}-{s['Plate Position']}"
    searchString = f"{outSuf}.d ...\nOriginal Time Range \(secs\):"
    l = re.findall(rf"{searchString}.*", logLines)[0]
    startTime = float(l.split(' ')[-1].split('-')[0])
    fnameMethod = [os.path.join(args.methodsDir, x) for x in os.listdir(args.methodsDir) if x == f"{s['RF Method']}.rfcfg"][0]
    with open(fnameMethod, 'r') as f:
        methodLines = f.read()
    methodD = xmltodict.parse(methodLines)['RFConfig']
    td = dict(zip(methodD['CycleNames']['string'], methodD['CycleDurations']['int']))
    # print(td)
    # mtMS = sum([float(x) for x in td.values()]) # method time in milliseconds
    mtMS = float(td['Load/Wash']) #BLAZE Mode Elution is in Load/Wash
    endTime = startTime + ( mtMS / 1000)
    startTime_adjusted = startTime - scanLength
    # endTime_adjusted = endTime + scanLength
    endTime_adjusted = endTime
    return(outSuf, startTime_adjusted, endTime_adjusted)
    print(f"{outSuf}.d", startTime_adjusted, endTime_adjusted)

list_output = []
for s in sampleInfoD:
    outSuf, startTime_adjusted, endTime_adjusted = getSampleInfo(s)
    if outSuf != None:
        # print(f'["{args.dFile}", "{outSuf}.d", {startTime_adjusted}, {endTime_adjusted}]')
        print(f'{os.path.basename(args.dFile)} {outSuf}.d {startTime_adjusted} {endTime_adjusted}')
        # print([args.dFile, f"{outSuf}.d", startTime_adjusted, endTime_adjusted])
        list_output.append([args.dFile, f"{outSuf}.d", startTime_adjusted, endTime_adjusted])

# print(list_output)

#### REMEMBER - when you actually call the file splitter, remove any existing output .d files that already exist
