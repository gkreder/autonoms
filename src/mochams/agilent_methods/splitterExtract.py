#!/usr/bin/env python
####################################################################################
import sys
import os
import re
import xml.etree.ElementTree as ET
import argparse
####################################################################################


def get_splits(splitterLog, RFDB, dFile):
    sequence = os.path.basename(dFile.lower()).replace(".demp.d", "").replace('.d', '').replace('sequence', '')
    tree = ET.parse(RFDB)
    root = tree.getroot()
    samples =  [x for x in root.iterfind("Plates/Plate/Injections/SampleInfo") if x.find(".//Name[.='Sequence']/../Value").text == sequence]
    barcodes = [s.find("./Field/Name[.='Barcode']/../Value").text for s in samples]
    if len(set(barcodes)) != 1:
        sys.exit('Error - more than one plate barcode found?')
    barcode = barcodes[0]

    with open(splitterLog, 'r') as f:
        logLines = f.read()
    splitterLines = re.findall(rf"Writing .*-{barcode}-.*\.d.*\n.*\n.*\n.*\n.*\n.*\nTime.*", logLines)

    def fl(l):
        return([(float(x), float(y)) for (x,y) in l])
    originalTimes = fl([x.split('\n')[1].split(': ')[-1].split('-') for x in splitterLines])
    effectiveTimes = fl([x.split('\n')[4].split(': ')[-1].split('-') for x in splitterLines])
    effectiveTimesStart = [x[0] for x in effectiveTimes]
    effectiveTimesEnd = [x[1] for x in effectiveTimes]
    if len(effectiveTimes) == 1:
        diffs = [0]
    else:
        diffs = [effectiveTimesStart[i] - effectiveTimesStart[i - 1] for i in range(1, len(effectiveTimesStart))]
        diffs = diffs + [diffs[-1]]
    newTimes = [(max(s - diffs[i], 0.1), e - diffs[i]) for i, (s,e) in enumerate(effectiveTimes)]
    outSufs = [re.findall(rf"Inj.*\.d", x)[0].replace('.d', '') for x in splitterLines]

    out_lines = []
    for i, (startTime_adjusted, endTime_adjusted) in enumerate(newTimes):
        outSuf = outSufs[i]
        t = (os.path.basename(dFile), f"{outSuf}.d", startTime_adjusted, endTime_adjusted)
        out_lines.append(t)
    return(out_lines)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--splitterLog', '-l', required = True)
    parser.add_argument('--dFile', '-d', required = True)
    parser.add_argument('--RFDB', '-b', required = True)
    args = parser.parse_args()
    out_lines = get_splits(args.splitterLog, args.RFDB, args.dFile)
    for sd, outSuf, startTime_adjusted, endTime_adjusted in out_lines:
        print(f'{sd} {outSuf}.d {startTime_adjusted} {endTime_adjusted}')


