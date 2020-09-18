import sys, os

import numpy as np
import pandas as pd
from nptdms import TdmsFile
from dateutil.relativedelta import relativedelta
from datetime import datetime

### plotting libs
import matplotlib.pyplot as plt
plt.style.use('seaborn-colorblind')

### some convenient magics
%load_ext autoreload
%autoreload 2

### Directory setup
cwd = os.getcwd()
datapath = os.path.abspath(os.path.join(cwd, '../../data/'))
figpath = os.path.abspath(os.path.join(cwd, 'figs/'))

filename = os.path.join(datapath, 'DOE15_SlowData_2020_02_10_14_34_59_1Hz.tdms')
tdms_file = TdmsFile(filename)

channels = ['LabVIEW Timestamp','Windspeed_87m','WD1_87m']
dataset = {channel: tdms_file.object('SlowData', channel) for channel in channels}

time = dataset['LabVIEW Timestamp'].data
timestamp = [datetime.fromtimestamp(x- 2082844800) for x in time]

windspeed = dataset['Windspeed_87m'].data
winddirection = dataset['WD1_87m'].data
