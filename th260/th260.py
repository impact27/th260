#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Class for controlling a TimeHarp 260 via TH260LIB.DLL v 3.1.

Based on tttrmode.py; Keno Goertz, PicoQuant GmbH, February 2018

Created on Jul 2019

@author: Quentin Peter
"""

import time
import ctypes as ct
from ctypes import byref
import warnings
import uuid
import numpy as np
import threading

from th260 import th260definitions as thdef
from th260.tttr_result import T2Result
from th260.ptu_format import write_ptu


dll_file = "th260lib64.dll"

default_settings = dict(
    mode=2,
    binning=0,  # you can change this, meaningful only in T3 mode
    offset=0,  # you can change this, meaningful only in T3 mode
    syncDivider=1,  # you can change this, observe mode! READ MANUAL!
    syncChannelOffset=0,
    inputChannelOffset=[0],
    # For TimeHarp 260 P
    syncCFDZeroCross=-10,  # you can change this (in mV)
    syncCFDLevel=-180,  # you can change this (in mV)
    inputCFDZeroCross=[-10],  # you can change this (in mV)
    inputCFDLevel=[-180],  # you can change this (in mV)
    # For TimeHarp 260 N
    syncTriggerEdge=0,  # you can change this
    syncTriggerLevel=-50,  # you can change this
    inputTriggerEdge=[0],  # you can change this
    inputTriggerLevel=[-50],  # you can change this
)


# =============================================================================
# General Functions
# =============================================================================
class TH260lib():
    """
    Wrap dll to add a threading lock.
    """

    def __init__(self):
        # Open DLL
        self._dll = ct.CDLL(dll_file)
        self.lock = threading.RLock()

    def __getattr__(self, name):
        with self.lock:
            return getattr(self._dll, name)


th260lib = TH260lib()


def dlllock(func):
    """
    Decorator for functions.

    This is needed because it looks like the dll is not thread safe.
    """
    def wrapper(*args, **kwargs):
        with th260lib.lock:
            return func(*args, **kwargs)
    return wrapper


@dlllock
def getErrorString(retcode):
    """
    TH260_GetErrorString

    This function is provided to obtain readable error strings that explain the
    cause of the error better than the numerical error code. Use these in error
    handling message boxes, support enquiries etc.
    """
    errorString = ct.create_string_buffer(b"", thdef.MAXSTRLEN_ERRSTR)
    th260lib.TH260_GetErrorString(errorString, ct.c_int(retcode))
    return errorString.value.decode("utf-8")


@dlllock
def getLibraryVersion():
    """
    TH260_GetLibraryVersion

    Use the version information to ensure compatibility of the library with
    your own application.
    """
    libVersion = ct.create_string_buffer(b"", thdef.MAXSTRLEN_LIBVER)
    th260lib.TH260_GetLibraryVersion(libVersion)
    return libVersion.value.decode("utf-8")


# Check lib version
if getLibraryVersion() != thdef.LIB_VERSION:
    warnings.warn("Warning: The application was built for version %s"
                  % thdef.LIB_VERSION)

# =============================================================================
# Helper functions for TH260_Device
# =============================================================================


class TH260Error(RuntimeError):
    """
    An error specific for TH260.
    """
    pass


def tryfunc(retcode):
    """
    Raise an error if an error is present.
    """
    if retcode < 0:
        raise TH260Error(retcode, getErrorString(retcode))


def get_avilable_devices():
    """
    Get a list of avilable devices.
    """
    dev = {}
    for i in range(0, thdef.MAXDEVNUM):
        try:
            # Open a device and check if there is no errors
            device = TH260_API(device_number=i)
            dev[i] = device.openDevice()
            device.closeDevice()
        except TH260Error as e:
            if e.args[0] != -1:  # TH260_ERROR_DEVICE_OPEN_FAIL
                raise
    return dev

# =============================================================================
# Device Specific Functions
# =============================================================================


class TH260_API():
    def __init__(self, device_number=None):
        """
        Open the devices. Specify serial number or device number.
        """
        self._device_number = ct.c_int(device_number)

    def closeDevice(self):
        """
        TH260_CloseDevice

        Closes and releases the device for use by other programs.
        """
        tryfunc(th260lib.TH260_CloseDevice(self._device_number))

    @dlllock
    def openDevice(self):
        """
        TH260_OpenDevice

        Opens the device for use. Must be called before any of the other
        functions below can be used.
        """
        hwSerial = ct.create_string_buffer(b"", thdef.MAXSTRLEN_SERIAL)
        tryfunc(th260lib.TH260_OpenDevice(self._device_number, hwSerial))
        return hwSerial.value.decode("utf-8")

    @dlllock
    def initialize(self, mode):
        """
        TH260_Initialize

        This routine must be called before any of the other routines below can
        be used. Note that some of them depend on the measurement mode you
        select here. See the TimeHarp manual for more information on the
        measurement modes.
        """
        tryfunc(th260lib.TH260_Initialize(
            self._device_number, ct.c_int(mode)))

    # =========================================================================
    # Methods for Use on Initialized Devices
    # =========================================================================

    @dlllock
    def getHardwareInfo(self):
        """
        TH260_GetHardwareInfo
        """
        hwPartno = ct.create_string_buffer(b"", thdef.MAXSTRLEN_PART)
        hwVersion = ct.create_string_buffer(b"", thdef.MAXSTRLEN_VERSION)
        hwModel = ct.create_string_buffer(b"", thdef.MAXSTRLEN_MODEL)
        tryfunc(th260lib.TH260_GetHardwareInfo(
            self._device_number, hwModel, hwPartno, hwVersion))
        return {"Model": hwModel.value.decode("utf-8"),
                "Partno": hwPartno.value.decode("utf-8"),
                "Version": hwVersion.value.decode("utf-8")}

    @dlllock
    def getNumOfInputChannels(self):
        """
        TH260_GetNumOfInputChannels

        The number of input channels is counting only the regular detector
        channels. It does not count the sync channel. Nevertheless, it is
        possible to connect a detector also to the sync channel, e.g. in
        histogramming mode for antibunching or in T2 mode.
        """
        numChannels = ct.c_int()
        tryfunc(th260lib.TH260_GetNumOfInputChannels(
            self._device_number, byref(numChannels)))
        return numChannels.value

    def setSyncDiv(self, syncDivider):
        """
        TH260_SetSyncDiv

        The sync divider must be used to keep the effective sync rate at values
        < 40 MHz. It should only be used with sync sources of stable period.
        The readings obtained with TH260_GetCountRate are corrected for the
        divider setting and deliver the ex- ternal (undivided) rate. When the
        sync input is used for a detector signal the divider should be set to
        1.
        """
        tryfunc(th260lib.TH260_SetSyncDiv(
            self._device_number, ct.c_int(syncDivider)))
        # Note: after Init or SetSyncDiv allow 150 ms
        # for valid count rate readings
        time.sleep(thdef.INIT_WAIT_TIME)

    def setSyncCFD(self, syncCFDLevel, syncCFDZeroCross):
        """
        TH260_SetSyncCFD
        """
        tryfunc(th260lib.TH260_SetSyncCFD(
            self._device_number, ct.c_int(syncCFDLevel),
            ct.c_int(syncCFDZeroCross)))

    def setInputCFD(self, channel, inputCFDLevel, inputCFDZeroCross):
        """
        TH260_SetInputCFD

        The maximum channel index must correspond to nchannels-1 as obtained
        through TH260_GetNumOfInputChannels().
        """
        tryfunc(th260lib.TH260_SetInputCFD(
            self._device_number, ct.c_int(channel), ct.c_int(inputCFDLevel),
            ct.c_int(inputCFDZeroCross)))

    def setSyncEdgeTrg(self, syncTriggerLevel, syncTriggerEdge):
        """
        TH260_SetSyncEdgeTrg
        """
        tryfunc(th260lib.TH260_SetSyncEdgeTrg(
            self._device_number, ct.c_int(syncTriggerLevel),
            ct.c_int(syncTriggerEdge)))

    def setInputEdgeTrg(self, channel, inputTriggerLevel, inputTriggerEdge):
        """
        TH260_SetInputEdgeTrg

        The maximum channel index must correspond to nchannels-1 as obtained
        through TH260_GetNumOfInputChannels().
        """
        tryfunc(th260lib.TH260_SetInputEdgeTrg(
            self._device_number, ct.c_int(channel),
            ct.c_int(inputTriggerLevel),
            ct.c_int(inputTriggerEdge)))

    def setSyncChannelOffset(self, offset):
        """
        TH260_SetSyncChannelOffset
        """
        tryfunc(th260lib.TH260_SetSyncChannelOffset(
            self._device_number, ct.c_int(offset)))

    def setInputChannelOffset(self, channel, offset):
        """
        TH260_SetInputChannelOffset

        The maximum channel index must correspond to nchannels-1 as obtained
        through TH260_GetNumOfInputChannels().
        """
        tryfunc(th260lib.TH260_SetInputChannelOffset(
            self._device_number, ct.c_int(channel), ct.c_int(offset)))

    def setBinning(self, binning):
        """
        TH260_SetBinning

        binning corresponds to repeated multiplication of the base resolution
        by 2 as follows:
            0 = 1x base resolution,
            1 = 2x base resolution,
            2 = 4x base resolution,
            3 = 8x base resolution, and so on.
        """
        tryfunc(th260lib.TH260_SetBinning(
                self._device_number, ct.c_int(binning)))

    def setOffset(self, offset):
        """
        TH260_SetOffset

        The offset programmed here is fundamentally different from the input
        offsets. It applies only after the time difference of input channel
        and sync has been calculated. It can be used to move arge stop-start
        differences into the histogram range that would normally not be
        recorded. It is only meaningful in histogramming and T3 mode.
        """
        tryfunc(th260lib.TH260_SetOffset(
                self._device_number, ct.c_int(offset)))

    @dlllock
    def getResolution(self):
        """
        TH260_GetResolution

        This is meaningful only in histogramming and T3 mode. T2 mode always
        runs at the boards's base resolution.
        """
        resolution = ct.c_double()
        tryfunc(th260lib.TH260_GetResolution(
                self._device_number, byref(resolution)))
        return resolution.value

    @dlllock
    def getBaseResolution(self):
        """
        TH260_GetBaseResolution

        The value returned in binsteps is the maximum value allowed for the
        TH260_SetBinning function.
        """
        resolution = ct.c_double()
        binsteps = ct.c_int()
        tryfunc(th260lib.TH260_GetBaseResolution(
                self._device_number, byref(resolution), byref(binsteps)))
        return resolution.value

    @dlllock
    def getSyncRate(self):
        """
        TH260_GetSyncRate

        This is used to get the pulse rate at the sync input. The result is
        internally corrected for the current sync divider setting. Allow at
        least 100 ms after TH260_Initialize or TH260_SetSyncDivider to get a
        stable rate reading. Similarly, wait at least 100 ms to get a new
        reading. This is the gate time of the hardware counters.
        """
        syncRate = ct.c_int()
        tryfunc(th260lib.TH260_GetSyncRate(
            self._device_number, byref(syncRate)))
        return syncRate.value

    @dlllock
    def getCountRate(self, channel):
        """
        TH260_GetCountRate

        Allow at least 100 ms after TH260_Initialize to get a stable rate
        reading. Similarly, wait at least 100 ms to get a new reading. This is
        the gate time of the hardware counters. The maximum channel index must
        correspond to nchannels-1 as obtained through
        TH260_GetNumOfInputChannels().
        """
        countRate = ct.c_int()
        tryfunc(th260lib.TH260_GetCountRate(
            self._device_number, ct.c_int(channel), byref(countRate)))
        return countRate.value

    @dlllock
    def getWarnings(self):
        """
        TH260_GetWarnings

        You must call TH260_GetCoutRate and TH260_GetCoutRate for all channels
        prior to this call.
        """
        warnings = ct.c_int()
        tryfunc(th260lib.TH260_GetWarnings(
            self._device_number, byref(warnings)))
        return warnings.value

    @dlllock
    def getWarningsText(self, warnings):
        """
        TH260_GetWarningsText

        This helps to identify suspicious measurement conditions that may be
        due to inappropriate settings.
        """
        warnings = ct.c_int(warnings)
        warningstext = ct.create_string_buffer(b"", thdef.MAXSTRLEN_WRNTXT)
        if warnings.value != 0:
            tryfunc(th260lib.TH260_GetWarningsText(
                self._device_number, warningstext, warnings))
            return warningstext.value.decode("utf-8")
        return ''

# =============================================================================
#  Measurment
# =============================================================================

    @dlllock
    def readFiFo(self):
        """
        TH260_ReadFiFo

        CPU time during wait for completion will be yielded to other processes
        / threads. The call will return after a timeout period of a few ms if
        no more data could be fetched. The buffer must not be accessed until
        the call returns.
        New in v 3.1: Note that the buffer must be aligned on a 4096-byte
        boundary in order to allow efficient DMA transfers. If the buffer does
        not meet this requirement the library will use an internal buffer and
        copy the data. This slows down data throughput.
        """
        flags = ct.c_int()
        tryfunc(th260lib.TH260_GetFlags(self._device_number, byref(flags)))

        if flags.value & thdef.FLAG_FIFOFULL > 0:
            raise TH260Error(0, "FiFo Overrun!")

        buffer = (ct.c_uint * thdef.TTREADMAX)()
        nRecords = ct.c_int()
        try:
            tryfunc(th260lib.TH260_ReadFiFo(
                self._device_number, byref(buffer), thdef.TTREADMAX,
                byref(nRecords)))
        except TH260Error:
            raise

        if nRecords.value > 0:
            # Cut the buffer at the right size and wrap it in a numpy array
            # so we can avoid working with ctypes objects
            return np.array((ct.c_uint * nRecords.value).from_address(
                        ct.addressof(buffer)))
        return np.zeros(0, dtype=ct.c_uint)

    @dlllock
    def CTCStatus(self):
        """
        TH260_CTCStatus

        This routine should be called to determine if the acuisition time
        has expired.
        """
        ctcstatus = ct.c_int()
        tryfunc(th260lib.TH260_CTCStatus(
            self._device_number, byref(ctcstatus)))
        return ctcstatus.value

    def startMeas(self, tacq):
        """
        TH260_StartMeas

        tacq: Measurement time in millisec

        This starts a measurement in the current measurement mode. Should be
        called after all settings are done. Previous measurements should be
        stopped before calling this routine again.
        """
        # send start signal
        tryfunc(th260lib.TH260_StartMeas(
            self._device_number, ct.c_int(tacq)))

    def stopMeas(self):
        """
        TH260_StopMeas

        This must be called after the acquisition time is expired.
        Can also be used to force stop before the acquisition time expires.
        """
        tryfunc(th260lib.TH260_StopMeas(self._device_number))


class TH260():
    """
    Class to add higher level capabilities to the TH260 API.
    """

    def __init__(self, serial_number=None):
        """
        Open the devices. Specify serial number or device number.
        """
        self._keep_buffer = True

        self.__running = False
        self._measure_thread = None
        self._acquisition_time = None
        self._local_buffer = []
        self.records = None

        self._serial = serial_number
        self._api = None
        devices = get_avilable_devices()
        for device_number in devices:
            if devices[device_number] == serial_number:
                self._api = TH260_API(device_number)
                break
        if self._api is None:
            raise RuntimeError(
                f"Couldn't find serial number {serial_number}")

        self._settings = default_settings

    @property
    def mode(self):
        """
        Get current mode.
        """
        return self._settings['mode']

    @property
    def settings(self):
        """
        Get settings.
        """
        return self._settings

    @property
    def serial(self):
        """
        Get the serial number.
        """
        return self._serial

    def closeDevice(self):
        """
        Close connection to the device.

        Closes and releases the device for use by other programs.
        """
        self._api.closeDevice()

    def openDevice(self):
        """
        Open connection to the device.

        Opens the device for use. Must be called before any of the other
        functions below can be used.
        """
        serial = self._api.openDevice()
        if self._serial is None:
            self._serial = serial
        elif self._serial != serial:
            raise RuntimeError('Incorrect serial.')

    @dlllock
    def initialize(self, settings=None):
        """
        initialize the device with the settings.

        This routine must be called before any of the other routines below can
        be used. Note that some of them depend on the measurement mode you
        select here. See the TimeHarp manual for more information on the
        measurement modes.
        """
        # Read any settings that are applied
        if settings is not None:
            for key in settings:
                if key in self._settings:
                    self._settings[key] = settings[key]

        mode = self._settings['mode']
        assert mode in [thdef.MODE_T2, thdef.MODE_T3]
        self._api.initialize(self._settings['mode'])

        hardware_info = self.getHardwareInfo()
        numChannels = self.getNumOfInputChannels()

        # Transform length one arrays into a numChannels array
        for key in [
                'inputCFDZeroCross',
                'inputCFDLevel',
                'inputTriggerLevel',
                'inputTriggerEdge',
                'inputChannelOffset']:
            if not isinstance(self._settings[key], list):
                self._settings[key] = [self._settings[key]]
            if len(self._settings[key]) == 1:
                self._settings[key] *= numChannels

        self.setSyncDiv(self._settings['syncDivider'])

        if hardware_info['Model'] == "TimeHarp 260 P":
            self.setSyncCFD(
                self._settings['syncCFDLevel'],
                self._settings['syncCFDZeroCross'])

            # we use the same input self._settings for all channels
            for i in range(numChannels):
                self.setInputCFD(
                    i,
                    self._settings['inputCFDLevel'][i],
                    self._settings['inputCFDZeroCross'][i])

        if hardware_info['Model'] == "TimeHarp 260 N":
            self.setSyncEdgeTrg(
                self._settings['syncTriggerLevel'],
                self._settings['syncTriggerEdge'])
            # we use the same input self._settings for all channels
            for i in range(numChannels):
                self.SetInputEdgeTrg(
                    i,
                    self._settings['inputTriggerLevel'][i],
                    self._settings['inputTriggerEdge'][i])

        self.setSyncChannelOffset(self._settings['syncChannelOffset'])

        for i in range(numChannels):
            self.setInputChannelOffset(
                i, self._settings['inputChannelOffset'][i])

        self.setBinning(self._settings['binning'])
        self.setOffset(self._settings['offset'])

        time.sleep(thdef.INIT_WAIT_TIME)

    def getHardwareInfo(self):
        """
        Get Hardware Info.
        """
        return self._api.getHardwareInfo()

    def getNumOfInputChannels(self):
        """
        Get number of input Channels.

        The number of input channels is counting only the regular detector
        channels. It does not count the sync channel. Nevertheless, it is
        possible to connect a detector also to the sync channel, e.g. in
        histogramming mode for antibunching or in T2 mode.
        """
        return self._api.getNumOfInputChannels()

    def setSyncDiv(self, syncDivider):
        """
        set sync divider

        The sync divider must be used to keep the effective sync rate at values
        < 40 MHz. It should only be used with sync sources of stable period.
        The readings obtained with TH260_GetCountRate are corrected for the
        divider setting and deliver the ex- ternal (undivided) rate. When the
        sync input is used for a detector signal the divider should be set to
        1.
        """
        self._settings['syncDivider'] = syncDivider
        self._api.setSyncDiv(syncDivider)

    def getSyncDiv(self):
        """
        getSyncDiv
        """
        return self._settings['syncDivider']

    def setSyncCFD(self, syncCFDLevel, syncCFDZeroCross):
        """
        TSet Sync CFD
        """
        self._settings['syncCFDLevel'] = syncCFDLevel
        self._settings['syncCFDZeroCross'] = syncCFDZeroCross
        self._api.setSyncCFD(syncCFDLevel, syncCFDZeroCross)

    def getSyncCFD(self):
        """
        getSyncCFD
        """
        return (self._settings['syncCFDLevel'],
                self._settings['syncCFDZeroCross'])

    def setInputCFD(self, channel, inputCFDLevel, inputCFDZeroCross):
        """
        TH260_SetInputCFD

        The maximum channel index must correspond to nchannels-1 as obtained
        through TH260_GetNumOfInputChannels().
        """
        self._settings['inputCFDLevel'][channel] = inputCFDLevel
        self._settings['inputCFDZeroCross'][channel] = inputCFDZeroCross
        self._api.setInputCFD(channel, inputCFDLevel, inputCFDZeroCross)

    def getInputCFD(self, channel):
        """
        getInputCFD
        """
        return (self._settings['inputCFDLevel'][channel],
                self._settings['inputCFDZeroCross'][channel])

    def setSyncEdgeTrg(self, syncTriggerLevel, syncTriggerEdge):
        """
        TH260_SetSyncEdgeTrg
        """
        self._settings['syncTriggerLevel'] = syncTriggerLevel
        self._settings['syncTriggerEdge'] = syncTriggerEdge
        self._api.setSyncEdgeTrg(syncTriggerLevel, syncTriggerEdge)

    def getSyncEdgeTrg(self):
        """
        getSyncEdgeTrg
        """
        return (self._settings['syncTriggerLevel'],
                self._settings['syncTriggerEdge'])

    def setInputEdgeTrg(self, channel, inputTriggerLevel, inputTriggerEdge):
        """
        SetInputEdgeTrg

        The maximum channel index must correspond to nchannels-1 as obtained
        through TH260_GetNumOfInputChannels().
        """
        self._settings['inputTriggerLevel'][channel] = inputTriggerLevel
        self._settings['inputTriggerEdge'][channel] = inputTriggerEdge
        self._api.setInputEdgeTrg(channel, inputTriggerLevel, inputTriggerEdge)

    def getInputEdgeTrg(self, channel):
        """
        getInputEdgeTrg
        """
        return (self._settings['inputTriggerLevel'][channel],
                self._settings['inputTriggerEdge'][channel])

    def setSyncChannelOffset(self, offset):
        """
        SetSyncChannelOffset
        """
        self._settings['syncChannelOffset'] = offset
        self._api.setSyncChannelOffset(offset)

    def getSyncChannelOffset(self):
        """
        getSyncChannelOffset
        """
        return self._settings['syncChannelOffset']

    def setInputChannelOffset(self, channel, offset):
        """
        SetInputChannelOffset

        The maximum channel index must correspond to nchannels-1 as obtained
        through TH260_GetNumOfInputChannels().
        """
        self._settings['inputChannelOffset'][channel] = offset
        self._api.setInputChannelOffset(channel, offset)

    def getInputChannelOffset(self, channel):
        """
        getInputChannelOffset
        """
        return self._settings['inputChannelOffset'][channel]

    def setBinning(self, binning):
        """
        SetBinning

        binning corresponds to repeated multiplication of the base resolution
        by 2 as follows:
            0 = 1x base resolution,
            1 = 2x base resolution,
            2 = 4x base resolution,
            3 = 8x base resolution, and so on.
        """
        self._settings['binning'] = binning
        self._api.setBinning(binning)

    def getBinning(self):
        """
        getBinning
        """
        return self._settings['binning']

    def setOffset(self, offset):
        """
        SetOffset

        The offset programmed here is fundamentally different from the input
        offsets. It applies only after the time difference of input channel
        and sync has been calculated. It can be used to move arge stop-start
        differences into the histogram range that would normally not be
        recorded. It is only meaningful in histogramming and T3 mode.
        """
        self._settings['offset'] = offset
        self._api.setOffset(offset)

    def getOffset(self):
        """
        getOffset
        """
        return self._settings['offset']

    def getResolution(self):
        """
        TH260_GetResolution

        This is meaningful only in histogramming and T3 mode. T2 mode always
        runs at the boards's base resolution.
        """
        return self._api.getResolution()

    def getBaseResolution(self):
        """
        TH260_GetBaseResolution

        The value returned in binsteps is the maximum value allowed for the
        TH260_SetBinning function.
        """
        return self._api.getBaseResolution()

    def getSyncRate(self):
        """
        TH260_GetSyncRate

        This is used to get the pulse rate at the sync input. The result is
        internally corrected for the current sync divider setting. Allow at
        least 100 ms after TH260_Initialize or TH260_SetSyncDivider to get a
        stable rate reading. Similarly, wait at least 100 ms to get a new
        reading. This is the gate time of the hardware counters.
        """
        return self._api.getSyncRate()

    def getCountRate(self, channel):
        """
        TH260_GetCountRate

        Allow at least 100 ms after TH260_Initialize to get a stable rate
        reading. Similarly, wait at least 100 ms to get a new reading. This is
        the gate time of the hardware counters. The maximum channel index must
        correspond to nchannels-1 as obtained through
        TH260_GetNumOfInputChannels().
        """
        return self._api.getCountRate(channel)

    def getWarnings(self):
        """
        TH260_GetWarnings

        You must call TH260_GetCoutRate and TH260_GetCoutRate for all channels
        prior to this call.

        This helps to identify suspicious measurement conditions that may be
        due to inappropriate settings.
        """
        warnings = self._api.getWarnings()
        return self._api.getWarningsText(warnings)

# =============================================================================
#  Measurment interface
# =============================================================================

    def _fill_buffer(self):
        """
        Fill measurment buffer.
        """
        # Empty local buffer
        try:
            while self.is_running():
                # Get Buffer
                try:
                    buffer = self._api.readFiFo()
                except TH260Error as e:
                    if e.args[1] == "FiFo Overrun!":
                        self.stop_measure(thdef.STOPREASON_FIFO_OVERRUN)
                # Save Buffer
                if len(buffer) > 0:
                    self._local_buffer.append(buffer)
                else:
                    # Check for timeover
                    ctcstatus = self._api.CTCStatus()
                    if ctcstatus > 0:
                        self.stop_measure(thdef.STOPREASON_TIMEOVER)
                        return
        except TH260Error:
            self.stop_measure(thdef.STOPREASON_ERROR)

    def measure(self, time_acquisition=None, blocking=True,
                bin_time=None, only_bin=False, keep_buffer=True,
                channels=None):
        """
        Start a measurment and generates the buffers.
        """

        if time_acquisition is None:
            time_acquisition = thdef.ACQTMAX
        self._acquisition_time = time_acquisition
        self._keep_buffer = keep_buffer

        # Reset buffers and records
        self._local_buffer = []
        if channels is None:
            channels = [1]
        if self.mode == 2:
            self._records = {i: T2Result(
                channel=i,
                global_resolution=self.getBaseResolution(),
                bin_time=bin_time,
                only_bin=only_bin,
                ) for i in channels}
        else:
            raise NotImplementedError
        self._records_read_position = 0

        self.__running = True
        self._stop_reason = None

        self._api.startMeas(int(self._acquisition_time))
        self._measure_thread = threading.Thread(target=self._fill_buffer)
        self._measure_thread.start()
        if blocking:
            self.wait_end_measure()

    def stop_measure(self, reason=thdef.STOPREASON_MANUAL):
        """
        Stop measurment.
        """
        self.__running = False
        self._stop_reason = reason
        self._api.stopMeas()

    def is_running(self):
        """
        Check if measurment is running.
        """
        return self.__running

    def wait_end_measure(self):
        """
        Wait for the end of measurment.
        """
        if self.__running:
            self._measure_thread.join()

    def get_metadata(self, ndata, extra_metadata=None):
        '''
        Returns a tag list.
        '''
        # Stop reason
        stop_reason = self._stop_reason
        if stop_reason is None:
            stop_reason = thdef.STOPREASON_MANUAL

        # Acquisition time
        tacq = int(self._acquisition_time)

        hardware_info = self.getHardwareInfo()
        tags = {
            # Mendatory fileds
            'File_GUID': str(uuid.uuid4()),
            'Measurement_Mode': self.mode,
            'Measurement_SubMode': thdef.SUBMODE_OSC,
            # Need to adjust units
            'MeasDesc_GlobalResolution': self.getBaseResolution() * 1e-12,
            'MeasDesc_Resolution': self.getResolution() * 1e-12,
            'TTResult_SyncRate': self.getSyncRate(),
            'TTResult_NumberOfRecords': ndata,
            'TTResultFormat_TTTRRecType':  thdef.record_formats_code[
                (hardware_info['Model'], self.mode)],
            'TTResultFormat_BitsPerRecord': thdef.BITSLEN_RECORD,
            # Extra filelds
            'CreatorSW_Name': thdef.SOFTWARE_NAME,
            'CreatorSW_Version': thdef.SOFTWARE_VERSION,
            'CreatorSW_ContentVersion': thdef.CONTENT_VERSION,
            'MeasDesc_AcquisitionTime': tacq,
            'MeasDesc_StopOnOvfl': stop_reason == thdef.STOPREASON_OVERFLOW,
            'MeasDesc_Restart': False,
            'TTResult_StopReason': stop_reason,
            # Settings
            'MeasDesc_BinningFactor': self.getBinning(),
            'MeasDesc_Offset': self.getOffset(),
            'HWSync_Divider': self.getSyncDiv(),
            'HWSync_Offset': self.getSyncChannelOffset(),
            # Compatibility with th software
            'File_AssuredContent': 'TimeHarp 260: HWSETG SWSETG',
            'MeasDesc_StopAt': 0xffffffff,

        }

        if extra_metadata is not None:
            tags['File_Comment'] = extra_metadata

        numChannels = self.getNumOfInputChannels()

        for i in range(numChannels):
            tags['HWInputChan_Offset'] = self.getInputChannelOffset(i)

        # For TimeHarp 260 P
        if hardware_info['Model'] == "TimeHarp 260 P":
            level, zeros = self.getSyncCFD()
            tags['HWSync_CFDZeroCross'] = zeros
            tags['HWSync_CFDLevel'] = level

            for i in range(numChannels):
                level, zeros = self.getInputCFD(i)
                tags[('HWInputChan_CFDZeroCross', i)] = zeros
                tags[('HWInputChan_CFDLevel', i)] = level

        # For TimeHarp 260 N
        if hardware_info['Model'] == "TimeHarp 260 N":
            level, edge = self.getSyncEdgeTrg()
            tags['HWSync_TrgEdge'] = edge
            tags['HWSync_TrgLevel'] = level

            for i in range(numChannels):
                level, edge = self.getInputEdgeTrg(i)
                tags[('HWInpChan_TrgEdge', i)] = edge
                tags[('HWInpChan_TrgLevel', i)] = level
        return tags

    def get_records(self):
        """
        Get the records in a usable format.
        """
        # If we don't have a valid read position, return last good record

        buffer_len = len(self._local_buffer)
        if self._records_read_position == buffer_len:
            return self._records

        buffer_slice = slice(self._records_read_position, buffer_len)
        buffer = np.concatenate(self._local_buffer[buffer_slice])
        for channel in self._records:
            self._records[channel].add_buffer(buffer)

        # Empty buffer if needed
        if self._keep_buffer:
            self._records_read_position = buffer_len
        else:
            del self._local_buffer[buffer_slice]
            self._records_read_position = 0

        return self._records

    def save_data(self, outputfilename, metadata=None):
        """
        Save the data in a ptu file
        """
        if not self._keep_buffer:
            raise RuntimeError('The data was not kept.')
        # Current data
        if len(self._local_buffer) == 0:
            raise RuntimeError('Nothing to save!')
        data = np.concatenate(self._local_buffer)
        tags = self.get_metadata(len(data), metadata)

        write_ptu(outputfilename, data, tags)

        return len(data)
