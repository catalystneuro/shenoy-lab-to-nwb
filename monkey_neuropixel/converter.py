from nwb_conversion_tools import NWBConverter, SpikeGLXRecordingInterface
from monkey_neuropixel.matdatainterface import NpxMatDataInterface
from pathlib import Path
from nwb_conversion_tools.utils.json_schema import dict_deep_update, FilePathType
import uuid
import json
from typing import Optional


class ShenoySpikeGLXRecordingInterface(SpikeGLXRecordingInterface):

    def __init__(self, file_path: FilePathType, stub_test: Optional[bool] = False):
        super(ShenoySpikeGLXRecordingInterface, self). __init__(file_path=file_path, stub_test=stub_test)
        for ch in self.recording_extractor.get_channel_ids():
            self.recording_extractor.set_channel_property(
                channel_id=ch, property_name="group_name", value="Probe0"
            )

    def get_metadata(self):
        metadata = super(ShenoySpikeGLXRecordingInterface, self).get_metadata()
        with open("data/metadata.json","r") as io:
            metadata_lab  = json.load(io)
        metadata["Ecephys"] = dict_deep_update(metadata["Ecephys"], metadata_lab["Ecephys"])
        return metadata

class NpxNWBConverter(NWBConverter):
    data_interface_classes = dict(
        Sgx=ShenoySpikeGLXRecordingInterface,
        Mat=NpxMatDataInterface,
    )

    def get_metadata(self):
        metadata = super(NpxNWBConverter, self).get_metadata()
        metadata["NWBFile"].update(
            session_description="",
            identifier=str(uuid.uuid4()),
            experimenter=["Daniel O'Shea"],
            institution="Stanford University",
            # related_publications="",
        )
        return metadata