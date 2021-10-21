from datetime import datetime
from pathlib import Path
from typing import Union

import pynwb
from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils.json_schema import (
    get_base_schema, get_schema_from_hdmf_class, get_schema_for_NWBFile)
from pynwb import NWBFile, TimeSeries
from pynwb.behavior import Position, SpatialSeries, BehavioralTimeSeries

from .matextractor import MatDataExtractor

PathType = Union[str, Path]

brain_location_map = {
    "P20180323": "M1",
    "P20180327": "M1",
    "P20180607": "PMd",
    "P20180608": "PMd",
    "P20180609": "PMd",
    "P20180612": "PMd",
    "P20180613": "PMd",
    "P20180614": "PMd",
    "P20180615": "PMd",
    "P20180620": "M1",
    "P20180622": "M1",
    "P20180704": "M1",
    "P20180705": "M1",
    "P20180707": "M1",
    "P20180710": "PMd",
    "P20180711": "PMd",
    "V20180814": "PMd",
    "V20180815": "PMd",
    "V20180817": "PMd",
    "V20180818": "PMd",
    "V20180819": "PMd",
    "V20180820": "PMd",
    "V20180821": "M1",
    "V20180822": "M1",
    "V20180823": "M1",
    "V20180919": "PMd",
    "V20180920": "PMd",
    "V20180921": "PMd",
    "V20180922": "PMd",
    "V20180923": "PMd",
    "V20180925": "PMd",
    "V20180926": "PMd",
    "V20180927": "M1",
    "V20180928": "M1",
    "V20181128": "PMd",
    "V20181204": "PMd",
}


class NpxMatDataInterface(BaseDataInterface):
    def __init__(self, filename: PathType):
        super().__init__(filename=filename)
        self.filename = Path(filename)
        assert self.filename.suffix == ".mat", "file_path should be a .mat"
        assert self.filename.exists(), "file_path does not exist"
        self.brain_location = brain_location_map.get(self.filename.stem.split('.')[0], "PMd")
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
        metadata = dict(
            NWBFile=dict(
                session_start_time=str(datetime.strptime(self.filename.stem.split('.')[0][1:], "%Y%m%d")),
                experiment_description="Monkeys were trained to perform an instructed-delay reaching task in order "
                                       "to drive task-related neural activity in primary motor and dorsal premotor "
                                       "cortex where our electrodes were located. We trained the monkey to use his "
                                       "right hand to grasp and translate a custom 3D printed handle (Shapeways, Inc.) "
                                       "attached to a haptic feedback device (Delta.3, Force Dimension, Inc.). "
                                       "The monkey was trained to perform a delayed reaching task by moving the "
                                       "haptic device cursor towards green rectangular targets displayed on the "
                                       "screen. Successful completion of each movement triggered a juice reward."
            ),
            Subject=dict(
                sex="M", species="Macaca mulatta",
                subject_id=self.mat_extractor.subject_name
            ),
            Behavior=dict(
                Position=[
                    dict(name="hand_position", reference_frame="screen center", description="hand position x,y,z")],
                BehavioralTimeSeries=[dict(name="hand_speed", unit="m/s", description="hand speed in x,y,z")],
            )
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
