import numpy as np
import scipy.io as scio
from pathlib import Path
import neo


class MatDataExtractor:

    def __init__(self, input_dir):
        raw_file_loc = list(Path(input_dir).glob('**/*.ns2'))[0].parent
        path_r_file = list(Path(input_dir).glob('**/RC*.mat'))[0]
        rfile = scio.loadmat(str(path_r_file))
        self.nsx_loc = Path(raw_file_loc)
        self.R = rfile['R'][0]
        self.SU = rfile['SU']
        self._no_trials = self.R.shape[0]
        self._no_units = self.SU[0,0]['unitLookup'].shape[0]

    def get_trial_ids(self):
        return [self.R['CerebusInfoA'][i]['trialID'][0, 0][0, 0] for i in range(self._no_trials)]

    def extract_unit_spike_times(self, trial_nos=None):
        if trial_nos is None:
            trial_nos = np.arange(self._no_trials)
        units_list = []
        for trial_no in trial_nos:
            units_list.append([self.R['unit'][trial_no]['spikeTimes'][0][i].flatten()/1e3 for i in range(self._no_units)])
        return units_list

    def extract_trial_times(self, trial_nos=None):
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

    def extract_trial_events(self, trial_nos=None):
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

    def extract_trial_details(self, trial_nos=None):
        """
                Time in seconds wrt trial start time
                """
        if trial_nos is None:
            trial_nos = np.arange(self._no_trials)
        trial_details_dict = []
        events = [['possibleRTproblem','discardTrial',"flag that will usually be 0, but is set to 1 "
                                                      "if there was a photo box problem (meaning RT can't be "
                                                      "calculated accurately) or we had a hand tracking error "
                                                      "during the movement. In general, throw those trials away."],
                  ['success','task_success',"indicates whether the monkey was successful on this trial"],
                  ['trialType','trialType','trial type'],
                  ['trialVersion','trialVersion','should be 0 for a truly random maze '
                                                 '(two random barriers). For a degenerate maze'
                                                 ' (real maze with some barriers randomly removed) '
                                                 'trialVersion is >10'],
                  ['protoTrial','protoTrial','whether that trial was used as the prototype '
                                             'trial for figuring out which trials were consistent'],
                  ['primaryCondNum','maze_condition',
                   'The set of 27 (or 108) mazes included was composed of 3 (or 12) “subsets”. '
                   'Each subset contained 3 related mazes. Each maze had 3 “versions”: the 3-target with barrier, '
                   'the 1-target with barriers, and the 1-target with no barriers. These 3 versions shared the same '
                   'target positions. The 3-target and 1-target versions also shared the same barrier positions. '
                   'In the 3-target version, exactly one target was accessible ']]
        for event in events:
            trial_details_dict.append(dict(name=event[1],
                                          data=np.array([self.R[event[0]][i][0, 0] for i in trial_nos]),
                                          description=event[2]))

        return trial_details_dict
    
    def extract_behavioral_position(self, trial_nos=None):
        trial_times,_ = self.extract_trial_times()
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

    def extract_lfp(self):
        nsx_files_list = list([i.stem.strip('datafile') for i in self.nsx_loc.glob('**/*.ns2')])
        no_segments = 5
        raw_files_names = []
        for seg_no in range(no_segments):
            if f'A00{seg_no}' in nsx_files_list:
                assert f'B00{seg_no}' in nsx_files_list
                raw_files_names.append([f'A00{seg_no}',f'B00{seg_no}'])
        lfps = [None]*len(raw_files_names)
        for no, data_part in enumerate(raw_files_names):
            electrodes = [None]*2
            for elec_no, electrode in enumerate((data_part)):
                nev_file = self.nsx_loc/f'datafile{electrode}.nev'
                print(f'reading: {nev_file.name}')
                bk = neo.BlackrockIO(str(nev_file))
                electrodes[elec_no] = bk.get_analogsignal_chunk()
            lfps[no] = electrodes
        return lfps
    
    def extract_maze_data(self, trial_nos=None):
        if trial_nos is None:
            trial_nos = np.arange(self._no_trials)
        maze_details_list = []
        maze_details = [
            ['numFlies', 'maze_num_targets', 'number of targets presented'],
            ['numBarriers', 'maze_num_barriers', 'number of barriers presented'],
            ['novelMaze', 'novelMaze', 'novel maze']
        ]
        for maze_data in maze_details:
            maze_details_list.append(dict(name=maze_data[1],
                                           data=np.array([self.R[maze_data[0]][i][0, 0] for i in trial_nos]),
                                           description=maze_data[2]))
        # add target positions/size:
        target_positions = []
        for i in trial_nos:
            target_positions.append(np.concatenate([self.R['PARAMS'][i][0, 0]['flyX'],
                                                    self.R['PARAMS'][i][0, 0]['flyY']],
                                                   axis=0).T)
        hit_target_position = np.concatenate(
            [pos[self.R['whichFly'][no][0, 0] - 1, :][:, np.newaxis].T for no, pos in enumerate(target_positions)])
        maze_details_list.append(dict(name='hit_target_position',
                                       data=hit_target_position,
                                       description='x,y position on screen of the target hit'))
        target_size = np.array([self.R['PARAMS'][i][0, 0]['flySize'][0, 0] for i in trial_nos])
        maze_details_list.append(dict(name='target_size',
                                       data=target_size,
                                       description='half width of the targets'))
        barrier_data = []
        for trial_no in trial_nos:
            non_empty = True if len(self.R['BARRIER'][trial_no])>0 else False
            struct_len = self.R['BARRIER'][trial_no]['X'].shape[1] if non_empty else 0
            keys = ['X','Y','halfHeight','halfWidth']
            out_ar = np.zeros([struct_len,4])
            for no, key in enumerate(keys):
                out_ar[:, no] = \
                    np.array([self.R['BARRIER'][trial_no][key][0,i][0, 0] for i in range(struct_len)]).squeeze()
            barrier_data.append(out_ar)
        maze_details_list.append(dict(name='barrier_info',
                                      data=barrier_data,
                                      description='(x,y,halfwidth,halfhwidth)'))
        return maze_details_list