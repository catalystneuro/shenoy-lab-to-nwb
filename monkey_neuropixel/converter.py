from nwb_conversion_tools import NWBConverter, SpikeGLXRecordingInterface
from monkey_neuropixel.matdatainterface import NpxMatDataInterface
from pathlib import Path
from nwb_conversion_tools.utils.json_schema import dict_deep_update
import uuid


class NpxNWBConverter(NWBConverter):
    data_interface_classes = dict(
        Mat=NpxMatDataInterface,
        Sgx=SpikeGLXRecordingInterface
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
            experiment_description="center out task for Monkeys with mouse version of neuropixels",
            institution="Stanford University",
            related_publications="",
        )
        metadata_base = dict_deep_update(metadata_base,super().get_metadata())
        return metadata_base