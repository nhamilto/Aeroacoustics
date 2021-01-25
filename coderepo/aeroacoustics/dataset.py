# import stuff
import os
import datetime
import pandas as pd
import numpy as np
import pickle
import sys
import floris.utilities as geo

from aeroacoustics import read_data_files as rd
   
def identify_NoiseLabSlice_to_add(list_filename='noiseLAB_files.p',root_dir='/Volumes/Aeroacoustics/_ProcessedData/SliceData'):
    """Check list of NoiseLab Slice files already processed and determine 
    new files to add

    inputs:
    list_filename: pickle file containing list of NoiseLab Slice files processed
    root_dir: directory where noiseLAB slice files are saved

    outputs:
    files: List of new files to add 
    """

    # List the available files in the root dir
    files = os.listdir(os.path.join(root_dir))
    files = [f for f in files if ('.xls' in f)]

    # Get the list of processed filenames
    files_old = pickle.load( open( list_filename, "rb" ) )

    # Check for the files not in the processed list
    files = [f for f in files if f not in files_old]

    # Return in reverse order (most recent fist)
    files = sorted(files, reverse=False)

    return files

def process_NoiseLabSlice_file(filename, root_dir_noiselab='/Volumes/Aeroacoustics/_ProcessedData/SliceData',
                                root_dir_tdms='/Volumes/Tests/_raw data/Slow',
                                dataset_file='aeroacoustics_dataset.p',third_octave=True):
    """Read a noiseLAB slice file, combine it with turbine and met data and 
    append to the master dataset

    inputs:
    filename: noiseLAB slice file to process
    root_dir_noiselab: directory where noiseLAB slice files are saved
    root_dir_tdms: directory where SCADA tdms files are stored
    dataset_file: name of file containing master dataset
    """

    if third_octave:
        df_nl = rd.read_NoiseLabSlice_file(os.path.join(root_dir_noiselab,filename))
    else:
        df_nl = rd.read_NoiseLabFFTSlice_file(os.path.join(root_dir_noiselab,filename))

    # DEBUGGING, REMOVE!!!
    # df_nl.time = df_nl.time+pd.DateOffset(days=2)

    # drop clip name column, not needed. TODO: just remove this column in the reader function?
    df_nl.drop(columns=['Clip Name'],inplace=True)

    # group variables by mic name, set time as index
    df_new = df_nl.set_index(['time','mic'])
    df_new = df_new.unstack()
    df_new.columns = ['_'.join(col[::-1]) for col in df_new.columns.values]

    # load tdms SCADA files covering the noiseLAB data time period
    # TODO: It seems the previous day's folder is more likely to contain the next day's data.
    # See if this needs to be updated later
    tdms_dir = os.path.join(root_dir_tdms,(df_new.index[0]-pd.DateOffset(days=1)).strftime('%Y-%m-%d'))
    files = os.listdir(tdms_dir)
    files = [f for f in files if 'tdms_index' not in f]

    df_sc = pd.DataFrame()
    for f in files:
        df_sc = df_sc.append(rd.read_tdmsSCADA_file(os.path.join(tdms_dir,f)))

    # do we need to load previous day?
    if df_sc.time.min() > df_new.index.min():
        tdms_dir = os.path.join(root_dir_tdms,(df_new.index[0]-pd.DateOffset(days=2)).strftime('%Y-%m-%d'))

        files = os.listdir(tdms_dir)
        files = [f for f in files if 'tdms_index' not in f]

        for f in files:
            df_sc = df_sc.append(rd.read_tdmsSCADA_file(os.path.join(tdms_dir,f)))

    # do we need to load next couple days?
    for i in [0,1]:
        if df_sc.time.max()+pd.DateOffset(seconds=10) <= df_new.index.max():
            tdms_dir = os.path.join(root_dir_tdms,(df_new.index[0]+pd.DateOffset(days=i)).strftime('%Y-%m-%d'))

            files = os.listdir(tdms_dir)
            files = [f for f in files if 'tdms_index' not in f]

            for f in files:
                df_sc = df_sc.append(rd.read_tdmsSCADA_file(os.path.join(tdms_dir,f)))

    df_sc.drop_duplicates('time',inplace=True)
    df_sc.set_index('time',inplace=True)
    df_sc.sort_index(inplace=True)

    df_sc = df_sc[df_sc.index >= df_new.index[0]]

    # resample to 10 seconds w/ circular averaging for wind directions
    # columns to circularly average
    cols_circ = ['WD1_87m', 'Wind_Direction_38m', 'Yaw_Encoder', 'EGD_Yaw_PositionToNorth', 'Yaw_Offset_Cmd']

    for col in cols_circ:
        df_sc[col+'_cos'] = np.cos(np.radians(df_sc[col]))
        df_sc[col+'_sin'] = np.sin(np.radians(df_sc[col]))

    df_sc = df_sc.resample('10s',base=df_new.index[0].second).mean()

    for col in [c for c in cols_circ if c != 'Yaw_Offset_Cmd']:
        df_sc[col] = geo.wrap_360(np.degrees(np.arctan2(df_sc[col+'_sin'], df_sc[col+'_cos'])))

    col = 'Yaw_Offset_Cmd'
    df_sc[col] = geo.wrap_180(np.degrees(np.arctan2(df_sc[col+'_sin'], df_sc[col+'_cos'])))

    cols_vane = ['WD_Nacelle', 'WD_Nacelle_Mod']
    for col in cols_vane:
        df_sc[col] = df_sc[col] - 180.

    df_sc.drop(columns=[col for col in df_sc.columns if (('_cos' in col) | ('_sin' in col))],inplace=True)

    # trim to only same times as in df
    df_sc = df_sc[df_sc.index <= df_new.index[-1]]

    # combine df and df_sc
    df_new = pd.concat([df_new, df_sc], axis=1)

    # append to existing dataset
    df = pd.read_pickle(dataset_file)
    df = df.append(df_new)
    df = df.loc[~df.index.duplicated(keep='first')]
    df.sort_index(inplace=True)
    df.to_pickle(dataset_file)

    return 1
