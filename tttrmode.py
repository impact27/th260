#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo for access to TimeHarp 260 Hardware via TH260LIB.DLL v 3.1.
The program performs a measurement based on hard coded settings.
The resulting data is stored in a binary output file.

Based on tttrmode.py; Keno Goertz, PicoQuant GmbH, February 2018

Created on Jul 2019

@author: Quentin Peter
"""

import th260

settings = dict(
    # Measurement parameters, these are hardcoded since this is just a demo
    # set T2 or T3 here, observe suitable Syncdivider and Range!
    mode = 2,
    binning = 0,  # you can change this, meaningful only in T3 mode
    offset = 0,  # you can change this, meaningful only in T3 mode
    syncDivider = 1,  # you can change this, observe mode! READ MANUAL!
    # For TimeHarp 260 P
    syncCFDZeroCross = -10,  # you can change this (in mV)
    syncCFDLevel = -50,  # you can change this (in mV)
    inputCFDZeroCross = -10,  # you can change this (in mV)
    inputCFDLevel = -50,  # you can change this (in mV)
    # For TimeHarp 260 N
    syncTriggerEdge = 0,  # you can change this
    syncTriggerLevel = -50,  # you can change this
    inputTriggerEdge = 0,  # you can change this
    inputTriggerLevel = -50,  # you can change this
)

tacq = 10000  # Measurement time in millisec, you can change this
outputfilename = "tttrmode.ptu"


print("\nSearching for TimeHarp devices...")
print("Devidx     Status")

# Get first device
dev = th260.get_avilable_devices()

for i in range(0, th260.MAXDEVNUM):
    if i in dev:
        print("  %1d        S/N %s" % (i, dev[i]))
    else:
        print("  %1d        no device" % i)

# In this demo we will use the first TimeHarp device we find, i.e. dev.keys[0].
# You can also use multiple devices in parallel.
# You can also check for specific serial numbers, so that you always know
# which physical device you are talking to.
if len(dev) < 1:
    raise RuntimeError("No device available.")

print("Using device #%1d" % list(dev.keys())[0])
print("\nInitializing the device...")

device = th260.TH260(serial_number=dev[list(dev.keys())[0]])

# with internal clock
device.openDevice()
device.initialize(settings)

hardware_info = device.getHardwareInfo()

print("Found Model %s Part no %s Version %s" % (
    hardware_info['Model'], hardware_info["Partno"], hardware_info["Version"]))

numChannels = device.getNumOfInputChannels()
print("Device has %i input channels." % numChannels)

print("\nUsing the following settings:")
print("Mode              : %d" % device.mode)
print("Binning           : %d" % device.getBinning())
print("Offset            : %d" % device.getOffset())
print("AcquisitionTime   : %d" % tacq)
print("SyncDivider       : %d" % device.getSyncDiv())

if hardware_info['Model'] == "TimeHarp 260 P":
    level, zero = device.getSyncCFD()
    print("SyncCFDZeroCross  : %d" % zero)
    print("SyncCFDLevel      : %d" % level)
    level, zero = device.getInputCFD(0)
    print("InputCFDZeroCross : %d" % zero)
    print("InputCFDLevel     : %d" % level)
elif hardware_info['Model'] == "TimeHarp 260 N":
    level, edge = device.getSyncEdgeTrg()
    print("SyncTriggerEdge   : %d" % edge)
    print("SyncTriggerLevel  : %d" % level)
    level, edge = device.getInputEdgeTrg(0)
    print("InputTriggerEdge  : %d" % edge)
    print("InputTriggerLevel : %d" % level)
else:
    print("Unknown hardware model %s. Aborted." % hardware_info['Model'])

resolution = device.getResolution()

print("Resolution is %1.1lfps" % resolution)

print("\nMeasuring input rates...")

syncRate = device.getSyncRate()

print("\nSyncrate=%1d/s" % syncRate)

for i in range(0, numChannels):
    countRate = device.getCountRate(i)
    print("Countrate[%1d]=%1d/s" % (i, countRate))

# after getting the count rates you can check for warnings
warnings = device.getWarnings()
if warnings:
    print("\n\n%s" % warnings)

print("\nPress RETURN to start")
input()

print(f'Starting data collection, {tacq}ms')
device.measure(tacq)
data = device.get_records()[1].time_s()
print(f'End Recording, {len(data)}')
device.save_data(outputfilename)

print("\nDone")
