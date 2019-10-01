#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Class to read tttr buffers and process them

Created on Wed Jul 24 13:46:53 2019

@author: Quentin Peter
"""
import numpy as np

from th260.ptu_format import read_T2_buffer, read_T3_buffer


T2WRAPAROUND_V2 = 0x2000000
T3WRAPAROUND = 0x400


class ExtendableTable():
    """Wrap around a numpy array for frequent append."""

    def __init__(self, ndim=None, dtype='uint32'):
        """
        uint32 is enough to store everything, as this is what the device gives.
        """
        if ndim is not None:
            shape = (0x100, ndim)
        else:
            shape = (0x100, )
        self.__data = np.zeros(shape, dtype=dtype)
        self._size = 0
        self._ndim = ndim
        self.dtype = dtype

    def add(self, data):
        """
        Add list to table, growing it as needed.
        """

        new_size = self._size + np.shape(data)[0]
        self._inner_resize(new_size)

        self.__data[self._size:new_size] = data
        self._size = new_size

    def _inner_resize(self,  new_size):
        """
        New size for array.
        """
        capacity = len(self.__data)
        if new_size >= capacity:
            new_capacity = 2 ** int(np.ceil(np.log2(new_size)))
            if self._ndim is not None:
                shape = (new_capacity, self._ndim)
            else:
                shape = (new_capacity, )
            newdata = np.empty(shape, dtype=self.dtype)
            newdata[:self._size] = self.__data[:self._size]
            self.__data = newdata

    def __len__(self):
        """
        Length of data.
        """
        return self._size

    @property
    def data(self):
        """
        Get the data.
        """
        return self.__data[:self._size]

    def remove(self, nremove):
        '''Remove from the data.'''
        new_size = self._size - nremove
        self.__data[:new_size] = self.__data[nremove:self._size]
        self._size = new_size


class binnableTable(ExtendableTable):

    def __init__(self, ndim=None, dtype='uint32',
                 bin_factor=None, only_bin=False):
        super().__init__(ndim=ndim, dtype=dtype)
        self._bin_factor = bin_factor
        self._bin_read_position = 0
        self._bin_counts = np.zeros(0, dtype=int)
        self._only_bin = only_bin

    def bin_count(self):
        """Get bin counts with factor given in set_bin_time."""

        if self._bin_factor is None:
            raise RuntimeError('Need to set bin factor.')

        newpos = self._size
        if newpos == self._bin_read_position:
            return self._bin_counts

        timetags = self.data[self._bin_read_position:newpos]
        timetags = timetags // self._bin_factor

        bin_count = np.bincount(timetags)
        bin_count[:len(self._bin_counts)] += self._bin_counts

        self._bin_counts = bin_count
        if self._only_bin:
            self.remove(newpos)
            self._bin_read_position = 0
        else:
            self._bin_read_position = newpos
        return bin_count

    def set_bin_factor(self, bin_factor):
        """Change the bin time and discards the saved values."""
        if self._only_bin:
            raise NotImplementedError("We don't have the raw data")
        self._bin_factor = bin_factor
        self._bin_read_position = 0
        self._bin_counts = np.zeros(0, dtype=int)


class T2Result():
    def __init__(self, channel, global_resolution,
                 bin_time=None, only_bin=False):
        """
        Resolution of the record.
        """
        self._channel = channel
        self._bin_time = bin_time
        self.global_resolution = global_resolution

        if self._bin_time:
            bin_factor = int(1e12 * self._bin_time / self.global_resolution)
        else:
            bin_factor = None

        # uint64 doesn't work with bincount
        # (https://github.com/numpy/numpy/issues/823)
        self._timetags = binnableTable(
            dtype='int64', bin_factor=bin_factor, only_bin=only_bin)
        self._n_overflows = 0

    def add_buffer(self, buffer):
        """
        Batch read T2 buffer.
        """
        n_overflows, timetag, total_overflows = (
            read_T2_buffer(buffer, channel=self._channel, rtype='photon'))

        n_overflows = self._n_overflows + np.asarray(n_overflows, 'int64')
        self._timetags.add(n_overflows * T2WRAPAROUND_V2 + timetag)

        self._n_overflows += total_overflows

    @property
    def timetags(self):
        """
        Time since the last overflow event, in controller units.
        """
        return self._timetags.data

    def time_s(self):
        """
        Arrival time of the photon, in s
        """
        return self.timetags * (self.global_resolution * 1e-12)

    def difftime_s(self):
        """
        Time since the last photon, in s.

        Uses int to avoid floating point rounding errors.
        """
        return np.diff(self.timetags) * (self.global_resolution * 1e-12)

    def bin_count(self):
        """Get bin counts with factor given in set_bin_time."""
        return self._timetags.bin_count()

    def bin_time(self):
        """
        Get the bin time.
        """
        return self._bin_time


class T3Result():
    def __init__(self, channel, global_resolution, resolution,
                 bin_time=None, only_bin=False):
        """
        T3 data need both a global resolution (for syncs events),
        and a resolution for dtime.
        """
        self.global_resolution = global_resolution
        self.resolution = resolution
        self._channel = channel

        self._bin_time = bin_time
        bin_factor = int(1e9 * self._bin_time / self.global_resolution)
        self._nsyncs = binnableTable(
            dtype='int64', bin_factor=bin_factor, only_bin=only_bin)

        self._dtimes = ExtendableTable(dtype='uint32')

    def add_buffer(self, buffer):
        """
        Read T3 buffer.
        """
        n_overflows, dtime, nsync, total_overflows = (
            read_T3_buffer(buffer, channel=self._channel, rtype='photon'))

        n_overflows = self._n_overflows + np.asarray(n_overflows, 'int64')
        self._nsyncs.add(n_overflows * T3WRAPAROUND + nsync)
        self._dtimes.add(dtime)

        self._n_overflows += total_overflows

    @property
    def nsyncs(self):
        """
        Number of syncs events since the last overflow.
        """
        return self._nsyncs.data

    @property
    def dtimes(self):
        """
        Time in controller units since the last sync event.
        """
        return self._dtimes

    def sync_time_s(self):
        """
        Time in seconds of the last sync event, ns resolution.
        """
        return self.nsyncs * (self.global_resolution * 1e-9)

    def dtime_s(self):
        """
        Time in seconds since the last sync event, ps resolution.
        """
        return self.dtimes * (self.resolution * 1e-12)

    def bin_count(self):
        """Get bin counts with factor given in set_bin_time."""
        return self._nsyncs.bin_count()
