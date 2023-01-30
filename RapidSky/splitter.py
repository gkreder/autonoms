import sys
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--seqFile', '-i', required = True)
args = parser.parse_args()

parentDir = os.path.dirname(args.seqFile)



