################################################################################################
# gk@reder.io
################################################################################################
import sys
import argparse
import deimos
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
################################################################################################

################################################################################################
# Overriding the deimos tunemix function because I'm not sure about the deimos tunemix slice implementation with the mz_tol
def tunemix(features, mz, ccs, q=[1, 1, 1, 1, 1, 1],
            buffer_mass=28.006148, 
            mz_tol_ppm=None,
            mz_tol_da=None, 
            dt_tol=0.04,
            power=False):
    """Note - this is a slightly modified copy of the Deimos tunemix function. Provided tune mix data with known calibration ions (i.e. known m/z, CCS, and nominal charge),
    determine the arrival time for each to define a CCS calibration.

    :param mz: Calibration mass-to-charge ratios.
    :type mz: `numpy.array`
    :param ccs: Calibration collision cross sections.
    :type ccs: `numpy.array`
    :param q: Calibration nominal charges, defaults to [1, 1, 1, 1, 1, 1].
    :type q: `numpy.array`, optional
    :param buffer_mass: Mass of the buffer gas, defaults to 28.006148, .
    :type buffer_mass: float, optional
    :param mz_tol_ppm: Tolerance in ppm to isolate tune ion. Exactly one of mz_tol_ppm or mz_tol_da should be supplied (not both), defaults to None.
    :type mz_tol_ppm: float, optional
    :param mz_tol_da: Tolerance in da to isolate tune ion. Exactly one of mz_tol_ppm or mz_tol_da should be supplied (not both), defaults to None.
    :type mz_tol_da: float, optional
    :param dt_tol: Fractional tolerance to define drift time window bounds, defaults to 0.04.
    :type dt_tol: float, optional
    :param power: Indicate whether to use linearize power function for calibration i.e. in traveling wave ion moblility spectrometry, defaults to False.
    :type power: bool, optional
    :return: A calibrated deimos CCSCalibration instance
    :rtype: `deimos.calibration.CCSCalibration`
    """
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
        subset = deimos.slice(features, by='mz', low = mz_lower, high = mz_upper)
        # extract dt info
        dt_profile = deimos.collapse(subset, keep='drift_time')
        dt_i = dt_profile.sort_values(by='intensity', ascending=False)['drift_time'].values[0]
        dt_profile = deimos.locate(dt_profile, by='drift_time', loc=dt_i, tol=dt_tol * dt_i).sort_values(by='drift_time')
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
    cal_out = deimos.calibration.calibrate_ccs(mz=mz, ta=ta, ccs=ccs, q=q, buffer_mass=buffer_mass,power=power)
    return(cal_out)

def ccs_cal(inMZML, tuneIonsFile, mz_tol_ppm = 10, bufferGasMass = 28.006148):
    """Calculates CCS calibration coefficients (single field) from an mzML file assumed to contain standard ions

    :param inMZML: Path to .mzML file containing standards run
    :type inMZML: str
    :param tuneIonsFile: Path to .csv file containing standards' m/z values and CCS values
    :param mz_tol_ppm: Tolerance (in da) for finding matching ions in data to expected standards, defaults to 10
    :type mz_tol_ppm: float, optional
    :param bufferGasMass: Buffer gas mass to use in CCS calculation (default value of 28.006148 for N2 gas), defaults to 28.006148
    :type bufferGasMass: float, optional
    :return: XML string content of CCS calibration file containing calibration coefficients
    :rtype: str
    """

    print('Loading data...')
    data = deimos.load(inMZML, accession={'retention_time': 'MS:1000016', 'drift_time': 'MS:1002476', 'Positive Scan' : "MS:1000130", 'Negative Scan' : 'MS:1000129'})
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
    dfRef = pd.read_csv(tuneIonsFile)
    dfRef = pd.DataFrame(dfRef[dfRef['Precursor Charge'] * modeInt >= 1])
    print(f'...done, found {mode} mode data\n\n')

    # Using the built in deimos tunemix method
    # ccs_cal = deimos.calibration.tunemix(ms1, mz = dfRef['Precursor m/z'], ccs = dfRef['CCS'], q = modeInt * dfRef['Precursor Charge'], buffer_mass = bufferGasMass) #mz_tol is in ppm?
    ccs_cal = tunemix(ms1, mz = dfRef['Precursor m/z'], ccs = dfRef['CCS'], q = modeInt * dfRef['Precursor Charge'], mz_tol_ppm = mz_tol_ppm) 

    print(f'r-squared:\t{ccs_cal.fit["r"] ** 2}')
    print(f"Beta - {ccs_cal.beta}")
    print(f"TFix - {ccs_cal.tfix}")

    override_string = f'''<?xml version="1.0" encoding="utf-8"?>
    <OverrideImsCalibration>
        <FileVersion>1</FileVersion>
        <SingleFieldCcsCalibration>
            <DriftGas mass="{bufferGasMass}">N2</DriftGas>
            <TFix>{ccs_cal.tfix}</TFix>
            <Beta>{ccs_cal.beta}</Beta>
        </SingleFieldCcsCalibration>
    </OverrideImsCalibration>'''
    return(override_string)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inMZML', required = True)
    parser.add_argument('-t', '--tuneIonsFile', required = True)
    parser.add_argument('-o', '--outDir', required = True)
    parser.add_argument('--mz_tol_ppm', default = 10)
    parser.add_argument('--bufferGasMass', default = 28.006148)
    # 28.006148 - AutoCCS N2
    # 28.013 - Deimos N2
    # default_tol = 0.01
    # default_buffer_gas_mass = 28.006148
    args = parser.parse_args()
    override_string = ccs_cal(args.inMZML, args.tuneIonsFile, mz_tol_ppm = args.mz_tol_ppm, bufferGasMass = args.bufferGasMass)
    