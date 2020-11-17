import sys, os

import numpy as np
import pandas as pd
from nptdms import TdmsFile
import wave
import struct

# from sklearn.preprocessing import StandardScaler

# from dateutil.relativedelta import relativedelta
# from datetime import datetime

# ### plotting libs
# import matplotlib.pyplot as plt
# plt.style.use('seaborn-colorblind')


def read_noise_tdms(filename, sampleRate=51200):

    # read metadata and TDMS channel data
    noisedata = TdmsFile(filename)

    # parse start time of recording
    # strip off folders
    startTime = filename.split("/")[-1].split("_")[:2]
    # join date (YYYYMMDD) to time (HHMMSS)
    startTime = "_".join(startTime)

    # convert tdms data to pd.DataFrame
    noisedf = noisedata.as_dataframe()

    # Make time index
    noisedf.index = pd.TimedeltaIndex(
        data=1 / sampleRate * np.arange(len(noisedf)), unit="s"
    )

    return noisedf, startTime


def tdms2wav(
    noisedf,
    startTIme,
    writedir,
    calData=False,
    sampleRate=51200,
    sampleWidth=2,
    maxVolume=None,
):

    channelNames = noisedf.columns

    for cn in range(len(channelNames)):

        if calData:
            filename = writedir + "{}_CAL_channel_{}.wav".format(
                startTIme, channelNames[cn].split("'/'")[-1].split("'")[0]
            )
        else:
            filename = writedir + "{}_NOISE_channel_{}.wav".format(
                startTIme, channelNames[cn].split("'/'")[-1].split("'")[0]
            )

        print("Writing data to:", filename)

        # create wave_write file object
        obj = wave.open(filename, "wb")

        # establish parameters
        sampleRate = sampleRate  # hertz
        sampleWidth = sampleWidth
        if maxVolume is None:
            maxVolume = 2 ** (8 * sampleWidth - 1) - 1

        # set parameters
        obj.setnchannels(1)  # mono
        obj.setsampwidth(sampleWidth)
        obj.setframerate(sampleRate)

        ## Scale input data
        data = noisedf[channelNames[cn]]
        data = data / np.max((data.max(), data.min()))

        # 16-bit audio data is written as integers
        tmp = (maxVolume / 2 * data).astype(int).values

        # binary data is packed as little-endian, unsigned integers
        formatlist = ["<"] + ["h"] * len(tmp)
        formatlist = ("").join(formatlist)
        # pack bindary data
        buf = struct.pack(formatlist, *tmp)
        # write data to file
        obj.writeframesraw(buf)
        obj.close()
