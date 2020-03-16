import sys, os

import numpy as np
import pandas as pd
from nptdms import TdmsFile
from dateutil.relativedelta import relativedelta
from datetime import datetime

### plotting libs
import matplotlib.pyplot as plt
plt.style.use('seaborn-colorblind')


class CaptureTracker():
    '''
    Capture tracker class. Object methods load, process, and visualize data.
    '''
    def __init__(
        self,
        tdmsfilename=None,
        yawbincenters=np.array([
            -18.0,
            0.0,
            18,
            25,
        ]),
        yawbinwidth=5,
        wsbincenters=np.arange(6, 12),
        wsbinwidth=1.0,
        channels=[
            'LabVIEW Timestamp',
            'WindSpeed_87m',
            'WD1_87m',
            'WD_Mod_Active',
            'WD_Nacelle',
            'WD_Nacelle_Mod',
            'OPC_OpCtl_TurbineStatus',
            'Active Power',
        ],
        savedir='capture/',
    ):

        # set up some object stuff
        self.tdmsfilename = tdmsfilename
        self.yawbincenters = yawbincenters
        self.yawbinwidth = yawbinwidth
        self.wsbincenters = wsbincenters
        self.wsbinwidth = wsbinwidth
        self.channels = channels

        # setup save areas
        self.datasavedir = savedir
        self.figsavedir = os.path.join(self.datasavedir, 'figs/')

        # load data, extract specified channels
        self._load_tdms_data()
        self._extract_channels()

    ######################
    def _load_tdms_data(self):
        '''
        loads data from the specified file
        '''
        self.tdmsdata = TdmsFile(self.tdmsfilename)

    ######################
    def load_cumulative_data(self, file=None):
        '''
        loads data from the specified file
        '''

        # previous capture data
        if file is None:
            try:
                cumulative_datafiles = sorted([
                    x for x in os.listdir(self.datasavedir)
                    if 'cumulative' in x
                ])
                self.cumulative_data = pd.read_csv(cumulative_datafiles[-1])
            except:
                print('no exisiting cumulative data')
                print('starting new df ...')

                ind = pd.MultiIndex.from_arrays([[]] * 2,
                                                names=(u'yawbins', u'wsbins'))
                self.cumulative_data = pd.DataFrame(columns=['0', '1'],
                                                    index=ind)
                tmp = np.array([[x, y] for x in self.yawbincenters
                                for y in self.wsbincenters])

                # self.cumulative_data = pd.DataFrame(index=[self.yawbinsc])
        else:
            self.cumulative_data = pd.read_csv(file, header=[0, 1])

    ######################
    def _extract_channels(self):
        '''
        make dataframe of selected channels
        '''
        # Make dictionary containing specified channels and respective data
        dataset = {
            channel: self.tdmsdata.object('SlowData', channel).data
            for channel in self.channels
        }
        # convert LabVIEW Timestamp into human-readable datetime
        dataset['LabVIEW Timestamp'] = [
            datetime.fromtimestamp(x - 2082844800)
            for x in dataset['LabVIEW Timestamp']
        ]
        # make pandas DataFrame from dictionary
        dataset = pd.DataFrame.from_dict(dataset)
        # make datetime index
        dataset = dataset.set_index('LabVIEW Timestamp')
        # resample to 1 minute resolution and clean up
        dataset = dataset[dataset['Active Power'] > 1].resample(
            '1T').mean().dropna()

        self.dataset = dataset

        self.starttime = self.dataset.index[0]
        self.endtime = self.dataset.index[-1]

    ######################
    def bin_yaw_offsets(self):
        '''
        Calculate yaw offset from nacelle position, bin data according to the 
        self.yawbincenters and self.yawbinwidth
        '''
        self.dataset['yaw_offfset'] = self.dataset[
            'WD_Nacelle'] - self.dataset['WD_Nacelle_Mod']

        binedges = [(x - self.yawbinwidth / 2.0, x + self.yawbinwidth / 2.0)
                    for x in self.yawbincenters]
        binedges = [item for t in binedges for item in t]

        binlabels = ['garb'] * len(self.yawbincenters)
        binlabels = [x + '_{}'.format(ii) for ii, x in enumerate(binlabels)]
        binlabels = [x for x in zip(self.yawbincenters, binlabels)]
        binlabels = [item for t in binlabels for item in t][:-1]

        self.dataset['yawbins'] = pd.cut(self.dataset['yaw_offfset'],
                                         bins=binedges,
                                         labels=binlabels)

    ######################
    def bin_wind_speeds(self):
        '''
        Bin wind speed data according to 
        self.wsbincenters and self.wsbinwidth
        '''
        binedges = [(x - self.wsbinwidth / 2.0, x + self.wsbinwidth / 2.0)
                    for x in self.wsbincenters]
        binedges = [item for t in binedges for item in t]
        binedges = np.array(list(set(binedges)))
        self.dataset['wsbins'] = pd.cut(self.dataset['WindSpeed_87m'],
                                        bins=binedges,
                                        labels=self.wsbincenters)

    ######################
    def current_capture(self, save_current_data=True):
        '''
        Group observations according the respective wind speed and yaw offset bin, and count corresponding observations. 
        
        Save data to a csv file named with the timestamp of the last observation.
        
        Args:
            save_current_data (bool, optional): Flag to save bin counts to csv file. Defaults to True.
        '''

        # Check for binned data, if not, do it.
        if 'wsbins' not in self.dataset:
            self.bin_wind_speeds()
        if 'yawbins' not in self.dataset:
            self.bin_yaw_offsets()

        # make an empty df of the appropriate size
        emptycounts = pd.DataFrame(index=self.yawbincenters,
                                   columns=self.wsbincenters).fillna(0)

        self.capturecounts = self.dataset.dropna().groupby(
            ['yawbins', 'wsbins'])['yaw_offfset'].count().unstack()

        try:
            self.capturecounts = (emptycounts +
                                  self.capturecounts).fillna(0).astype(int)
        except:
            print('problem with data.')
            print(self.capturecounts.head())

    ######################
    def append_to_cumulative(self):

        currentdatadf = pd.Series()
        if not hasattr(self, 'running_df'):
            try:
                self.load_cumulative_data()
            except:
                print('cumulative data not found')
                pass

    ######################
    def cumulative_capture(self, save_running_total=True):

        if not hasattr(self, 'cumulative_data'):
            try:
                self.load_cumulative_data()
            except:
                print('cumulative data not found')
                pass

        running_capture_count = sorted(os.listdir(self.datasavedir))
        running_capture_count = [
            x for x in running_capture_count if '_capture_to_date' in x
        ]

        running_capture = pd.DataFrame(index=self.capturecounts.index,
                                       columns=self.capturecounts.columns)
        try:
            if self.endtime.strftime(
                    '%Y%m%d_%H%M%S') in running_capture_count[-1]:
                print('time already taken into account...')
                return
            running_capture = pd.read_csv(os.path.join(
                self.savedir, running_capture_count[-1]),
                                          index_col='Unnamed: 0')
            running_capture.columns = running_capture.columns.astype(np.int)
            print('adding previous capture data')
        except:
            print('no existing capture data found')

        self.running_capture = self.capturecounts.fillna(0).add(
            running_capture, fill_value=0)
        self.running_capture = self.running_capture.astype(np.int)

    ######################
    def vis_current_capture(self, savefig=True):
        '''
        Generate figure of capture matrix for the current file/data
        
        Args:
            savefig (bool, optional): Flag to save figure. Defaults to True.
        
        Returns:
            fig, ax: figure and axis
        '''
        fig, ax = plt.subplots()

        cpct = ax.pcolor(self.capturecounts, cmap='RdYlGn')

        # fix x ticks
        locs, labels = plt.xticks()
        locs = [(locs[i] + locs[i + 1]) / 2 for i in range(len(locs) - 1)]
        plt.xticks(ticks=locs, labels=self.wsbincenters)

        # fix y ticks
        locs, labels = plt.yticks()
        locs = [(locs[i] + locs[i + 1]) / 2 for i in range(len(locs) - 1)]
        plt.yticks(ticks=locs, labels=self.yawbincenters)

        plt.colorbar(cpct, ax=ax, label='Number of 1-min Obs.')

        ax.set_xlabel(r'Wind Speed Bin [m/s]')
        ax.set_ylabel(r'Yaw Offset Bin [$^\circ$]')

        for i, ws in enumerate(self.wsbincenters[:-1]):
            for j, yw in enumerate(self.yawbincenters[:-1]):
                if np.isnan(self.capturecounts.to_numpy()[i, j]):
                    continue
                ax.text(j + 0.5,
                        i + 0.5,
                        np.int(self.capturecounts.to_numpy()[i, j]),
                        color="k",
                        ha="center",
                        va="center",
                        fontweight="bold")

        plt.tight_layout()

        if savefig:
            figurename = self.endtime.strftime(
                '%Y%m%d_%H%M%S') + '_capture_matrix.pdf'
            fig.savefig(os.path.join(self.figsavedir, figurename))

        return fig, ax

    ######################
    def vis_cumulative_capture(self, savefig=True):
        '''
        Plot running total of capture matrix
        
        Args:
            savefig (bool, optional): Flag to save figure. Defaults to True.
        
        Returns:
            fig, ax: figure and axes object handles
        '''
        fig, ax = plt.subplots()

        pdat = self.running_capture.replace(0, np.nan).to_numpy()
        cpct = ax.pcolor(pdat, cmap='RdYlGn')

        # fix x ticks
        locs, _ = plt.xticks()
        locs = [(locs[i] + locs[i + 1]) / 2 for i in range(len(locs) - 1)]
        plt.xticks(ticks=locs, labels=self.wsbincenters)

        # fix y ticks
        locs, _ = plt.yticks()
        locs = [(locs[i] + locs[i + 1]) / 2 for i in range(len(locs) - 1)]
        plt.yticks(ticks=locs, labels=self.yawbincenters)

        plt.colorbar(cpct, ax=ax, label='Number of 1-min Obs.')

        ax.set_xlabel(r'Wind Speed Bin [m/s]')
        ax.set_ylabel(r'Yaw Offset Bin [$^\circ$]')

        for j, ws in enumerate(self.wsbincenters):
            for i, yw in enumerate(self.yawbincenters):
                if np.isnan(pdat[i, j]):
                    continue
                ax.text(j + 0.5,
                        i + 0.5,
                        pdat[i, j],
                        color="k",
                        ha="center",
                        va="center",
                        fontweight="bold")

        plt.tight_layout()

        if savefig:
            figurename = self.endtime.strftime(
                '%Y%m%d_%H%M%S') + '_running_total.pdf'
            fig.savefig(os.path.join(self.figsavedir, figurename))

        return fig, ax

    ######################
    def save_data(self, current_capture=True, cumulative_capture=True):

        ## save current capture data
        if current_capture:
            datafilename = self.endtime.strftime(
                '%Y%m%d_%H%M%S') + '_capture_data.csv'
            self.capturecounts.to_csv(
                os.path.join(self.datasavedir, datafilename))

        # save running total
        if cumulative_capture:
            datafilename = self.endtime.strftime(
                '%Y%m%d_%H%M%S') + '_cumulative_capture.csv'
            self.running_capture.to_csv(
                os.path.join(self.datasavedir, datafilename))


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print('No file specified. Looking for latest data...')
        datadir = os.path.abspath('')
        datafiles = sorted([x for x in os.listdir(datadir)])

    if len(sys.argv) == 2:
        print('loading data from', sys.argv[-1])

    ####### THis should occur in specific instances of the object, not the init.

    # # automate the process for a single data file
    # if bin_and_count:
    #     self.bin_yaw_offsets()
    #     self.bin_wind_speeds()
    #     self.cut_by_bins()
    #     self.current_capture_matrix()

    # # calculate running total of bin observations
    # if track_capture:
    #     self.add_running_total()
    #     self.running_capture_matrix()