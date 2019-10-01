#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Definitions for TH260Lib programming library for TimeHarp 260

Based on th260defin.h; Ver. 3.1.0.2; PicoQuant GmbH, May 2017

Created on Jul 2019

@author: Quentin Peter
"""


type_code = {
    'Empty8': 0xFFFF0008,
    'Bool8': 0x00000008,
    'Int8': 0x10000008,
    'BitSet64': 0x11000008,
    'Color8': 0x12000008,
    'Float8': 0x20000008,
    'TDateTime': 0x21000008,
    'Float8Array': 0x2001FFFF,
    'ASCII-String': 0x4001FFFF,
    'Wide-String': 0x4002FFFF,
    'BinaryBlob': 0xFFFFFFFF
       }

record_formats_code = {
 ('PicoHarp', 3): 0x00010303,
 ('PicoHarp', 2): 0x00010203,
 ('HydraHarp V1.x', 3): 0x00010304,
 ('HydraHarp V1.x', 2): 0x00010204,
 ('HydraHarp V2.x', 3): 0x01010304,
 ('HydraHarp V2.x', 2): 0x01010204,
 ('TimeHarp 260 N', 2): 0x00010205,
 ('TimeHarp 260 N', 3): 0x00010305,
 ('TimeHarp 260 P', 2): 0x00010206,
 ('TimeHarp 260 P', 3): 0x00010306,
 ('MultiHarp', 2): 0x00010207,
 ('MultiHarp', 3): 0x00010307,
 ('LIN Camera', 3): 0x00010300,
 }


tag_types = {
    # Mendatory fileds
    'File_GUID': 'ASCII-String',
    'Measurement_Mode': 'Int8',
    'Measurement_SubMode': 'Int8',
    'MeasDesc_GlobalResolution': 'Float8',
    'MeasDesc_Resolution': 'Float8',
    'TTResult_SyncRate': 'Int8',
    'TTResult_NumberOfRecords': 'Int8',
    'TTResultFormat_TTTRRecType': 'Int8',
    'TTResultFormat_BitsPerRecord': 'Int8',
    # Extra filelds
    'CreatorSW_Name': 'ASCII-String',
    'CreatorSW_Version': 'ASCII-String',
    'CreatorSW_ContentVersion': 'ASCII-String',
    'MeasDesc_AcquisitionTime': 'Int8',
    'File_AssuredContent': 'ASCII-String',
    'MeasDesc_StopAt': 'Int8',
    'MeasDesc_StopOnOvfl': 'Bool8',
    'MeasDesc_Restart': 'Bool8',
    'TTResult_StopReason': 'Int8',
    'TTResult_InputRate': 'Int8',
    'File_Comment': 'ASCII-String',
    # Settings
    'MeasDesc_BinningFactor': 'Int8',
    'MeasDesc_Offset': 'Int8',
    'HWSync_Divider': 'Int8',
    'HWSync_Offset': 'Int8',
    'HWInputChan_Offset': 'Int8',
    # For TimeHarp 260 P
    'HWSync_CFDZeroCross': 'Int8',
    'HWSync_CFDLevel': 'Int8',
    'HWInputChan_CFDZeroCross': 'Int8',
    'HWInputChan_CFDLevel': 'Int8',
    # For TimeHarp 260 N
    'HWSync_TrgEdge': 'Int8',
    'HWSync_TrgLevel': 'Int8',
    'HWInpChan_TrgEdge': 'Int8',
    'HWInpChan_TrgLevel': 'Int8',

    # End header

    'Header_End': 'Empty8',

    }

LIB_VERSION = "3.1"

MAXSTRLEN_LIBVER = 8  # max string length of *version in TH260_GetLibraryVersion
MAXSTRLEN_ERRSTR = 40  # max string length of *errstring in TH260_GetErrorString
MAXSTRLEN_SERIAL = 8  # max string length of *serial in TH260_OpenDevice and TH260_GetSerialNumber
MAXSTRLEN_MODEL = 16  # max string length of *model in TH260_GetHardwareInfo
MAXSTRLEN_PART = 8  # max string length of *partno in TH260_GetHardwareInfo
MAXSTRLEN_VERSION = 16  # max string length of *version in TH260_GetHardwareInfo
MAXSTRLEN_WRNTXT = 16384  # max string length of *text in TH260_GetWarningsText

HWIDENT_PICO = "TimeHarp 260 P"  # as returned by TH260_GetHardwareInfo
HWIDENT_NANO = "TimeHarp 260 N"  # as returned by TH260_GetHardwareInfo

MAXDEVNUM = 4  # max number of TH260 devices

MAXINPCHAN = 2  # max number of detector input channels

MAXBINSTEPS = 22  # get actual number via TH260_GetBaseResolution() !

MAXHISTLEN = 32768  # max number of histogram bins
MAXLENCODE = 5  # max length code histo mode

TTREADMAX = 131072  # 128K event records can be read in one chunk
TTREADMIN = 128     # 128 records = minimum buffer size that must be provided

MODE_HIST = 0  # for TH260_Initialize
MODE_T2 = 2
MODE_T3 = 3

MEASCTRL_SINGLESHOT_CTC = 0  # for TH260_SetMeasControl, 0=default
MEASCTRL_C1_GATE = 1
MEASCTRL_C1_START_CTC_STOP = 2
MEASCTRL_C1_START_C2_STOP = 3

EDGE_RISING = 1  # for TH260_SetXxxEdgeTrg, TH260_SetMeasControl and TH260_SetMarkerEdges
EDGE_FALLING = 0

TIMINGMODE_HIRES = 0  # used by TH260_SetTimingMode
TIMINGMODE_LORES = 1  # used by TH260_SetTimingMode

FEATURE_DLL = 0x0001  # DLL License available
FEATURE_TTTR = 0x0002  # TTTR mode available
FEATURE_MARKERS = 0x0004  # Markers available
FEATURE_LOWRES = 0x0008  # Long range mode available
FEATURE_TRIGOUT = 0x0010  # Trigger output available
FEATURE_PROG_TD = 0x0020  # Programmable deadtime available

FLAG_OVERFLOW = 0x0001  # histo mode only
FLAG_FIFOFULL = 0x0002
FLAG_SYNC_LOST = 0x0004  # T3 mode only
FLAG_EVTS_DROPPED = 0x0008  # dropped events due to high input rate
FLAG_SYSERROR = 0x0010  # hardware error, must contact support
FLAG_SOFTERROR = 0x0020  # software error, must contact support

SYNCDIVMIN = 1  # for TH260_SetSyncDiv
SYNCDIVMAX = 8

TRGLVLMIN = -1200  # mV  TH260 Nano only
TRGLVLMAX = 1200  # mV  TH260 Nano only

CFDLVLMIN = -1200  # mV  TH260 Pico only
CFDLVLMAX = 0  # mV  TH260 Pico only
CFDZCMIN = -40  # mV  TH260 Pico only
CFDZCMAX = 0  # mV  TH260 Pico only

CHANOFFSMIN = -99999  # ps, for TH260_SetSyncChannelOffset and TH260_SetInputChannelOffset
CHANOFFSMAX = 99999  # ps

OFFSETMIN = 0  # ns, for TH260_SetOffset
OFFSETMAX = 100000000  # ns

ACQTMIN = 1  # ms, for TH260_StartMeas
ACQTMAX = 360000000  # ms  (100*60*60*1000ms = 100h)

STOPCNTMIN = 1  # for TH260_SetStopOverflow
STOPCNTMAX = 4294967295  # 32 bit is mem max

TRIGOUTMIN = 0  # for TH260_SetTriggerOutput, 0=off
TRIGOUTMAX = 16777215  # in units of 100ns

HOLDOFFMIN = 0  # ns, for TH260_SetMarkerHoldoffTime
HOLDOFFMAX = 25500  # ns

TDCODEMIN = 0  # for TH260_SetDeadTime
TDCODEMAX = 7

# The following are bitmasks for return values from GetWarnings()

WARNING_SYNC_RATE_ZERO = 0x0001
WARNING_SYNC_RATE_VERY_LOW = 0x0002
WARNING_SYNC_RATE_TOO_HIGH = 0x0004
WARNING_INPT_RATE_ZERO = 0x0010
WARNING_INPT_RATE_TOO_HIGH = 0x0040
WARNING_INPT_RATE_RATIO = 0x0100
WARNING_DIVIDER_GREATER_ONE = 0x0200
WARNING_TIME_SPAN_TOO_SMALL = 0x0400
WARNING_OFFSET_UNNECESSARY = 0x0800
WARNING_DIVIDER_TOO_SMALL = 0x1000
WARNING_COUNTS_DROPPED = 0x2000

# For header

BITSLEN_MAGIC = 8
BITSLEN_VERSION = 8
BITSLEN_RECORD = 32

BITSLEN_TAG_ID = 32
BITSLEN_TAG_IDX = 4
BITSLEN_TAG_TYPECODE = 4
BITSLEN_TAG_VALUE = 8

SUBMODE_OSC = 0
SUBMODE_INT = 1
SUBMODE_TRES = 2
SUBMODE_IMG = 3

STOPREASON_TIMEOVER = 0
STOPREASON_MANUAL = 1
STOPREASON_OVERFLOW = 2
STOPREASON_ERROR = 3
STOPREASON_UNKNOWN = -1
STOPREASON_FIFO_OVERRUN = -2

SOFTWARE_NAME = 'Quentin Peter'
SOFTWARE_VERSION = '0.1'
CONTENT_VERSION = '2.0'

TTTR_MAGIC = 'PQTTTR'
FILE_VERSION = '1.1.00'

INIT_WAIT_TIME = 0.15
