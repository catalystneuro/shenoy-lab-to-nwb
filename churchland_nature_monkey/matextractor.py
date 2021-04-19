import numpy as np
import scipy.io as scio


class MatDataExtractor:

    def __init__(self, path_r_file):
        rfile = scio.loadmat(path_r_file)
        self.R = rfile['R'][0]
        self.SU = rfile['SU']
        self._no_trials = self.R.shape[0]
        self._no_units = self.SU[0,0]['unitLookup'].shape[0]

    def _get_trial_ids(self):
        return [self.R['CerebusInfoA'][i]['trialID'][0, 0][0, 0] for i in range(self._no_trials)]

    def _extract_unit_spike_times(self, trial_nos=None):
        if trial_nos is None:
            trial_nos = np.arange(self._no_trials)
        units_list = []
        for trial_no in trial_nos:
            units_list.append([self.R['unit'][trial_no]['spikeTimes'][0][i].flatten()/1e3 for i in range(self._no_units)])
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
        trial_events_dict = []
        events = [['actualFlyAppears','target_presentation','time of target presentation'],
                  ['actualLandingTime','go_cue','time of go cue'],
                  ['onlineRT','RT','reaction time'],
                  ['moveBeginsTime','moveBeginsTime','movement onset time'],
                  ['moveEndsTime','moveEndsTime','movement stop time']]
        for event in events:
            trial_events_dict.append(dict(name=event[1],
                                          data=np.array([self.R[event[0]][i][0, 0]
                                                       if self.R[event[0]][i].shape[0]!=0
                                                       else np.nan
                                                       for i in trial_nos])/1e3,
                                          description=event[2]))
        return trial_events_dict

    def _extract_trial_details(self, trial_nos=None):
        """
                Time in seconds wrt trial start time
                """
        if trial_nos is None:
            trial_nos = np.arange(self._no_trials)
        trial_events_dict = []
        events = [['possibleRTproblem','discardTrial',"flag that will usually be 0, but is set to 1 if there was a photo box problem (meaning RT can't be calculated accurately) or we had a hand tracking error during the movement. In general, throw those trials away."],
                  ['success','task_success',"indicates whether the monkey was successful on this trial"],
                  ['trialType','trialType','trial type'],
                  ['trialVersion','trialVersion','trial version'],
                  ['novelMaze','novelMaze','novel maze']]
        for event in events:
            trial_events_dict.append(dict(name=event[1],
                                          data=np.array([self.R[event[0]][i][0, 0] for i in trial_nos]),
                                          description=event[2]))
        maze_details = [
            ['numFlies','maze_num_targets','number of targets presented'],
            ['numBarriers','maze_num_barriers','number of barriers presented'],
            ['activeFly','accessible_target',"indicates which target is accessible (indices match flyX and flyY)."],
            ['whichFly','hit_target',"indicates which target was hit (indices match flyX and flyY)"]
        ]
        for maze_data in maze_details:
            trial_events_dict.append(dict(name=maze_data[1],
                                          data=np.array([self.R[maze_data[0]][i][0, 0] for i in trial_nos]),
                                          description=maze_data[2]))
        #add target positions/size:
        target_positions = []
        for i in trial_nos:
            target_positions.append(np.concatenate([self.R['PARAMS'][i][0, 0]['flyX'],
                                                    self.R['PARAMS'][i][0, 0]['flyY']],
                                                   axis=0))
        target_size = np.array([self.R['PARAMS'][i][0, 0]['flySize'][0,0] for i in trial_nos])
        trial_events_dict.append(dict(name='target_position',
                                      data=target_positions,
                                      description='x,y position of all targets on screen'))
        trial_events_dict.append(dict(name='target_size',
                                      data=target_size,
                                      description='half width of the targets'))
        #add barrier position/size:
        return trial_events_dict
    
    def _create_behavioral_position(self, trial_nos=None):
        trial_times,_ = self._extract_trial_times()
        trial_nos = np.arange(self._no_trials) if trial_nos is None else trial_nos
        eye_positions = []
        hand_positions = []
        cursor_positions = []
        offset_hand_Y_jenkins = 8 # offset value, value saved is higher by this amount
        offset_hand_Y_nitschke = 24
        for trial_no in trial_nos:
            timestamps = trial_times[trial_no,0] + \
                         np.arange(len(self.R['EYE'][trial_no][0,0]['X'].squeeze()))/1000.0
            eye_positions.append(
                np.array([self.R['EYE'][trial_no][0,0]['X'].squeeze(),
                         self.R['EYE'][trial_no][0,0]['Y'].squeeze(),
                         timestamps]).T)
            hand_positions.append(
                np.array([self.R['HAND'][trial_no][0, 0]['X'].squeeze(),
                          self.R['HAND'][trial_no][0, 0]['Y'].squeeze()-offset_hand_Y_jenkins,
                          timestamps]).T)
            cursor_positions.append(
                np.array([self.R['CURSOR'][trial_no][0, 0]['X'].squeeze(),
                          self.R['CURSOR'][trial_no][0, 0]['Y'].squeeze(),
                          timestamps]).T)
        return eye_positions, hand_positions, cursor_positions
