from pathlib import Path
import numpy as np

from nwb_conversion_tools import NWBConverter
from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.json_schema_utils import get_base_schema, dict_deep_update
from nwb_conversion_tools.utils import get_schema_from_hdmf_class
from pynwb import NWBFile, TimeSeries
from pynwb.behavior import Position, SpatialSeries
from pynwb.file import Subject, TrialTable, ElectrodeTable
from pynwb.epoch import TimeIntervals
from pynwb.misc import Units
from .matextractor import MatDataExtractor
from pynwb.device import Device
from pynwb.ecephys import ElectrodeGroup
from pynwb.base import DynamicTable


class MatDataInterface(BaseDataInterface):

    def __init__(self, file_path: Path):
        super().__init__()
        self.file_path = Path(file_path)
        assert self.file_path.suffix == '.mat', 'file_path should be a .mat'
        assert self.file_path.exists(), 'file_path does not exist'
        self.mat_extractor = MatDataExtractor(self.file_path)

    @classmethod
    def get_source_schema(cls):
        base = super().get_source_schema()
        base.update(required=['file_path'],
                    properties=dict(
                        file_path=dict(
                            type='string')))
        return base

    def get_metadata_schema(self):
        metadata_schema = NWBConverter.get_metadata_schema()
        metadata_schema['required'] = ['Behavior', 'trials', 'units']
        metadata_schema['properties']['Behavior'] = get_base_schema()
        metadata_schema['properties']['Intervals'] = get_base_schema()
        metadata_schema['properties']['Units'] = get_base_schema()
        metadata_schema['properties']['Electrodes'] = get_base_schema()
        metadata_schema['properties']['Ecephys'] = get_base_schema(tag='Ecephys')
        metadata_schema['properties']['Ecephys']['properties'] = dict(
            Device=get_schema_from_hdmf_class(Device),
            ElectrodeGroup=get_schema_from_hdmf_class(ElectrodeGroup),
        )
        metadata_schema['properties']['Ecephys']['required'] = ['Device', 'ElectrodeGroup']
        metadata_schema['properties']['Electrodes']['properties'] = dict(
            ElectrodeTable=get_base_schema(DynamicTable),
        )
        metadata_schema['properties']['Behavior']['properties'] = dict(
            Position=get_base_schema(),
        )
        metadata_schema['properties']['Behavior']['properties']['Position']['properties'] = dict(
            Position=get_schema_from_hdmf_class(SpatialSeries),
        )
        metadata_schema['properties']['Intervals']['properties'] = dict(
            Trials=get_schema_from_hdmf_class(TrialTable),
        )
        metadata_schema['properties']['Units']['properties'] = dict(
            Units=get_schema_from_hdmf_class(Units),
        )

    def get_metadata(self):
        eye_positions, hand_positions, cursor_positions = \
            self.mat_extractor.extract_behavioral_position()
        eye_data = np.concatenate(eye_positions, axis=0)
        cursor_data = np.concatenate(cursor_positions, axis=0)
        hand_data = np.concatenate(hand_positions, axis=0)
        trial_events = self.mat_extractor.extract_trial_events()
        trial_details = self.mat_extractor.extract_trial_details()
        maze_details = self.mat_extractor.extract_maze_data()
        unit_lookup = self.mat_extractor.SU['unitLookup'][0, 0][:, 0]
        array_lookup = self.mat_extractor.SU['arrayLookup'][0, 0][:, 0]
        unit_spike_times, trial_times = self._extract_channel_spike_times()
        unit_lookup_corrected = [list(np.array([ch_id - 1]) + 96) if array_lookup[no] == 2 else [ch_id - 1]
                                 for no, ch_id in enumerate(unit_lookup)]
        metadata = dict(
            Ecephys=dict(Device=dict(),
                         ElectrodeGroup=dict()),
            Behavior=dict(Position=[dict(name='Eye',
                                         data=eye_data[:, :2],
                                         timestamps=eye_data[:, 2],
                                         reference_frame='screen center',
                                         conversion=np.nan),
                                    dict(name='Hand',
                                         data=hand_data[:, :2],
                                         timestamps=hand_data[:, 2],
                                         reference_frame='screen center',
                                         conversion=np.nan),
                                    dict(name='Cursor',
                                         data=cursor_data[:, :2],
                                         timestamps=cursor_data[:, 2],
                                         reference_frame='screen center',
                                         conversion=np.nan)
                                    ]
                          ),
            Intervals=dict(Trials=trial_events + trial_details + maze_details +
                                  [dict(name='start_time',
                                        data=trial_times[:, 0],
                                        description='Start time of epoch, in seconds'),
                                   dict(name='stop_time',
                                        data=trial_times[:, 1],
                                        description='Stop time of epoch, in seconds')
                                   ]),
            Units=dict(Units=dict(spike_times=unit_spike_times,
                                  electrodes=[unit_lookup_corrected],
                                  electrode_group=lambda x: electrode_group_list[array_lookup[x]-1],
                                  obs_intervals=trial_times)
                        ),
            Electrodes=dict(ElectrodeTable=[])
        )

    def _extract_channel_spike_times(self):
        trial_spike_times = self.mat_extractor.extract_unit_spike_times()
        trial_times, _ = self.mat_extractor.extract_trial_times()
        unit_spike_times = []
        for chan in range(len(trial_spike_times[0])):
            channel_ts = []
            for trialno in range(self.mat_extractor._no_trials):
                channel_ts.extend(trial_spike_times[trialno][chan] + trial_times[trialno, 0])
                if trial_spike_times[trialno][chan].size > 0:
                    assert trial_spike_times[trialno][chan][-1] < trial_times[trialno, 1]
            unit_spike_times.append(np.array(channel_ts))
        return unit_spike_times, trial_times
