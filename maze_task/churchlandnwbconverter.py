from nwb_conversion_tools import NWBConverter
from shenoymatdatainterface import ShenoyMatDataInterface
from shenoyblackrockrecordingdatainterface import ShenoyBlackRockRecordingDataInterface
from pathlib import Path
import uuid
import pytz
from datetime import datetime


class ChurchlandNWBConverter(NWBConverter):
    data_interface_classes = dict(
        A1=ShenoyBlackRockRecordingDataInterface,
        B1=ShenoyBlackRockRecordingDataInterface,
        A2=ShenoyBlackRockRecordingDataInterface,
        B2=ShenoyBlackRockRecordingDataInterface,
        A3=ShenoyBlackRockRecordingDataInterface,
        B3=ShenoyBlackRockRecordingDataInterface,
        A4=ShenoyBlackRockRecordingDataInterface,
        B4=ShenoyBlackRockRecordingDataInterface,
        Mat=ShenoyMatDataInterface,
    )

    def __init__(self, source_data):
        """
        Converts mat and .nsx data associated with Churchland(2012) monkey experiments with Utah
        multielectrode implants.
        Parameters
        ----------
        source_folder : dict
        """
        self.subject_name = source_data.get("subject_name", "Jenkins")
        self.session_date = source_data.get("date", datetime.now())
        super().__init__(source_data)

    @classmethod
    def get_source_schema(cls):
        base_schema = super().get_source_schema()
        base_schema["additionalProperties"] = True
        base_schema["properties"].update(subject_name=dict(type="string"))
        return base_schema

    def get_metadata(self):
        metadata_base = super().get_metadata()
        metadata_base["NWBFile"] = dict(
            session_description="",
            identifier=str(uuid.uuid4()),
            session_start_time=datetime.isoformat(self.session_date),
            experimenter=["Matthew T. Kaufman", "Mark M. Churchland"],
            experiment_description="",
            institution="Stanford University",
            related_publications=[
                "10.1038/nature11129",
                "10.1152/jn.00892.2011",
                "10.1038/nn.3643",
                "10.1038/nn.4042",
                "10.1146/annurev-neuro-062111-150509",
                "10.7554/eLife.04677"""
                "10.1523/ENEURO.0085-16.2016",
                "10.1038/s41592-018-0109-9"
            ],
        )
        metadata_base["Subject"] = dict(
            sex="M", species="Macaca mulatta", subject_id=self.subject_name
        )
        return metadata_base
