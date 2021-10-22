from datetime import datetime
from pathlib import Path
from typing import Union
import json
import pynwb
from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils.json_schema import (
    get_base_schema, get_schema_from_hdmf_class, get_schema_for_NWBFile)
from pynwb import NWBFile, TimeSeries
from pynwb.behavior import Position, SpatialSeries, BehavioralTimeSeries

from .matextractor import MatDataExtractor

PathType = Union[str, Path]


class NpxMatDataInterface(BaseDataInterface):
    def __init__(self, filename: PathType):
        super().__init__(filename=filename)
        self.filename = Path(filename)
        assert self.filename.suffix == ".mat", "file_path should be a .mat"
        assert self.filename.exists(), "file_path does not exist"
        with open("data/brain_location_map.json", "r") as io:
            self.brain_location_map = json.load(io)
        self.brain_location = self.brain_location_map.get(self.filename.stem.split('.')[0], "PMd")
        self.mat_extractor = MatDataExtractor(self.filename)

    def get_metadata_schema(self):
        metadata_schema = get_base_schema()
        metadata_schema["required"] = ["Behavior", "Subject", "NWBFile",
                                       "Ecephys"]
        metadata_schema["properties"] = dict()
        metadata_schema["properties"]["Behavior"] = get_base_schema()
        metadata_schema["properties"]["NWBFile"] = get_schema_for_NWBFile()

        metadata_schema["properties"]["Behavior"]["properties"] = dict(
            Position=dict(
                type="array",
                items=get_schema_from_hdmf_class(SpatialSeries)
            ),
            BehavioralTimeSeries=dict(
                type="array",
                items=get_schema_from_hdmf_class(TimeSeries)
            )
        )
        return metadata_schema

    def get_metadata(self):
        with open("data/metadata.json", "r") as io:
            metadata = json.load(io)
        metadata["NWBFile"].update(
            session_start_time=str(datetime.strptime(self.filename.stem.split('.')[0][1:], "%Y%m%d")))
        metadata["Subject"].update(
            subject_id=self.mat_extractor.subject_name
        )
        metadata["Behavior"] = dict(
            Position=[
                dict(name="hand_position", reference_frame="screen center", description="hand position x,y,z")],
            BehavioralTimeSeries=[dict(name="hand_speed", unit="m/s", description="hand speed in x,y,z")],
        )
        return metadata

    def run_conversion(self, nwbfile: NWBFile, metadata: dict, **kwargs):
        metadata_comp = self.get_metadata()
        metadata_comp.update(metadata)
        assert isinstance(nwbfile, NWBFile), "'nwbfile' should be of type pynwb.NWBFile"
        start_times, stop_times = self.mat_extractor.get_trial_times()
        events_dict = self.mat_extractor.get_trial_epochs()
        beh_dict = self.mat_extractor.get_behavior_movement()
        trial_ids = self.mat_extractor.get_trial_ids()
        task_dict = self.mat_extractor.get_task_details()
        spike_times_list = self.mat_extractor.extract_unit_spike_times()
        default_unit_args, custom_unit_args = self.mat_extractor.extract_unit_details()
        obs_intervals = [[start_times[i], stop_times[i]] for i in range(len(start_times))]
        # add behavior:
        beh_mod = nwbfile.create_processing_module(
            "behavior", "contains monkey movement data"
        )
        position_container = Position()
        beh_ts_container = BehavioralTimeSeries()
        spatial_series_list = []
        timestamps = beh_dict.pop('times')
        for name, args in beh_dict.items():
            args_ = dict(timestamps=timestamps['data'], **args)
            if 'position' in name:
                args_.update(metadata_comp['Behavior']['Position'][0])
                spatial_series_list.append(position_container.create_spatial_series(**args_))
            else:
                args_.update(metadata_comp['Behavior']['BehavioralTimeSeries'][0])
                beh_ts_container.create_timeseries(**args_)
        beh_mod.add(position_container)
        beh_mod.add(beh_ts_container)

        # add trials:
        task_dict.update(events_dict)
        for name, args in task_dict.items():
            col_det = dict(name=name, description=args['description'])
            nwbfile.add_trial_column(**col_det)
        for trial_no in range(self.mat_extractor._no_trials):
            col_details_dict = {
                key: args["data"][trial_no]
                for key, args in task_dict.items()
            }
            col_details_dict.update(
                start_time=start_times[trial_no],
                stop_time=stop_times[trial_no],
                timeseries=spatial_series_list,
                id=int(trial_ids[trial_no])
            )
            nwbfile.add_trial(**col_details_dict)

        if len(nwbfile.devices) == 0:
            nwbfile.create_device(**metadata_comp["Ecephys"]["Device"][0])
        if len(nwbfile.electrode_groups) == 0:
            # add electrdoe groups:
            args = metadata_comp["Ecephys"]["ElectrodeGroup"][0]
            nwbfile.create_electrode_group(device=nwbfile.devices[args.pop('device')],
                                           **args)
        # add units:
        args_all = dict()
        for name, custom_arg in custom_unit_args.items():
            nwbfile.add_unit_column(name=name, description=custom_arg['description'])
            args_all[name] = custom_arg['data']
        for name, def_arg in default_unit_args.items():
            args_all[name] = def_arg['data']
        for no, unit_sp_times in enumerate(spike_times_list):
            args = dict()
            for key, value in args_all.items():
                args[key] = int(value[no]) if key == 'id' else value[no]
            args.update(spike_times=unit_sp_times,
                        electrode_group=list(nwbfile.electrode_groups.values())[0],
                        obs_intervals=obs_intervals)
            nwbfile.add_unit(**args)
