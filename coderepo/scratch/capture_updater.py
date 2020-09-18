#!/usr/bin/env python
# coding: utf-8

import sys
import os

import numpy as np
import pandas as pd
from nptdms import TdmsFile
from dateutil.relativedelta import relativedelta
from datetime import datetime

### plotting libs
import matplotlib.pyplot as plt
plt.style.use('seaborn-colorblind')

### Directory setup
cwd = os.getcwd()
datapath = os.path.abspath(os.path.join(cwd, '../data/'))
figpath = os.path.abspath(os.path.join(cwd, 'figs/'))

filename = os.path.join(datapath,
                        'DOE15_SlowData_2020_02_10_14_34_59_1Hz.tdms')
tdms_file = TdmsFile(filename)

channels = ['LabVIEW Timestamp', 'Windspeed_87m', 'WD1_87m']

dataset = {
    channel: tdms_file.object('SlowData', channel).data
    for channel in channels
}
dataset['LabVIEW Timestamp'] = [
    datetime.fromtimestamp(x - 2082844800)
    for x in dataset['LabVIEW Timestamp']
]
dataset = pd.DataFrame.from_dict(dataset)
dataset = dataset.set_index('LabVIEW Timestamp')

data1T = dataset.resample('1T').mean()

wdbins = np.arange(100, 201, 10)
wsbins = np.arange(2, 7.1) + 0.5

fig, ax = plt.subplots(figsize=(5, 3))

dataset['Windspeed_87m'].plot(ax=ax, c='C0')
# ax.plot(timestamp, windspeed, c='C0')
ax.set_xlabel('Datetime')
ax.set_ylabel('Wind Speed [m/s]', c='C0')

ax2 = ax.twinx()
dataset['WD1_87m'].plot(ax=ax2, c='C1')
# ax2.plot(timestamp, winddirection, c='C1')
ax2.set_ylabel('Wind Direction [$^\circ$]', c='C1')

plt.tight_layout()
plt.show()

fig, ax = plt.subplots()

cpct, _, _, counts = ax.hist2d(data1T[channels[1]],
                               data1T[channels[2]], [wsbins, wdbins],
                               cmap='plasma')

for i in range(len(wdbins) - 1):
    for j in range(len(wsbins) - 1):
        ax.text(wsbins[j] + 0.5,
                wdbins[i] + 5,
                np.int(cpct.T[i, j]),
                color="w",
                ha="center",
                va="center",
                fontweight="bold")

plt.colorbar(counts, ax=ax, label='Number of 1-min Obs.')
ax.set_xlabel('Wind Speed Bin [m/s]')
ax.set_ylabel('Wind Direction Bin [$^\circ$]')

plt.tight_layout()
plt.show()
