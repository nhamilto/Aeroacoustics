#!/usr/bin/env python
# coding: utf-8

# In[1]:


import sys
import os

import numpy as np
import pandas as pd

# import matplotlib.pyplot as plt
# plt.style.use('seaborn-colorblind')
import datetime
from nptdms import TdmsFile
import wave

sys.path.append("../aeroacoustics/")
import CaptureTracker as ct
import TDMS2WAV as tw


# In[2]:


readpath = "/Volumes/Aeroacoustics/_RawData/FieldDay_20201105/"


# In[3]:


files = [x for x in os.listdir(readpath) if "index" not in x]


# In[5]:

filelist = open("processedFileList.txt", "a+")
processedfiles = filelist.readlines()

for file in files:
    if file in processedfiles:
        print(file, "already processed")
    else:
        try:
            noisedf, startTime = tw.read_noise_tdms(os.path.join(readpath, file))

            tw.tdms2wav(
                noisedf,
                startTime,
                "/Volumes/Aeroacoustics/_ProcessedData/FieldDay_20201105_WAV/",
            )
            processedfiles.write(file)
        except:
            print(file, "not processed due to error")
