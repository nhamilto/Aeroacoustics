# import stuff
import os
import datetime
import pandas as pd
import numpy as np
import pickle
import sys
from nptdms import TdmsFile
   
def read_NoiseLabSlice_file(filename):
    """Read a noiselab "train" file containing Leq and 1/3 octave bands in 10 second slices.
    The file can contain slices for mutiple recordings. The returned dataframe will parse 
    the recording names into microphone # and date/time.

    inputs:
    filename: Input file to read

    outputs:
    df_nl: Dataframe of the file 
    """

    df_nl = pd.read_csv(filename,sep='\t')

    # remove whitespace
    df_nl.rename(columns=lambda x: x.strip(),inplace=True)

    # convert to numeric
    cols_num = [c for c in df_nl.columns.values if c not in ('Clip Name','Filter Settled')]
    for col in cols_num:
        df_nl[col] = pd.to_numeric(df_nl[col],errors='coerce')

    # create new column for third octave bands
    df_nl['third_octave_spectrum'] = df_nl[df_nl.columns.values[33:-4]].values.tolist()
    df_nl['third_octave_spectrum'] = df_nl['third_octave_spectrum'].apply(lambda x: np.array(x))

    # columns to keep
    # cols_keep = ['Clip Name', 'Start Time', 'Duration [s]', 'Leq',
    #     'Filter Settled', '20.0', '25.0', '31.5', '40.0', '50.0', '63.0', '80.0',
    #     '100.0', '125.0', '160.0', '200.0', '250.0', '315.0', '400.0', '500.0',
    #     '630.0', '800.0', '1000.0', '1250.0', '1600.0', '2000.0', '2500.0',
    #     '3150.0', '4000.0', '5000.0', '6300.0', '8000.0', '10000.0', '12500.0',
    #     '16000.0', '20000.0', 'Settle [s]']
    cols_keep = ['Clip Name', 'Start Time', 'Duration [s]', 'Leq',
        'Filter Settled', 'Settle [s]', 'third_octave_spectrum']

    df_nl = df_nl[cols_keep]

    # drop unwanted rows
    df_nl = df_nl[df_nl['Duration [s]'] == 10.0]
    df_nl = df_nl[df_nl['Settle [s]'] == 0.0] # remove first slice where filter settling. Might not be necessary.

    # Get date, time, and mic # from Clip Name
    df_nl[['date','time','mic']] = df_nl['Clip Name'].str.split('_',expand=True)[[1,2,6]]
    df_nl['time'] = pd.to_datetime(df_nl['date']+' '+df_nl['time'])

    # add clip start time to time column
    df_nl['time'] = df_nl['time'] + pd.to_timedelta(df_nl['Start Time'], unit='s')
    df_nl.drop(columns=['Duration [s]','Filter Settled','Settle [s]','date','Start Time'],inplace=True)

    return df_nl

def read_NoiseLabFFTSlice_file(filename):
    """Read a noiselab "train" file containing FFT spectra in 10 second slices.
    The file can contain slices for mutiple recordings. The returned dataframe will parse 
    the recording names into microphone # and date/time.

    inputs:
    filename: Input file to read

    outputs:
    df_nl: Dataframe of the file 
    """

    df_nl = pd.read_csv(filename,sep='\t')

    # remove whitespace
    df_nl.rename(columns=lambda x: x.strip(),inplace=True)

    # create new column for spectrum
    df_nl['spectrum'] = df_nl[df_nl.columns.values[5:]].values.tolist()
    df_nl['spectrum'] = df_nl['spectrum'].apply(lambda x: np.array(x))

    # convert to numeric
    cols_num = ['Slice  Number']
    for col in cols_num:
        df_nl[col] = pd.to_numeric(df_nl[col],errors='coerce')

    # create a start time column
    df_nl['Start Time'] = 10*(df_nl['Slice  Number']-1)

    # columns to keep
    cols_keep = ['Clip Name', 'Start Time', 'df', 'f0', 'spectrum']

    df_nl = df_nl[cols_keep]

    # drop unwanted rows
    df_nl = df_nl.dropna()

    # Get date, time, and mic # from Clip Name
    df_nl[['date','time','mic']] = df_nl['Clip Name'].str.split('_',expand=True)[[1,2,6]]
    df_nl['time'] = pd.to_datetime(df_nl['date']+' '+df_nl['time'])

    # add clip start time to time column
    df_nl['time'] = df_nl['time'] + pd.to_timedelta(df_nl['Start Time'], unit='s')
    df_nl.drop(columns=['date','Start Time'],inplace=True)

    return df_nl

def read_tdmsSCADA_file(filename):
    """Read a tdms file containing DOE1.5 turbine SCADA and met tower data.
    The returned dataframe contains the variables of interest as a function of GPS time.

    inputs:
    filename: Input file to read

    outputs:
    df_sc: Dataframe of the file 
    """

    currFile = TdmsFile(filename)
    df_sc = currFile.as_dataframe()

    #rename columns
    col_names = list(df_sc.columns)
    for i in range(len(col_names)):
        col_names[i] = col_names[i].replace('/\'SlowData\'/\'','')[:-1]
    df_sc.columns = col_names

    # set timestamp
    # TODO: For now, rounding timestamp to nearest second. Should we change to interpolating to integer seconds?
    df_sc['time'] = pd.to_datetime(currFile.object('SlowData','MS Excel Timestamp').time_track(absolute_time=True))
    df_sc['time'] = df_sc.time.dt.round(freq='s')

    # yaw offset target
    df_sc['Yaw_Offset_Cmd'] = df_sc.WD_Nacelle_Mod - df_sc.WD_Nacelle

    # columns to keep
    # TODO:
    # 1) Yaw_Encoder seems to be calibrated to true North (it agrees with WD1_87m)
    # 2) Not sure what combination of the EGD_OpCtl variables will be helpful for turbine status info
    # 3) Is EGD_In_WindSpd a corrected version of NacelleWindSpeed?
    # 4) What is the difference between met instruments 1 and 2?
    # 5) The "EGD" prefixes seem to be new as of mid Feb. 2020. Before they were "OPC." Check the 
    #    variables again when the aeroacoustics experiments starts
    cols_keep = ['time', 'Hum1', 'Temp1', 'Hum2', 'Temp2',
       'Windspeed_87m', 'WD1_87m', 'Air_Press_2', 'Air_Press_1',
       'WindSpeed_80m', 'Active Power', 'LSS RPM', 'NacelleWindSpeed',
       'Yaw_Encoder', 'Pitch_Blade1', 'WD_Mod_Active', 'WD_Nacelle', 
       'WD_Nacelle_Mod', 'Yaw_Offset_Cmd', 'EGD_AI_In_GridMonRealPowerAct',
       'EGD_In_RotorSpd', 'EGD_In_WindSpd', 'EGD_OpCtl_TurbineFullState',
       'EGD_OpCtl_TurbineOperationState', 'EGD_OpCtl_TurbineStatus',
       'EGD_Out_CalcTrbineStateSCADA', 'EGD_Out_TurbineStatusSCADA']

    #df_sc = df_sc[cols_keep]

    return df_sc
