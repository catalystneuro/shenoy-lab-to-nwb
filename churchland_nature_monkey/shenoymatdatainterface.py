from pathlib import Path
import numpy as np
from typing import Union
from nwb_conversion_tools import NWBConverter
from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.json_schema_utils import get_base_schema, dict_deep_update
from nwb_conversion_tools.utils import get_schema_from_hdmf_class
from pynwb import NWBFile
from pynwb.behavior import Position, SpatialSeries
from pynwb.misc import Units
from matextractor import MatDataExtractor
from pynwb.base import DynamicTable

PathType = Union[str, Path]


class ShenoyMatDataInterface(BaseDataInterface):
    def __init__(self, filename: PathType, subject_name="J"):
        super().__init__()
        self.file_path = Path(filename)
        self._subject_name = subject_name
        assert self.file_path.suffix == ".mat", "file_path should be a .mat"
        assert self.file_path.exists(), "file_path does not exist"
        self.mat_extractor = MatDataExtractor(
            self.file_path, monkey_name=self._subject_name
        )

    @classmethod
    def get_source_schema(cls):
        base = super().get_source_schema()
        base.update(
            required=["filename"],
            properties=dict(
                filename=dict(type="string", format="file"),
                subject_name=dict(type="string"),
            ),
        )
        return base

    @staticmethod
    def _convert_schema_object_to_array(schema_to_convert):
        base_schema = get_base_schema()
        base_schema.update(type="array")
        _ = base_schema.pop("properties")
        base_schema["items"] = schema_to_convert
        return base_schema

    def get_metadata_schema(self):
        metadata_schema = NWBConverter.get_metadata_schema()
        metadata_schema["required"] = ["Behavior", "trials", "units"]
        metadata_schema["properties"]["Behavior"] = get_base_schema()
        metadata_schema["properties"]["Intervals"] = get_base_schema()

        dt_schema = get_base_schema(DynamicTable)
        dt_schema["additionalProperties"] = True
        metadata_schema["properties"]["Behavior"]["properties"] = dict(
            Position=get_base_schema(),
        )
        metadata_schema["properties"]["Behavior"]["properties"]["Position"][
            "properties"
        ] = dict(
            Position=self._convert_schema_object_to_array(
                get_schema_from_hdmf_class(SpatialSeries)
            ),
        )
        metadata_schema["properties"]["Intervals"]["properties"] = dict(
            Trials=dt_schema,
        )
        units_schema = get_schema_from_hdmf_class(Units)
        units_schema["additionalProperties"] = True
        metadata_schema["properties"]["Units"] = units_schema
        return metadata_schema

    def get_metadata(self):
        metadata = dict(
            Behavior=dict(
                Position=[
                    dict(name="Eye", reference_frame="screen center"),
                    dict(name="Hand", reference_frame="screen center"),
                    dict(name="Cursor", reference_frame="screen center"),
                ]
            ),
            Intervals=dict(
                Trials=dict(
                    name="trials", description="metadata about experimental trials"
                )
            ),
            Units=dict(name="units"),
        )
        return metadata

    def _extract_channel_spike_times(self):
        trial_spike_times = self.mat_extractor.extract_unit_spike_times()
        trial_times, _ = self.mat_extractor.extract_trial_times()
        unit_spike_times = []
        for chan in range(len(trial_spike_times[0])):
            channel_ts = []
            for trialno in range(self.mat_extractor._no_trials):
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
                electrodes=[unit_lookup_corrected[unit_no]],
                electrode_group=list(nwbfile.electrode_groups.values())[
                    array_lookup[unit_no] - 1
                ],
                obs_intervals=trial_times,
            )
