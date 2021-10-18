from nwb_conversion_tools import NWBConverter, SpikeGLXRecordingInterface
from monkey_neuropixel.matdatainterface import NpxMatDataInterface
from pathlib import Path
from nwb_conversion_tools.utils.json_schema import dict_deep_update, FilePathType
import uuid
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
        _ = metadata["Ecephys"].pop["ElectrodeGroup"]
        _ = metadata["Ecephys"].pop["Device"]
        return metadata

class NpxNWBConverter(NWBConverter):
    data_interface_classes = dict(
        Mat=NpxMatDataInterface,
        Sgx=ShenoySpikeGLXRecordingInterface
    )

    def __init__(self, source_data):
        """
        Converts mat and .nsx data associated with Churchland(2012) monkey experiments with Utah
        multielectrode implants.
        Parameters
        ----------
        source_folder : dict
        """
        super().__init__(source_data)


    def get_metadata(self):
        metadata_base = dict()
        metadata_base["NWBFile"] = dict(
            session_description="",
            identifier=str(uuid.uuid4()),
            experimenter=["Daniel O'Shea"],
            institution="Stanford University",
            related_publications="",
        )
        metadata_base = dict_deep_update(metadata_base,super().get_metadata())
        return metadata_base