from pathlib import Path
import numpy as np
from typing import Union
from nwb_conversion_tools import NWBConverter
from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils.json_schema import get_base_schema, get_schema_from_hdmf_class
from pynwb import NWBFile, TimeSeries
from pynwb.behavior import Position, SpatialSeries
from pynwb.misc import Units
from .matextractor import MatDataExtractor
from pynwb.base import DynamicTable

PathType = Union[str, Path]


class COutMatDataInterface(BaseDataInterface):
    def __init__(self, filename: PathType):
        super().__init__()
        self.file_path = Path(filename)
        assert self.file_path.suffix == ".mat", "file_path should be a .mat"
        assert self.file_path.exists(), "file_path does not exist"
        self.mat_extractor = MatDataExtractor(self.file_path)

    @classmethod
    def get_source_schema(cls):
        base = super().get_source_schema()
        base.update(
            required=["filename"],
            properties=dict(
                filename=dict(type="string", format="file"),
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
        metadata_schema = get_base_schema()
        metadata_schema["required"] = ["Behavior", "Intervals", "Units"]
        metadata_schema["properties"] = dict()
        metadata_schema["properties"]["Behavior"] = get_base_schema()
        metadata_schema["properties"]["Intervals"] = get_base_schema()

        dt_schema = get_base_schema(DynamicTable)
        dt_schema["additionalProperties"] = True
        metadata_schema["properties"]["Behavior"]["properties"] = dict(
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

    def run_conversion(self, nwbfile: NWBFile, metadata: dict, **kwargs):
        assert isinstance(nwbfile, NWBFile), "'nwbfile' should be of type pynwb.NWBFile"
        (
            eye_positions,
            hand_positions,
            cursor_positions,
            decode_positions,
            juice
        ) = self.mat_extractor.extract_behavioral_position()
        trial_times = self.mat_extractor.get_trial_times()
        trial_times_all = np.concatenate(trial_times)
        task_data = self.mat_extractor.extract_task_data()
        task_times_data = self.mat_extractor.extract_task_times()
        # spike_times = self.mat_extractor.extract_unit_spike_times()

        # add behavior:
        beh_mod = nwbfile.create_processing_module(
            "behavior", "contains monkey movement data"
        )
        position_container = Position()
        spatial_series_list = []
        for name, data in zip(
            ["Eye", "Hand", "Cursor", "Decode"],
                [eye_positions, hand_positions, cursor_positions, decode_positions]
        ):
            spatial_series_list.append(
                position_container.create_spatial_series(
                    name=name,
                    data=data,
                    timestamps=trial_times_all,
                    reference_frame="screen center",
                    conversion=np.nan,
                )
            )
        beh_mod.add(position_container)
        #add stimulus:
        nwbfile.add_stimulus(TimeSeries(name='juice_reward',
                                        description='times when the juice reward was given',
                                        data=juice,
                                        timestamps=trial_times_all))
        # add trials:
        for col_details in task_data+task_times_data:
            col_det = dict(name=col_details['name'],description=col_details['description'])
            if 'index' in col_details:
                col_det.update(index=col_details['index'])
            nwbfile.add_trial_column(**col_det)
        for trial_no in range(self.mat_extractor._no_trials):
            col_details_dict = {
                i["name"]: i["data"][trial_no]
                for i in task_data+task_times_data
            }
            col_details_dict.update(
                start_time=trial_times[trial_no][0],
                stop_time=trial_times[trial_no][-1],
                timeseries=spatial_series_list,
            )
            nwbfile.add_trial(**col_details_dict)

        # # add units:
        # for no,unit_sp_times in enumerate(spike_times):
        #     nwbfile.add_unit(
        #         spike_times=unit_sp_times,
        #         electrodes=no,
        #         electrode_group=list(nwbfile.electrode_groups.values())[round(192/no)],
        #         obs_intervals=trial_times[no])