# import stuff
import os
import datetime
import pandas as pd
import numpy as np
import pickle
import sys
   
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

    # columns to keep
    cols_keep = ['Clip Name', 'Start Time', 'Duration [s]', 'Leq',
        'Filter Settled', '20.0', '25.0', '31.5', '40.0', '50.0', '63.0', '80.0',
        '100.0', '125.0', '160.0', '200.0', '250.0', '315.0', '400.0', '500.0',
        '630.0', '800.0', '1000.0', '1250.0', '1600.0', '2000.0', '2500.0',
        '3150.0', '4000.0', '5000.0', '6300.0', '8000.0', '10000.0', '12500.0',
        '16000.0', '20000.0', 'Settle [s]']

    df_nl = df_nl[cols_keep]

    # convert to numeric
    cols_num = [c for c in cols_keep if c not in ('Clip Name','Filter Settled')]
    for col in cols_num:
        df_nl[col] = pd.to_numeric(df_nl[col],errors='coerce')

    # drop unwanted rows
    df_nl = df_nl[df_nl['Duration [s]'] == 10.0]
    df_nl = df_nl[df_nl['Settle [s]'] == 0.0] # remove first slice where filter settling. Might not be necessary.

    # Get date, time, and mic # from Clip Name
    df_nl[['date','time','mic']] = df_nl['Clip Name'].str.split('_',expand=True)[[1,2,3]]
    df_nl['time'] = pd.to_datetime(df_nl['date']+' '+df_nl['time'])

    # add clip start time to time column
    df_nl['time'] = df_nl['time'] + pd.to_timedelta(df_nl['Start Time'], unit='s')
    df_nl.drop(columns=['Duration [s]','Filter Settled','Settle [s]','date','Start Time'],inplace=True)

    return df_nl