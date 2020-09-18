#!/usr/bin/python

import sys

if len(sys.argv) < 2:
    print('No file specified. Looking for latest data...')

if len(sys.argv) == 2:
    print('loading data from', sys.argv[-1])
    print(type(sys.argv[-1]))