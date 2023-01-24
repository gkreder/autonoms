#!/bin/bash

parentdir="$(dirname "$1")"
basename="$(basename "$1")"

cmd="docker run --rm -e WINEDEBUG=-all -v $parentdir:/data chambm/pwiz-skyline-i-agree-to-the-vendor-licenses wine msconvert /data/$basename"
echo $cmd
$cmd

# hello world