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
        trial_times = np.array([[self.R['CerebusInfoA'][i]['startTime'][0, 0][0, 0],
                                 self.R['CerebusInfoA'][i]['endTime'][0, 0][0, 0]]
                                for i in trial_nos])
        split_id = np.where(np.diff(trial_times[:, 0]) < 0)[0][0] + 1
        # find mean inter_trial times:
        inter_trial_intervals = np.array(
            [trial_times[i + 1, 0] - trial_times[i, 1] for i in range(self._no_trials - 1)])
        inter_trial_intervals = np.delete(inter_trial_intervals, split_id-1)
        mean_interval = np.mean(inter_trial_intervals)
        offset_value = trial_times[split_id-1,1]+mean_interval-trial_times[split_id,0]
        trial_times[split_id:,:]=trial_times[split_id:,:]+offset_value
        return trial_times, split_id

    def _extract_trial_events(self, trial_nos=None):
        """
        Time in seconds wrt trial start time
        """
        if trial_nos is None:
            trial_nos = np.arange(self._no_trials)
        trial_events_dict = dict()
        events = {'actualFlyAppears': 'target_presentation',
                  'actualLandingTime': 'go_cue',
                  'onlineRT': 'RT',
                  'moveBeginsTime': 'moveBeginsTime',
                  'moveEndsTime': 'moveEndsTime'}
        for event in events:
            trial_events_dict.update({events[event]: np.array([self.R[event][i][0, 0]
                                                               if self.R[event][i].shape[0]!=0
                                                               else np.nan
                                                               for i in trial_nos])/1e3})
        return trial_events_dict

    def _extract_trial_details(self, trial_nos=None):
        """
                Time in seconds wrt trial start time
                """
        if trial_nos is None:
            trial_nos = np.arange(self._no_trials)
        trial_events_dict = dict()
        events = {'possibleRTproblem': 'discardTrial',
                  'success': 'task_success',
                  'unhittable': 'unhittable',
                  'trialType': 'trialType',
                  'trialVersion': 'trialVersion',
                  'novelMaze': 'novelMaze'}

        maze_details = {
            'mazeID': 'maze_ID',
            'numFlies': 'maze_num_targets',
            'numBarriers': 'maze_num_barriers',
            'BARRIER': 'maze_barrier_location',
            'activeFly': 'accessible_target',
            'whichFly': 'hit_target',
            'flySize': 'half_width_target'
        }
        for event in events:
            trial_events_dict.update({events[event]: np.array([self.R[event][i][0, 0] for i in trial_nos])})
        # discard trials:

        return trial_events_dict

    def _create_unit_details(self, unit_nos=None):
        pass
