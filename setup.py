#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  1 09:51:24 2019

@author: quentinpeter
"""

from setuptools import setup, find_packages


def readme():
    with open('README.md') as f:
        return f.read()


setup(name='th260',
      version='1.0.0',
      description='Read from PicoQuant TH260',
      long_description=readme(),
      classifiers=[
          'Development Status :: 4 - Beta',
          'Programming Language :: Python :: 3 :: Only',
          'Topic :: Scientific/Engineering',
      ],
      keywords='single photon counting',
      url='https://github.com/impact27/th260',
      author='Quentin Peter',
      author_email='qaep2@cam.ac.uk',
      license='',
      packages=find_packages(),
      install_requires=[
          'numpy',
      ],
      include_package_data=True,
      zip_safe=False)
