from collections import defaultdict
from pathlib import Path
from time import time

import h5py
import numpy as np
from tqdm import tqdm


class MatDataExtractor:
    def __init__(self, file_name):
        self.file_name = Path(file_name)
        assert self.file_name.suffix == ".mat"
        self._open_file = h5py.File(self.file_name, "r")
        self.trials = self._open_file["trials"]
        self.npix_meta = self._open_file["npix_meta"]
        self.trial_colnames = list(self.trials.keys())
        self._no_trials = max(self.trials[self.trial_colnames[0]].shape)
        self._no_units = max(self.npix_meta["cluster_ids"].shape)
        subject_array = self._open_file[self.trials["subject"][0, 0]]
        self.subject_name = "".join(
            [chr(subject_array[i, 0]) for i in range(subject_array.shape[0])]
        )

    def get_trial_times(self):
        """
        Trial start and end times for given trial nos.
        """
        start_time_list = []
        stop_time_list = []
        for trial_no in range(self._no_trials):
            start_time_list.append(
                self._open_file[self.trials["npix_start_idx"][0, trial_no]][0, 0]/3e4
            )
            stop_time_list.append(
                self._open_file[self.trials["npix_stop_idx"][0, trial_no]][0, 0]/3e4
            )
        return np.array(start_time_list), np.array(stop_time_list)

    def get_trial_epochs(self):
        """
        Trial start and end times for given trial nos.
        """
        trial_start, trial_end = self.get_trial_times()

        def get_val(name, trial_no):
            return (
                    np.array(self._return_trial_value(name, trial_no=trial_no)).flatten()[0]
                    *1e-3
                    + trial_start[trial_no]*1e-3
            )

        events_list = {
            "target_onset_time": "TargetOnset",
            "go_cue_time": "GoCue",
            "move_start_time": "Move",
            "move_end_time": "MoveEnd",
            "target_acquired_time": "TargetAcquired",
            "target_held_time": "TargetHeld",
            "delay_period": "delay",
            "reaction_time": "rt",
        }

        events_dict = defaultdict(dict)
        for event_name in events_list:
            events_dict[event_name].update(
                data=[
                    get_val(events_list[event_name], i) for i in range(self._no_trials)
                ],
                description=f"{events_list[event_name]} time in s",
            )

        return events_dict

    def _return_trial_value(self, field, trial_no=0):
        return self._open_file[self.trials[field][0, trial_no]]

    def get_behavior_movement(self):
        trial_start, trial_end = self.get_trial_times()
        beh_fields = {"hand_position": "handPosition", "hand_speed": "handSpeed"}
        beh_dict = defaultdict(dict)
        for field in beh_fields:
            beh_dict[field].update(
                data=np.concatenate(
                    [
                        np.array(self._return_trial_value(beh_fields[field], i)).T
                        *1e-3
                        for i in range(self._no_trials)
                    ],
                    axis=0,
                ).squeeze(),
                description=f"{field} x,y,z in m",
            )
        beh_dict["times"].update(
            data=np.concatenate(
                [
                    np.array(self._return_trial_value("hand_time", i)).T*1e-3
                    + trial_start[i]
                    for i in range(self._no_trials)
                ],
                axis=0,
            ).squeeze(),
            description="time vector in s",
        )
        return beh_dict

    def get_trial_ids(self):
        return np.array(
            [
                self._return_trial_value("trialId", i)[0, 0]
                for i in range(self._no_trials)
            ]
        )

    def get_task_details(self):
        task_fields = {
            "centerX": "center hold location x: screen center origin, direction: right",
            "centerY": "center hold location y: screen center origin, direction: top",
            "targetX": "x position of target",
            "targetY": "y position of target",
            "targetSize": "target dia",
            "targetDirection": "reach direction in radians, measured clockwise from +X axis at 3:00",
            "targetDistance": "distance to reaching target",
            "saveTag": "internal trial grouping indicator",
            "success": "boolean indicator of trial success, these will be all be true by filtering",
        }
        task_dict = defaultdict(dict)
        for field, desc in task_fields.items():
            task_dict[field].update(
                data=[
                    self._return_trial_value(field, i)[0, 0]
                    for i in range(self._no_trials)
                ],
                description=desc,
            )
        return task_dict

    def extract_unit_spike_times(self, spike_ids: list = None):
        no_neurons = len(self._open_file[self.trials["npix"][0, 0]])
        if spike_ids is None:
            spike_ids = np.arange(no_neurons)
        trial_nos = np.arange(self._no_trials)
        spike_times_all_list = []
        trial_start, _ = self.get_trial_times()
        for _ in spike_ids:
            spike_times_all_list.append([])
        start = time()
        for trl in tqdm(trial_nos):
            sptimes = self._return_trial_value("npix", trl)
            for id in spike_ids:
                spike_times_all_list[id].extend(
                    (
                            self._open_file[sptimes[id, 0]][:].flatten()*1e-3
                            + trial_start[trl]
                    ).tolist()
                )
        print(time() - start)
        return spike_times_all_list

    def extract_unit_details(self, selfspike_ids: list = None):
        default_unit_args = {
            "cluster_ids": "id",
            "cluster_waveform_ch": "electrodes",
            "cluster_waveform_template": "waveform_mean",
        }
        custom_unit_args = {
            "cluster_amplitude": "peak to peak amplitude in uV",
            "cluster_is_localized": "boolean indicator of whether or not center of mass of "
                                    "waveform is well defined",
            # 'cluster_layer':'one of "Superficial", "Deep", "White" (white matter), or '
            #                 '"Unknown", cluster layer identified via current source density '
            #                 'and peak first waveforms analysis',
            "cluster_position_aligned": "spatial positions of neurons on probe, "
                                        "aligned using CSD analysis. for Y, 0 corresponds"
                                        " to the nominal cortical surface, and increasingly "
                                        "negative values indicate deeper in cortex towards white matter",
            "cluster_positions": "spatial positions of neurons on probe, using raw probe coordinates "
                                 "from the channel map. 0 corresponds to the tip of the probe, "
                                 "and increasingly positive values indicate shallower in cortex "
                                 "towards the surface (note: same orientation as aligned, "
                                 "different offset)",
            # 'cluster_ratings':'one of "good" or "unstable", individually hand-reviewed indicator '
            #                   'of neuron stability over trials during the session'
        }
        default_dict = defaultdict(dict)
        custom_dict = defaultdict(dict)
        for arg in default_unit_args:
            default_dict[default_unit_args[arg]].update(
                data=np.concatenate(
                    [
                        self.npix_meta[arg][:, i].flatten()[:, np.newaxis]
                        for i in range(self._no_units)
                    ],
                    axis=1,
                ).T
            )
        for arg in custom_unit_args:
            custom_dict[arg].update(
                data=np.concatenate(
                    [
                        self.npix_meta[arg][:, i].flatten()[:, np.newaxis]
                        for i in range(self._no_units)
                    ],
                    axis=1,
                ).T,
                description=custom_unit_args[arg],
            )
        return default_dict, custom_dict
