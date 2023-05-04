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
parser.add_argument('--skipSeq', '-s', default = None)
parser.add_argument('--rawTimes', action = 'store_true')
args = parser.parse_args()
####################################################################################
with open(args.RFDB, 'r') as f:
    d = xmltodict.parse(f.read())
with open(args.splitterLog, 'r') as f:
    logLines = f.read()
with open(os.path.join(args.dFile, "AcqData", 'MSTS.xml'), 'r') as f:
    mstsD = xmltodict.parse(f.read())['TimeSegments']['TimeSegment']


scanLength = ( ( float(mstsD['EndTime']) - float(mstsD['StartTime']) ) / float(mstsD['NumOfScans']) ) * 60 # Scan Length in Seconds
endTimeCeil = ( float(mstsD['EndTime']) * 60 ) - 0.01 # So we don't try to slice past the end of the file
# startTimeFloor = ( float(mstsD['StartTime']) * 60 )
startTimeFloor = 0.0
dPlates =  d['RFDatabase']['Plates']['Plate']
if type(dPlates) == type([]):
    plateNum = int(os.path.basename(args.dFile).split('.')[0].replace('sequence', ''))
    sampleInfoD = d['RFDatabase']['Plates']['Plate'][plateNum - 1]['Injections']['SampleInfo']
elif type(dPlates) == type({'a' : 1}):
    sampleInfoD = d['RFDatabase']['Plates']['Plate']['Injections']['SampleInfo']

if args.rawTimes:
    searchString = f"Effective Time Range for splitting"
    l2 = float(re.findall(rf"{searchString}.*", logLines)[-1].split(' ')[-1].split('-')[0].strip())
    l1 = float(re.findall(rf"{searchString}.*", logLines)[-2].split(' ')[-1].split('-')[0].strip())
    effectiveOffset = l2 - l1

def getSampleInfo(s):
    s = s['Field']
    s = {x['Name'] : x['Value'] for x in s}
    if 'DELAY' in s['Plate Position']:
        return(None, None, None)
    if args.skipSeq != None and ((s['Sequence'] == args.skipSeq) or (int(s['Sequence']) == int(args.skipSeq))):
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
    # mtMS = sum([float(x) for x in td.values()]) # method time in milliseconds
    mtMS = float(td['Load/Wash']) #BLAZE Mode Elution is in Load/Wash
    if args.rawTimes: # changed scheme for time calculations
        ###########################
        # Calculating a shift based on MH Delay from raw times
        ###########################
        # mhOffset = float(re.findall(rf"Applying MassHunter delay .*", logLines)[-1].split(' ')[-1].strip())
        # # offset = (sum([float(x) for x in td.values()]) / 1000) # method time in milliseconds
        # # offset = (mtMS / 1000) # method time in milliseconds
        # # offset = 0
        # offset = mhOffset
        # endTime = float(l.split(' ')[-1].split('-')[1].strip())
        # startTime_adjusted = max( ( startTime - (offset) ), startTimeFloor)
        # # startTime_adjusted = startTime
        # endTime_adjusted = min(endTime - (offset), endTimeCeil)

        ###########################
        # Calculating a shift based on the adjusted times
        ###########################
        searchString = f"Effective Time Range for splitting .*\n.*{outSuf}.d"
        l = re.findall(rf"{searchString}.*", logLines)[0]
        startTime = float(l.split('\n')[0].split(' ')[-1].split('-')[0])
        endTime = float(l.split('\n')[0].split(' ')[-1].split('-')[1].strip())
        startTime_adjusted = startTime - effectiveOffset
        endTime_adjusted = endTime - effectiveOffset
        # mhOffset = float(re.findall(rf"Applying MassHunter delay .*", logLines)[-1].split(' ')[-1].strip())
        # # offset = (sum([float(x) for x in td.values()]) / 1000) # method time in milliseconds
        # # offset = (mtMS / 1000) # method time in milliseconds
        # # offset = 0
        # offset = mhOffset
        # endTime = float(l.split(' ')[-1].split('-')[1].strip())
        # startTime_adjusted = max( ( startTime - (offset) ), startTimeFloor)
        # # startTime_adjusted = startTime
        # endTime_adjusted = min(endTime - (offset), endTimeCeil)

        
    else:
        endTime = min(startTime + ( mtMS / 1000) + scanLength, endTimeCeil)
        startTime_adjusted = startTime - scanLength
        endTime_adjusted = endTime
    return(outSuf, startTime_adjusted, endTime_adjusted)

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