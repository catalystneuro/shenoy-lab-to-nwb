from nwb_conversion_tools import NWBConverter
from .shenoymatdatainterface import ShenoyMatDataInterface
from .shenoyblackrockrecordingdatainterface import ShenoyBlackRockRecordingDataInterface
from pathlib import Path
import uuid
import pytz
from datetime import datetime


class ChurchlandNWBConverter(NWBConverter):
    data_interface_classes = dict(
        Mat=ShenoyMatDataInterface,
        A0=ShenoyBlackRockRecordingDataInterface,
        B0=ShenoyBlackRockRecordingDataInterface,
        A1=ShenoyBlackRockRecordingDataInterface,
        B1=ShenoyBlackRockRecordingDataInterface,
    )

    def __init__(self, source_data, subject_name):
        """
        Converts mat and .nsx data associated with Churchland(2012) monkey experiments with Utah
        multielectrode implants.
        Parameters
        ----------
        source_folder : dict
        """
        self.subject_name = subject_name
        super().__init__(source_data)

    def get_metadata(self):
        metadata_base = super().get_metadata()
        session_date = pytz.timezone('US/Pacific').localize(datetime.strptime('2009'+self.source_folder.name, '%Y%m%d'))
        metadata_base['NWBFile']=dict(
            session_description='', identifier=str(uuid.uuid4()),
            session_start_time=session_date, experimenter=['Matthew T. Kaufman', 'Mark M. Churchland'],
            experiment_description='', institution='Stanford University',
            related_publications='10.1038/nature11129'
            )
        metadata_base['Subject'] = dict(sex='M', species='Macaca mulatta',
                                        subject_id=self.subject_name
        )
        return metadata_base