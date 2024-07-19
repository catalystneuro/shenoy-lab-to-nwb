from pathlib import Path
from typing import Union

import numpy as np
from neuroconv.basedatainterface import BaseDataInterface
from pynwb import NWBFile
from pynwb.behavior import Position

from .matextractor import MatDataExtractor

PathType = Union[str, Path]


class ShenoyMatDataInterface(BaseDataInterface):
    def __init__(self, filename: PathType, subject_name: str = "J"):
        super().__init__()
        self.file_path = Path(filename)
        assert self.file_path.suffix == ".mat", "file_path should be a .mat"
        assert self.file_path.exists(), "file_path does not exist"
        self.mat_extractor = MatDataExtractor(self.file_path, monkey_name=subject_name)

    def _extract_channel_spike_times(self):
        trial_spike_times = self.mat_extractor.extract_unit_spike_times()
        trial_times, _ = self.mat_extractor.extract_trial_times()
        unit_spike_times = []
        for chan in range(len(trial_spike_times[0])):
            channel_ts = []
            for trialno in range(len(self.mat_extractor._good_trials)):
                channel_ts.extend(
                    trial_spike_times[trialno][chan] + trial_times[trialno, 0]
                )
                if trial_spike_times[trialno][chan].size > 0:
                    assert (
                            trial_spike_times[trialno][chan][-1] < trial_times[trialno, 1]
                    )
            unit_spike_times.append(np.array(channel_ts))
        return unit_spike_times, trial_times

    def run_conversion(self, nwbfile: NWBFile, metadata: dict, **kwargs):
        assert isinstance(nwbfile, NWBFile), "'nwbfile' should be of type pynwb.NWBFile"
        (
            eye_positions,
            hand_positions,
            cursor_positions,
        ) = self.mat_extractor.extract_behavioral_position()
        eye_data = np.concatenate(eye_positions, axis=0)
        cursor_data = np.concatenate(cursor_positions, axis=0)
        hand_data = np.concatenate(hand_positions, axis=0)
        trial_events = self.mat_extractor.extract_trial_events()
        trial_details = self.mat_extractor.extract_trial_details()
        maze_details = self.mat_extractor.extract_maze_data()
        unit_lookup = self.mat_extractor.SU["unitLookup"][0, 0][:, 0]
        array_lookup = self.mat_extractor.SU["arrayLookup"][0, 0][:, 0]
        unit_spike_times, trial_times = self._extract_channel_spike_times()
        # add behavior:
        beh_mod = nwbfile.create_processing_module(
            "behavior", "contains monkey movement data"
        )
        position_container = Position()
        spatial_series_list = []
        for name, data in zip(
                ["Eye", "Hand", "Cursor"], [eye_data, hand_data, cursor_data]
        ):
            spatial_series_list.append(
                position_container.create_spatial_series(
                    name=name,
                    data=data[:, :2],
                    timestamps=data[:, 2],
                    reference_frame="screen center",
                    conversion=np.nan,
                )
            )
        beh_mod.add(position_container)
        # add trials:
        for col_details in trial_events + trial_details + maze_details:
            col_det = {i: col_details[i] for i in col_details if "data" not in i}
            nwbfile.add_trial_column(**col_det)
        for trial_no in range(trial_times.shape[0]):
            col_details_dict = {
                i["name"]: i["data"][trial_no]
                for i in trial_events + trial_details + maze_details
            }
            col_details_dict.update(
                start_time=trial_times[trial_no, 0],
                stop_time=trial_times[trial_no, 1],
                timeseries=spatial_series_list,
            )
            nwbfile.add_trial(**col_details_dict)
        # add units:
        unit_lookup_corrected = [
            list(np.array([ch_id - 1]) + 96) if array_lookup[no] == 2 else [ch_id - 1]
            for no, ch_id in enumerate(unit_lookup)
        ]
        for unit_no in range(len(unit_spike_times)):
            nwbfile.add_unit(
                spike_times=unit_spike_times[unit_no],
                electrodes=unit_lookup_corrected[unit_no],
                electrode_group=list(nwbfile.electrode_groups.values())[
                    array_lookup[unit_no] - 1
                    ],
                obs_intervals=trial_times,
            )
