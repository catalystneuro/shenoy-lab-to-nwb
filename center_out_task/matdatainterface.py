from pathlib import Path
import numpy as np
from typing import Union
from nwb_conversion_tools import NWBConverter
from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils.json_schema import (
    get_base_schema, get_schema_from_hdmf_class, get_schema_for_NWBFile, get_schema_from_method_signature)
from pynwb import NWBFile, TimeSeries
from pynwb.epoch import TimeIntervals
from pynwb.behavior import Position, SpatialSeries
from pynwb.misc import Units
from .matextractor import MatDataExtractor
from pynwb.base import DynamicTable
from pynwb.file import Subject

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
        return get_schema_from_method_signature(cls.__init__)

    @staticmethod
    def _convert_schema_object_to_array(schema_to_convert):
        base_schema = get_base_schema()
        base_schema.update(type="array")
        _ = base_schema.pop("properties")
        base_schema["items"] = schema_to_convert
        return base_schema

    def get_metadata_schema(self):
        metadata_schema = get_base_schema()
        metadata_schema["required"] = ["Behavior", "Intervals",
                                       "Units", "Subject", "NWBFile"]
        metadata_schema["properties"] = dict()
        metadata_schema["properties"]["Behavior"] = get_base_schema()
        metadata_schema["properties"]["Intervals"] = get_base_schema()
        metadata_schema["properties"]["NWBFile"] = get_schema_for_NWBFile()
        metadata_schema["properties"]["Intervals"] = get_schema_from_hdmf_class(TimeIntervals)

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
            Subject=dict(
                sex="M", species="Macaca mulatta",
                subject_id=self.mat_extractor.subject_name
                        ),
            NWBFile=dict(
                session_start_time=str(self.mat_extractor.session_start)),
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
        beh_pos = self.mat_extractor.extract_behavioral_position()
        stim_pos = self.mat_extractor.extract_stimulus()
        trial_times = self.mat_extractor.get_trial_times()
        trial_times_all = np.concatenate(trial_times)
        task_data = self.mat_extractor.extract_task_data()
        task_times_data = self.mat_extractor.extract_task_times()
        spike_times = self.mat_extractor.extract_unit_spike_times()

        # add behavior:
        beh_mod = nwbfile.create_processing_module(
            "behavior", "contains monkey movement data"
        )
        position_container = Position()
        spatial_series_list = []
        for beh in beh_pos:
            args = beh.update(
                timestamps=trial_times_all,
                reference_frame="screen center",
                conversion=np.nan)
            spatial_series_list.append(position_container.create_spatial_series(**args))
        beh_mod.add(position_container)
        #add stimulus:
        nwbfile.add_stimulus(TimeSeries(name='juice_reward',
                                        description='1 is when reward was presented',
                                        data=stim_pos,
                                        timestamps=trial_times_all,
                                        unit='n.a.'))
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
        #add electrdoe groups:
        nwbfile.create_device(name="Utah Electrode",description='192 channels microelectrode array')
        nwbfile.create_electrode_group(name="1",
                description="array corresponding to device implanted at PMd",
                location="Caudal, dorsal Pre-motor cortex, Left hemisphere",
                device=nwbfile.devices["Utah Electrode"])
        nwbfile.create_electrode_group(name="2",
                description="array corresponding to device implanted at M1",
                location="M1 in Motor Cortex, left hemisphere",
                device=nwbfile.devices["Utah Electrode"])
        # add units:
        for no,unit_sp_times in enumerate(spike_times):
            elec_group = 1 if no>95 else 0
            nwbfile.add_unit(
                spike_times=unit_sp_times,
                electrodes=[no],
                electrode_group=list(nwbfile.electrode_groups.values())[elec_group],
                obs_intervals=np.array([trial_times[0][0],trial_times[-1][-1]])[np.newaxis,:])