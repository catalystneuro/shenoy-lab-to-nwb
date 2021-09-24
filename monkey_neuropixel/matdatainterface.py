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
from ..center_out_task.matdatainterface import COutMatDataInterface
PathType = Union[str, Path]


class NpxMatDataInterface(COutMatDataInterface):
    def __init__(self, filename: PathType):
        super().__init__(filename = filename)

    @classmethod
    def get_source_schema(cls):
        return get_schema_from_method_signature(cls.__init__)

    def get_metadata(self):
        metadata = super(NpxMatDataInterface, self).get_metadata()
        _ = metadata.pop('NWBFile')
        metadata['Behavior']['Position'] = [
                    dict(name="hand_speed", reference_frame="screen center"),
                    dict(name="hand_position", reference_frame="screen center"),
                ]
        return metadata

    def run_conversion(self, nwbfile: NWBFile, metadata: dict, **kwargs):
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
        spatial_series_list = []
        timestamps = beh_dict.pop('times')
        for beh, args in beh_dict.items():
            args_ = dict(
                timestamps=timestamps['data'],
                reference_frame="screen center").update(args)
            spatial_series_list.append(position_container.create_spatial_series(name=beh,**args_))
        beh_mod.add(position_container)

        # add trials:
        task_dict.update(events_dict)
        for name, args in task_dict.items():
            col_det = dict(name=name,description=args['description'])
            nwbfile.add_trial_column(**col_det)
        for trial_no in range(self.mat_extractor._no_trials):
            col_details_dict = {
                i: args["data"][trial_no]
                for i,args in task_dict.items()
            }
            col_details_dict.update(
                start_time=start_times[trial_no],
                stop_time=stop_times[trial_no],
                timeseries=spatial_series_list,
                id=trial_ids[trial_no]
            )
            nwbfile.add_trial(**col_details_dict)

        if len(nwbfile.devices)==0:
            nwbfile.create_device(name="NeuroPixels", description='mouse version of neuropixels implanted in monkeys')
        if len(nwbfile.electrode_groups)==0:
            # add electrdoe groups:
            elec_gp_name = "ElectrodeGroup_1"
            nwbfile.create_electrode_group(name=elec_gp_name,
                                           description="desc",
                                           location="location",
                                           device=nwbfile.devices["NeuroPixels"])
        # add units:
        args_all = dict()
        for name, custom_arg in custom_unit_args.items():
            nwbfile.add_unit_column(name=name, description=custom_arg['description'])
            args_all[name]=custom_arg['data']
        for name, def_arg in default_unit_args.items():
            args_all[name]=def_arg['data']
        for no,unit_sp_times in enumerate(spike_times_list):
            args = dict()
            for key,value in args_all.items():
                args[key] = value[no]
            args.update(spike_times=unit_sp_times,
                        electrode_group=list(nwbfile.electrode_groups.values())[0],
                        obs_intervals=obs_intervals)
            nwbfile.add_unit(**args)