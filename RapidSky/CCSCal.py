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

# print('Scraping tune ion values...')
# tas = []
# for m in dfRef['Precursor m/z'].values:
#     ss = deimos.locate(ms1, by=['mz'], loc=[m], tol=[args.tol], return_index=False)
#     # slice by mass
#     # l = m - tol
#     # h = m + tol
#     # ss = deimos.slice(ms1, by='mz', low = l, high = h)
#     # t = ms1[(ms1['mz'] - m).abs() <= tol]
#     qs = np.quantile(ss.intensity, q = [0, 0.1, 0.5, 0.7, 0.9])
#     q90 = qs[-1]
#     # ta = ss.loc[lambda x : x['intensity'] > q90].drift_time.mean()
#     ta = np.average(ss['drift_time'], weights = ss['intensity'])
#     print(m, ta)
#     tas.append(ta)

# print('...done')
# # Beta comes out negative for negative charged ions? If I flip the ccs values or the tas in negative mode I think it works...
# # ccs_cal = deimos.calibration.calibrate_ccs(mz = dfRef['Precursor m/z'], ccs = float(modeInt) * dfRef['CCS'], q = dfRef['Precursor Charge'], ta = tas, buffer_mass = args.bufferGasMass)
# ccs_cal = deimos.calibration.calibrate_ccs(mz = dfRef['Precursor m/z'], ccs = dfRef['CCS'], q = modeInt * dfRef['Precursor Charge'], ta = tas, buffer_mass = args.bufferGasMass)


# Overriding the deimos tunemix function because I'm not sure they implemented slice correctedly with the mz_tol
def tunemix(features, mz, ccs, q=[1, 1, 1, 1, 1, 1],
            buffer_mass=args.bufferGasMass, mz_tol_ppm=None,
            mz_tol_da=None, 
            dt_tol=0.04,
            power=False):
    '''
    Provided tune mix data with known calibration ions (i.e. known m/z, CCS, and nominal charge),
    determine the arrival time for each to define a CCS calibration.
    Parameters
    ----------
    mz : :obj:`~numpy.array`
        Calibration mass-to-charge ratios.
    ccs : :obj:`~numpy.array`
        Calibration collision cross sections.
    q : :obj:`~numpy.array`
        Calibration nominal charges.
    buffer_mass : float
        Mass of the buffer gas.
    mz_tol_ppm : float
        Tolerance in ppm to isolate tune ion.
    mz_tol_da : float
        Tolerance in da to isolate tune ion
    dt_tol : float
        Fractional tolerance to define drift time window bounds.
    power : bool
        Indicate whether to use linearize power function for calibration,
        i.e. in traveling wave ion moblility spectrometry.
    Returns
    -------
    :obj:`~deimos.calibration.CCSCalibration`
        Instance of calibrated `~deimos.calibration.CCSCalibration`
        object.
    '''

    # cast to numpy array
    mz = np.array(mz)
    ccs = np.array(ccs)
    q = np.array(q)

    # check lengths
    deimos.utils.check_length([mz, ccs, q])

    if (mz_tol_da == None and mz_tol_ppm == None) or (mz_tol_da != None and mz_tol_ppm != None):
        sys.exit('Error, need to supply one of mz_tol_da or mz_tol_ppm (not both)')

    # iterate tune ions
    ta = []
    for mz_i, ccs_i, q_i in zip(mz, ccs, q):
        # slice ms1
        if mz_tol_ppm != None:
            mz_add = ( mz_tol_ppm * mz_i ) / 1e6
        if mz_tol_da != None:
            mz_add = mz_tol_da
        mz_lower = mz_i - mz_add
        mz_upper = mz_i + mz_add
        subset = deimos.slice(features, by='mz',
                              low = mz_lower,
                              high = mz_upper)

        # extract dt info
        dt_profile = deimos.collapse(subset, keep='drift_time')
        dt_i = dt_profile.sort_values(by='intensity', ascending=False)[
            'drift_time'].values[0]
        dt_profile = deimos.locate(
            dt_profile, by='drift_time', loc=dt_i, tol=dt_tol * dt_i).sort_values(by='drift_time')

        # interpolate spline
        x = dt_profile['drift_time'].values
        y = dt_profile['intensity'].values

        spl = interp1d(x, y, kind='quadratic')
        newx = np.arange(x.min(), x.max(), 0.001)
        newy = spl(newx)
        dt_j = newx[np.argmax(newy)]

        ta.append(dt_j)

    # calibrate
    ta = np.array(ta)
    return deimos.calibration.calibrate_ccs(mz=mz, ta=ta, ccs=ccs, q=q, buffer_mass=buffer_mass,
                                            power=power)

# Use the built in deimos tunemix method
# ccs_cal = deimos.calibration.tunemix(ms1, mz = dfRef['Precursor m/z'], ccs = dfRef['CCS'], q = modeInt * dfRef['Precursor Charge'], buffer_mass = args.bufferGasMass) #mz_tol is in ppm?
ccs_cal = tunemix(ms1, mz = dfRef['Precursor m/z'], ccs = dfRef['CCS'], q = modeInt * dfRef['Precursor Charge'], mz_tol_da = 0.005) #mz_tol is in ppm?

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
