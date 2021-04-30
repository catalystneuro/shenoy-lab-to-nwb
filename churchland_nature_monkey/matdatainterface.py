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
        return

    def _convert_schema_object_to_array(self, schema_to_convert):
        base_schema = get_base_schema()
        base_schema.update(type='array')
        _ = base_schema.pop('properties')
        base_schema['items'] = get_base_schema()
        base_schema['items']['properties'] = schema_to_convert
        return base_schema

    def get_metadata_schema(self):
        metadata_schema = NWBConverter.get_metadata_schema()
        metadata_schema['required'] = ['Behavior', 'trials', 'units', 'Ecephys']
        metadata_schema['properties']['Ecephys'] = get_base_schema()
        metadata_schema['properties']['Behavior'] = get_base_schema()
        metadata_schema['properties']['Intervals'] = get_base_schema()
        metadata_schema['properties']['Electrodes'] = get_base_schema()

        metadata_schema['properties']['Ecephys'] = get_base_schema(tag='Ecephys')

        metadata_schema['properties']['Ecephys']['properties'] = dict(
            Device=self._convert_schema_object_to_array(get_schema_from_hdmf_class(Device)),
            ElectrodeGroup=self._convert_schema_object_to_array(get_schema_from_hdmf_class(ElectrodeGroup)))
        metadata_schema['properties']['Ecephys']['required'] = ['Device', 'ElectrodeGroup', 'ElectricalSeries']
        dt_schema = get_base_schema(DynamicTable)
        dt_schema['additionalProperties'] = True
        metadata_schema['properties']['Electrodes']['properties'] = dict(
            ElectrodeTable=dt_schema,
        )
        metadata_schema['properties']['Behavior']['properties'] = dict(
            Position=get_base_schema(),
        )
        metadata_schema['properties']['Behavior']['properties']['Position']['properties'] = dict(
            Position=self._convert_schema_object_to_array(get_schema_from_hdmf_class(SpatialSeries)),
        )
        metadata_schema['properties']['Intervals']['properties'] = dict(
            Trials=dt_schema,
        )
        units_schema = get_schema_from_hdmf_class(Units)
        units_schema['additionalProperties'] = True
        metadata_schema['properties']['Units'] = units_schema
        return metadata_schema

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
            Ecephys=dict(Device=[dict(name='Utah Array(M1)',
                                      description='96 channel utah array',
                                      manufacturer='BlackRock Microsystems'),
                                 dict(name='Utah Array(PMd)',
                                      description='96 channel utah array',
                                      manufacturer='BlackRock Microsystems')],
                         ElectrodeGroup=[dict(name='M1 array',
                                              description='',
                                              location='M1',
                                              device='Utah Array(M1)'),
                                         dict(name='PMd array',
                                              description='',
                                              location='PMd',
                                              device='Utah Array(PMd)')]),
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
            Units=dict(spike_times=unit_spike_times,
                       electrodes=[unit_lookup_corrected],
                       obs_intervals=trial_times),
            Electrodes=dict(ElectrodeTable=dict(name='electrodes',
                                                description='metadata about extracellular electrodes'))
        )
        return metadata

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

    def run_conversion(self, nwbfile: NWBFile, metadata: dict = None, **kwargs):
        assert isinstance(nwbfile, NWBFile), "'nwbfile' should be of type pynwb.NWBFile"
        metadata_default = self.get_metadata()
        metadata = dict_deep_update(metadata_default, metadata)
        # add devices:
        device_list = []
        for device_kwargs in metadata['Ecephys']['Device']:
            device_list.append(nwbfile.create_device(**device_kwargs))
        # add electrode groups:
        elec_group_list = []
        for egroup_kwargs in metadata['Ecephys']['ElectrodeGroup']:
            egroup_kwargs['Device'] = nwbfile.device.get(egroup_kwargs['Device'])
            elec_group_list.append(nwbfile.create_electrode_group(**egroup_kwargs))
        # create electrodes table:
        for electrode_no in range(192):
            id = 1 if electrode_no > 95 else 0
            nwbfile.add_electrode(x=np.nan, y=np.nan, z=np.nan, imp=np.nan,
                                  location=metadata['Ecephys']['ElectrodeGroup'][id]['location'],
                                  filtering='1000Hz',
                                  group=elec_group_list[id], id=electrode_no)
        # add behavior:
        beh_mod = nwbfile.create_processing_module('behavior', 'contains monkey movement data')
        position_container = Position()
        for pos_container_args in metadata['Behavior']['Position']:
            position_container.create_spatial_series(**pos_container_args)
        beh_mod.add(position_container)
        # add trials:
        trials_kwargs = dict()
        for col_details in metadata['Intervals']['Trials']:
            trials_kwargs.update({col_details['name']:col_details['data']})
            if col_details['name'] not in ['start_time','stop_time']:
                nwbfile.add_trial_column(name=col_details['name'],
                                         description=col_details['description'])
        for trial_no in range(trials_kwargs['start_time'].shape[0]):
            nwbfile.add_trial(**{i['name']:i['data'][trial_no] for i in trials_kwargs})
        # add units:
        array_lookup = self.mat_extractor.SU['arrayLookup'][0, 0][:, 0]
        for unit_no in range(len(metadata['Units']['spike_times'])):
            unit_kwargs = {i:j[unit_no] for i,j in metadata['Units'].items()}
            unit_kwargs.update(electrode_group=elec_group_list[array_lookup[unit_no]-1])
            nwbfile.add_unit(**unit_kwargs)
