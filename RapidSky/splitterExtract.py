#!/usr/bin/env python
####################################################################################
import sys
import os
import re
import xml.etree.ElementTree as ET
import argparse
####################################################################################
parser = argparse.ArgumentParser()
parser.add_argument('--splitterLog', '-l', required = True)
parser.add_argument('--dFile', '-d', required = True)
parser.add_argument('--RFDB', '-b', required = True)
args = parser.parse_args()
####################################################################################

sequence = os.path.basename(args.dFile.lower()).replace(".demp.d", "").replace('.d', '').replace('sequence', '')
tree = ET.parse(args.RFDB)
root = tree.getroot()
samples =  [x for x in root.iterfind("Plates/Plate/Injections/SampleInfo") if x.find(".//Name[.='Sequence']/../Value").text == sequence]
barcodes = [s.find("./Field/Name[.='Barcode']/../Value").text for s in samples]
if len(set(barcodes)) != 1:
    sys.exit('Error - more than one plate barcode found?')
barcode = barcodes[0]

with open(args.splitterLog, 'r') as f:
    logLines = f.read()
splitterLines = re.findall(rf"Writing .*-{barcode}-.*\.d.*\n.*\n.*\n.*\n.*\n.*\nTime.*", logLines)

def fl(l):
    return([(float(x), float(y)) for (x,y) in l])
originalTimes = fl([x.split('\n')[1].split(': ')[-1].split('-') for x in splitterLines])
effectiveTimes = fl([x.split('\n')[4].split(': ')[-1].split('-') for x in splitterLines])
effectiveTimesStart = [x[0] for x in effectiveTimes]
effectiveTimesEnd = [x[1] for x in effectiveTimes]
diffs = [effectiveTimesStart[i] - effectiveTimesStart[i - 1] for i in range(1, len(effectiveTimesStart))]
diffs = diffs + [diffs[-1]]
newTimes = [(max(s - diffs[i], 0.1), e - diffs[i]) for i, (s,e) in enumerate(effectiveTimes)]
outSufs = [re.findall(rf"Inj.*\.d", x)[0].replace('.d', '') for x in splitterLines]

for i, (startTime_adjusted, endTime_adjusted) in enumerate(newTimes):
    outSuf = outSufs[i]
    print(f'{os.path.basename(args.dFile)} {outSuf}.d {startTime_adjusted} {endTime_adjusted}')
