import uuid

from nwb_conversion_tools import NWBConverter
from nwb_conversion_tools.utils.json_schema import dict_deep_update

from .coutblackrockiodatainterface import COutBlackrockIODataInterface
from .coutmoviedatainterface import CoutMoviedataInterface
from .matdatainterface import COutMatDataInterface


class COutNWBConverter(NWBConverter):
    data_interface_classes = dict(
        A1=COutBlackrockIODataInterface,
        B1=COutBlackrockIODataInterface,
        A2=COutBlackrockIODataInterface,
        B2=COutBlackrockIODataInterface,
        A3=COutBlackrockIODataInterface,
        B3=COutBlackrockIODataInterface,
        A4=COutBlackrockIODataInterface,
        B4=COutBlackrockIODataInterface,
        Mat=COutMatDataInterface,
        Movie=CoutMoviedataInterface,
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
            experimenter=["Nir Even-Chen", "Blue Scheffer"],
            experiment_description="center out task for Monkeys",
            institution="Stanford University",
            related_publications="10.1371/journal.pcbi.1006808",
        )
        metadata_base = dict_deep_update(metadata_base, super().get_metadata())
        return metadata_base
