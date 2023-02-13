########################################################################
import sys
import os
import argparse
import deimos
import pandas as pd
import numpy as np
########################################################################
parser = argparse.ArgumentParser()
parser.add_argument('-i', '--inMZML', required = True)
parser.add_argument('-t', '--tuneIonsFile', required = True)
parser.add_argument('-o', '--outDir', required = True)
parser.add_argument('--tol', default = 0.01)
parser.add_argument('--bufferGasMass', default = 28.006148)
# 28.006148 - AutoCCS N2
# 28.013 - Deimos N2
args = parser.parse_args()
########################################################################

print('Loading data...')
data = deimos.load(args.inMZML, accession={'retention_time': 'MS:1000016', 'drift_time': 'MS:1002476', 'Positive Scan' : "MS:1000130", 'Negative Scan' : 'MS:1000129'})
ms1 = data['ms1']
posModeI = len(ms1['Positive Scan'].mode().values)
negModeI = len(ms1['Negative Scan'].mode().values)
if posModeI > 0 and negModeI > 0:
    sys.exit('Error - I see scans in both positive and negative mode in the same mzML file')
# mode = {1.0 : 'Positive', 0 : 'Negative'}[ms1['Positive Scan'].mode().values[0]]
if posModeI == 0 and negModeI > 0:
    mode = 'Negative'
elif negModeI == 0 and posModeI > 0:
    mode = 'Positive'
modeInt = {'Positive' : 1.0, 'Negative' : -1.0}[mode]
dfRef = pd.read_csv(args.tuneIonsFile)
dfRef = pd.DataFrame(dfRef[dfRef['Precursor Charge'] * modeInt >= 1])
print(f'...done, found {mode} mode data\n\n')

print('Scraping tune ion values...')
tas = []
for m in dfRef['Precursor m/z'].values:
    ss = deimos.locate(ms1, by=['mz'], loc=[m], tol=[args.tol], return_index=False)
    # slice by mass
    # l = m - tol
    # h = m + tol
    # ss = deimos.slice(ms1, by='mz', low = l, high = h)
    # t = ms1[(ms1['mz'] - m).abs() <= tol]
    qs = np.quantile(ss.intensity, q = [0, 0.1, 0.5, 0.7, 0.9])
    q90 = qs[-1]
    # ta = ss.loc[lambda x : x['intensity'] > q90].drift_time.mean()
    ta = np.average(ss['drift_time'], weights = ss['intensity'])
    print(m, ta)
    tas.append(ta)

print('...done')
ccs_cal = deimos.calibration.calibrate_ccs(mz = dfRef['Precursor m/z'], ccs = dfRef['CCS'], q = dfRef['Precursor Charge'], ta = tas, buffer_mass = args.bufferGasMass)
print(f'r-squared:\t{ccs_cal.fit["r"] ** 2}')
print(f"Beta - {ccs_cal.beta}")
print(f"TFix - {ccs_cal.tfix}")


override_string = f'''<?xml version="1.0" encoding="utf-8"?>
<OverrideImsCalibration>
    <FileVersion>1</FileVersion>
    <SingleFieldCcsCalibration>
        <DriftGas mass="{args.bufferGasMass}">N2</DriftGas>
        <TFix>{ccs_cal.tfix}</TFix>
        <Beta>{ccs_cal.beta}</Beta>
    </SingleFieldCcsCalibration>
</OverrideImsCalibration>'''

with open(os.path.join(args.outDir, "AcqData", 'OverrideImsCal.xml'), 'w') as f:
    print(override_string, file = f)
