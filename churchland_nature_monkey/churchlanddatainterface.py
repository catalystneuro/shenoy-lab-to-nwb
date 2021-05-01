from nwb_conversion_tools import BlackrockRecordingExtractorInterface, NWBConverter
from .matdatainterface import MatDataInterface
from .multiblackrockrecordingdatainterface import MultiBlackRockRecordingDatainterface
import warnings
import jsonschema
from pathlib import Path
import uuid
import pytz
from datetime import datetime


class ChurchlandDataInterface(NWBConverter):
    data_interface_classes = dict(
        MatDataInterface=MatDataInterface,
        MultiBlackRockRecordingDatainterface=MultiBlackRockRecordingDatainterface,
    )

    def __init__(self, source_folder: Path):
        """
        Converts mat and .nsx data associated with Churchland(2012) monkey experiments with Utah
        multielectrode implants.
        Parameters
        ----------
        source_folder : str
            path to folder containing .mat and .nsx files for the whole session
        """
        self.source_folder = Path(source_folder)
        nsx_files_list = list(source_folder.glob('**/*.ns2'))
        mat_files_list = list(source_folder.glob('**/RC*.mat'))
        assert len(nsx_files_list)>0,'no nsx files found in the folder provided'
        assert len(mat_files_list)>0,'no .mat RC file found in the folder provided'
        source_data_dict = dict(MultiBlackRockRecordingDatainterface=dict(filename=str(nsx_files_list[0].parent)),
                                MatDataInterface=dict(file_path=str(mat_files_list[0])))
        super().__init__(source_data_dict)

    def get_metadata(self):
        metadata_base = super().get_metadata()
        session_date = pytz.timezone('US/Pacific').localize(datetime.strptime(self.source_folder.name, '%Y-%m-%d'))
        metadata_base['NWBFile']=dict(
            session_description='', identifier=str(uuid.uuid4()),
            session_start_time=session_date, experimenter=['Matthew T. Kaufman', 'Mark M. Churchland'],
            experiment_description='', institution='Stanford University',
            related_publications='10.1038/nature11129'
            ),
        metadata_base['Subject'] = dict(sex='M', species='Macaca mulatta', subject_id=self.source_folder.parent.name
        )