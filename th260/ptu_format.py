#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Functions to write ptu files and read TTTR records.

Created on Fri Jul 26 12:02:22 2019

@author: Quentin Peter

Functions to write ptu header and read records.
"""

import struct
import numpy as np

from th260 import th260definitions as thdef

# =============================================================================
# Header help functions
# =============================================================================


def tab_string(bstring, length):
    """
    Write a binary string to the specified length, appending zeros as needed.
    """
    return bstring + bytes(length - len(bstring))


def write_tag(key, value):
    """
    Write a single tag.
    """
    if isinstance(key, tuple):
        tag_id, tag_idx = key
    else:
        tag_id = key
        tag_idx = None
    dtype = thdef.tag_types[tag_id]

    header = tab_string(tag_id.encode(), thdef.BITSLEN_TAG_ID)

    # Index
    if tag_idx is not None:
        header += tag_idx.to_bytes(thdef.BITSLEN_TAG_IDX, byteorder='little')
    else:
        header += bytes([0xff] * thdef.BITSLEN_TAG_IDX)

    # Type Code
    header += thdef.type_code[dtype].to_bytes(
        thdef.BITSLEN_TAG_TYPECODE, byteorder='little')

    # Data
    is_array = dtype in [
        'Float8Array',
        'ASCII-String',
        'Wide-String',
        'BinaryBlob']

    is_string = dtype in [
        'ASCII-String',
        'Wide-String']

    if dtype == 'Empty8':
        header += bytes(thdef.BITSLEN_TAG_VALUE)
    elif dtype in ['Bool8', 'Int8']:
        header += value.to_bytes(
            thdef.BITSLEN_TAG_VALUE, byteorder='little', signed=True)
    elif dtype == 'Float8':
        header += struct.pack("<d", value)
    elif dtype in ['BitSet64', 'Color8', 'TDateTime']:
        header += value
    elif is_array:
        # Prepare value
        if is_string:
            value = value.encode('UTF8')
        elif dtype == 'Float8Array':
            out = b''
            for val in value:
                out += struct.pack("<d", val)
            value = out
        # Get length
        length = len(value)
        if is_string:
            # null-terminated
            length += 1
        # Round to ceil 8
        length += (8 - length % 8) % 8
        header += length.to_bytes(
            thdef.BITSLEN_TAG_VALUE, byteorder='little', signed=False)

        header += tab_string(value, length)

    else:
        raise RuntimeError(f"No such dtype {dtype}")

    return header


def write_ptu(outputfilename, data, tags):
    """
    Save the data in a ptu file
    """

    header = tab_string(thdef.TTTR_MAGIC.encode(), thdef.BITSLEN_MAGIC)
    header += tab_string(
        thdef.FILE_VERSION.encode(), thdef.BITSLEN_VERSION)

    for key in tags:
        header += write_tag(key, tags[key])

    header += write_tag('Header_End', None)
    # Write file
    with open(outputfilename, "wb+") as outputfile:
        outputfile.write(header)
        outputfile.write(data)


def read_T2_record(record):
    """
    Read T2 event

    The bit allocation in the record is, starting from the MSB:
        special: 1
        channel: 6
        timetag: 25
    If the special bit is clear, it's a regular event record.
    If the special bit is set, the following interpretation of the channel
    code is given:
     - code 63 (all bits ones) identifies a timetag overflow, increment the
       overflow timetag accumulator. For HydraHarp V1 ($00010204) it always
       means one overflow. For all other types the number of overflows can
       be read from timetag value.
     - code 0 (all bits zeroes) identifies a sync event,
     - codes from 1 to 15 identify markers, the individual bits are
       external markers.
    """
    recordData = "{0:032b}".format(record)
    special = int(recordData[0:1], base=2)
    channel = int(recordData[1:7], base=2)
    timetag = int(recordData[7:32], base=2)
    if special == 1:
        if channel == 0x3F:  # Overflow
            return 'overflow', 0, timetag
        elif 15 >= channel >= 1:  # markers
            return 'marker', channel, timetag
        elif channel == 0:  # sync
            return 'sync', 0, timetag
        else:
            raise RuntimeError("Invalid record.")
    else:  # regular input channel
        return 'photon', channel + 1, timetag


def read_T3_record(record):
    '''
    Read T3 event

    The bit allocation in the record is, starting from the MSB:
         special: 1
         channel: 6
         dtime: 15
         nsync: 10
    If the special bit is clear, it's a regular event record.
    If the special bit is set, the following interpretation of the channel
    code is given:
     - code 63 (all bits ones) identifies a sync count overflow, increment
       the sync count overflow accumulator. For HydraHarp V1 ($00010304)
       it means always one overflow. For all other types the number of
       overflows can be read from nsync value.
     - codes from 1 to 15 identify markers, the individual bits are
       external markers.
    '''
    recordData = "{0:032b}".format(record)
    special = int(recordData[0:1], base=2)
    channel = int(recordData[1:7], base=2)
    dtime = int(recordData[7:22], base=2)
    nsync = int(recordData[22:32], base=2)

    if special == 1:
        if channel == 0x3F:  # Overflow
            return 'overflow', 0, dtime, nsync
        elif 15 >= channel >= 1:  # markers
            return 'marker', channel, dtime, nsync
        else:
            raise RuntimeError("Can't read record.")
    else:  # regular input channel
        return 'photon', channel + 1, dtime, nsync


def read_T2_buffer(buffer, channel=1, rtype='photon'):
    """
    Read T2 buffer

    The bit allocation in the record is, starting from the MSB:
        special: 1
        channel: 6
        timetag: 25
    If the special bit is clear, it's a regular event record.
    If the special bit is set, the following interpretation of the channel
    code is given:
     - code 63 (all bits ones) identifies a timetag overflow, increment the
       overflow timetag accumulator. For HydraHarp V1 ($00010204) it always
       means one overflow. For all other types the number of overflows can
       be read from timetag value.
     - code 0 (all bits zeroes) identifies a sync event,
     - codes from 1 to 15 identify markers, the individual bits are
       external markers.
    """
    # 10000000000000000000000000000000
    bitmask_special = 0x80000000
    # 01111110000000000000000000000000
    bitmask_channel = 0x7e000000
    # 11111110000000000000000000000000
    bitmask_header = bitmask_special | bitmask_channel
    # 00000001111111111111111111111111
    bitmask_timetag = 0x01ffffff

    # 11111110000000000000000000000000
    bit_overflow = 0xfe000000

    if rtype == 'photon':
        # -1 becauses reasons?
        bit_selected = (channel - 1) << 25
    elif rtype == 'marker':
        bit_selected = 0x80000000 + channel << 25
    elif rtype == 'sync':
        bit_selected = 0x80000000
    else:
        raise RuntimeError(f'Unknown type {rtype}')

    header = buffer & bitmask_header

    mask_overflows = header == bit_overflow
    mask_data = header == bit_selected

    timetags = buffer & bitmask_timetag
    overflows_counts = np.cumsum(timetags * mask_overflows, dtype='uint32')

    n_overflows = overflows_counts[mask_data]
    timetag = timetags[mask_data]
    total_overflows = overflows_counts[-1]

    return n_overflows, timetag, total_overflows


def read_T3_buffer(buffer, channel=1, rtype='photon'):
    '''
    Read T3 buffer

    The bit allocation in the record is, starting from the MSB:
         special: 1
         channel: 6
         dtime: 15
         nsync: 10
    If the special bit is clear, it's a regular event record.
    If the special bit is set, the following interpretation of the channel
    code is given:
     - code 63 (all bits ones) identifies a sync count overflow, increment
       the sync count overflow accumulator. For HydraHarp V1 ($00010304)
       it means always one overflow. For all other types the number of
       overflows can be read from nsync value.
     - codes from 1 to 15 identify markers, the individual bits are
       external markers.
    '''
    bitmask_special = 0x80000000
    bitmask_channel = 0x7e000000
    bitmask_header = bitmask_special | bitmask_channel
    bitmask_dtime = 0x01fffc00
    bitmask_nsync = 0x000003ff

    bit_overflow = 0xfe000000

    if rtype == 'photon':
        # -1 becauses reasons?
        bit_selected = (channel - 1) << 25
    elif rtype == 'marker':
        bit_selected = 0x80000000 + channel << 25
    else:
        raise RuntimeError(f'Unknown type {rtype}')

    header = buffer & bitmask_header

    mask_overflows = header == bit_overflow
    mask_data = header == bit_selected

    dtime = (buffer & bitmask_dtime) >> 10
    nsync = buffer & bitmask_nsync
    overflows_counts = np.cumsum(nsync * mask_overflows, dtype='uint32')

    n_overflows = overflows_counts[mask_data]
    dtime = dtime[mask_data]
    nsync = nsync[mask_data]
    total_overflows = overflows_counts[-1]

    return n_overflows, dtime, nsync, total_overflows
