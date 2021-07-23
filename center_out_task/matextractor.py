import numpy as np
import h5py
from pathlib import Path
from scipy.sparse import csc_matrix
from datetime import datetime, timedelta
from tqdm import tqdm


class MatDataExtractor:

    def __init__(self, file_name):
        self.file_name = Path(file_name)
        assert self.file_name.suffix == '.mat'
        self._open_file = h5py.File(self.file_name, 'r')
        self.R = self._open_file['R']
        self._colnames = list(self.R.keys())
        self._no_trials = len(self.R[self._colnames[0]])
        self.session_start = self._convert_matlab_datenum(0)
        self.subject_name = ''.join(
            [chr(self.R[self.R['subject'][0][0]][j, 0])
             for j in range(len(self.R[self.R['subject'][0][0]]))])

    def _chr_convert(self, array):
        if isinstance(array, np.ndarray):
            array = array.flatten()
        out = ''.join([chr(i) for i in array])
        return out

    def _convert_matlab_datenum(self, trial_no: float):
        matlab_datenum = self.R[self.R['startDateNum'][trial_no][0]][0, 0]
        time = datetime.fromordinal(int(matlab_datenum)) + \
               timedelta(days=matlab_datenum%1) - \
               timedelta(days=366)
        return time

    def get_trial_times(self, trial_nos: list = None):
        if trial_nos is None:
            trial_nos = range(self._no_trials)

        time_list = []
        for trial_no in trial_nos:
            start_date = self._convert_matlab_datenum(trial_no)
            trial_len = self.R[self.R['trialLength'][trial_no][0]][0, 0]
            time_range = np.arange(trial_len)/1e3
            time_diff = (start_date - self.session_start)
            time_diff_sec = time_diff.seconds + np.round((time_diff.microseconds*1e-6), 3)
            time_list.append(time_diff_sec + time_range)
        return time_list

    def _return_array(self, field, element=0):
        if element == 0:
            return [self.R[self.R[field][i][0]][0, 0] for i in range(self._no_trials)]
        else:
            return [self.R[self.R[field][i][0]][:int(self.R[self.R['trialLength'][i][0]][0, 0]), :].squeeze()
                    for i in range(self._no_trials)]

    def get_trial_ids(self):
        return self._return_array('trialNum')

    def extract_unit_spike_times(self, spike_ids: list = None):
        if spike_ids is None:
            spike_ids = np.arange(192)
        trial_nos = np.arange(self._no_trials)
        spike_times_all_list = []
        for _ in spike_ids:
            spike_times_all_list.append([])
        for trl in tqdm(trial_nos):
            spike_times = self.get_trial_times(trial_nos=[trl])[0]
            ch_count = 0
            for no, ar in enumerate(['', '2']):
                sp1 = self.R[self.R[f'spikeRaster{ar}'][trl][0]]
                sp_bool = csc_matrix(
                    (sp1['data'], sp1['ir'], sp1['jc']), shape=(96, len(sp1['jc']) - 1)).toarray()
                trial_len = self.R[self.R['trialLength'][trl][0]][0, 0]
                spk_ids_bool = ((no*96) <= spike_ids) & (spike_ids < ((no + 1)*96))
                sp_bool = sp_bool[spike_ids[spk_ids_bool] - no*96, :int(trial_len)]
                for sp in sp_bool:
                    spike_times_all_list[ch_count].extend(spike_times[sp >= 1])
                    ch_count += 1
        return spike_times_all_list

    def extract_behavioral_position(self):
        out_dict = [dict(name='Eye',
                         description='pos of eye in x,y',
                         data=np.concatenate(self._return_array('eyePos', element=1))),
                    dict(name='Cursor',
                         description='cursor pos on screen in x,y',
                         data=np.concatenate(self._return_array('cursorPos', element=1))[:, :2]),
                    dict(name='Hand',
                         description='hand pos in x,y,z',
                         data=np.concatenate(self._return_array('handPos', element=1))),
                    dict(name='DecodePos',
                         description='decoded pos in x,y',
                         data=np.concatenate(self._return_array('decodePos', element=1)))]
        return out_dict

    def extract_stimulus(self):
        juice = np.concatenate([self.R[self.R['juice'][i][0]]['jc'][:int(self.R[self.R['trialLength'][i][0]][0, 0])]
                                for i in range(self._no_trials)])
        return juice

    def extract_task_data(self):
        trial_times = self.get_trial_times()
        trial_params = [self.R[self.R['startTrialParams'][i][0]] for i in range(self._no_trials)]
        out_dict = [dict(name='is_successful',
                         description='if monkey started before the mandatory delay period after target shown',
                         data=self._return_array('isSuccessful')),
                    dict(name='task_type',
                         description='which target configuration',
                         data=[trlparams['taskID'][0, 0]*1e-3 for no, trlparams in
                               enumerate(trial_params)]),
                    dict(name='reach_time',
                         description='max time to reach the target',
                         data=[trial_times[no][0] + trlparams['timeReach'][0, 0]*1e-3 for no, trlparams in
                               enumerate(trial_params)]),
                    dict(name='target_hold_time',
                         description='min time required to have successfully acquired the target',
                         data=[trial_times[no][0] + trlparams['timeTargetHold'][0, 0]*1e-3 for no, trlparams in
                               enumerate(trial_params)]),
                    dict(name='fail_time',
                         description='time limit to target reach failure',
                         data=[trial_times[no][0] + trlparams['timeFail'][0, 0]*1e-3 for no, trlparams in
                               enumerate(trial_params)]),
                    dict(name='target_pos',
                         description='position of target on screen',
                         data=[trlparams['posTarget'][()].squeeze() for trlparams in trial_params],
                         index=True),
                    dict(name='target_size',
                         description='target size',
                         data=[trlparams['sizeTarget'][()].squeeze() for trlparams in trial_params],
                         index=True),
                    dict(name='barrier_points',
                         description='barrier points location',
                         data=[trlparams['barrierPoints'][()].squeeze() for trlparams in trial_params],
                         index=True)]
        return out_dict

    def extract_task_times(self):
        trial_times = self.get_trial_times()
        time_target_on = []
        time_target_acquire = []
        time_target_held = []
        time_target_shown = []
        for i in range(self._no_trials):
            trial_start = trial_times[i][0]
            target_acquire = self.R[self.R['timeTargetAcquire'][i][0]]
            target_on = self.R[self.R['timeTargetOn'][i][0]]
            target_held = self.R[self.R['timeTargetHeld'][i][0]]
            delay_time = self.R[self.R['delayTime'][i][0]][0,0]
            if len(target_acquire.shape) > 1:
                if target_acquire.shape == (1, 1):
                    time_target_acquire.append([target_acquire[0, 0]/1e3 + trial_start])
                else:
                    time_target_acquire.append((target_acquire[()]/1e3 + trial_start).squeeze().tolist())
            else:
                time_target_acquire.append([np.nan])
            if len(target_held.shape) > 1:
                time_target_held.append(target_held[0, 0]/1e3 + trial_start)
            else:
                time_target_held.append(np.nan)
            if len(target_on.shape) > 1:
                time_target_on.append(target_on[0, 0]/1e3 + trial_start)
            else:
                time_target_on.append(np.nan)
            if np.isnan(delay_time):
                time_target_shown.append(time_target_on[-1])
            else:
                time_target_shown.append(time_target_on[-1] - delay_time/1e3)
        out_dict = [dict(name='go_cue_time',
                         description='time when the go cue was given',
                         data=time_target_on),
                    dict(name='target_acquire_time',
                         description='time when target was acquired by monkey',
                         data=time_target_acquire,
                         index=True),
                    dict(name='target_held_time',
                         description='time until which target was held by monkey',
                         data=time_target_held),
                    dict(name='target_shown_time',
                         description='time when target was shown but before the go cue was given',
                         data=time_target_shown)
                    ]
        return out_dict
