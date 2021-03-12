import numpy as np
import scipy.io as scio




class MatDataExtractor:

    def __init__(self, path_r_file, path_n_file):
        rfile = scio.loadmat(path_r_file)
        nfile = scio.loadmat(path_n_file)
        self.R = rfile['R'][0]
        self.N = nfile['Ns'][0]
        self.SU = rfile['SU']
        self._no_trials = self.R.shape[0]
        self._no_units = self.N.shape[0]

    def _get_trial_ids(self):
        return [self.R['CerebusInfoA'][i]['trialID'][0, 0][0, 0] for i in range(self._no_trials)]

    def _extract_unit_spike_times(self, trial_nos=None):
        if trial_nos is None:
            trial_nos = np.arange(self._no_trials)
        units_list = []
        for i in trial_nos:
            units_list.append([self.R['unit'][0]['spikeTimes'][0][i].flatten()/1e3 for i in range(self._no_units)])
        return units_list

    def _extract_trial_times(self, trial_nos=None):
        """
        Times in seconds
        """
        if trial_nos is None:
            trial_nos = np.arange(self._no_trials)
        return np.array([[self.R['CerebusInfoA'][i]['startTime'][0, 0][0, 0],
                          self.R['CerebusInfoA'][i]['endTime'][0, 0][0, 0]]
                         for i in trial_nos])

    def _extract_trial_events(self, trial_nos=None):
        """
        Time in seconds wrt trial start time
        """
        if trial_nos is None:
            trial_nos = np.arange(self._no_trials)
        trial_events_dict = dict()
        events = {'actualFlyAppears':'target_presentation',
                  'actualLandingTime': 'go_cue',
                  'offlineRT': 'RT'}
        for event in events:
            trial_events_dict.update({events[event]: np.array([self.R[event][i][0,0] for i in trial_nos])/1e3})
        return trial_events_dict
