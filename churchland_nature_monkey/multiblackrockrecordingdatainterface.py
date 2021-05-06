import numpy as np

from nwb_conversion_tools import BlackrockRecordingExtractorInterface
from spikeextractors import BlackrockRecordingExtractor, \
    MultiRecordingChannelExtractor, MultiRecordingTimeExtractor, NwbRecordingExtractor
from pathlib import Path
from pynwb.file import NWBFile
from typing import Union
from nwb_conversion_tools import NWBConverter
from nwb_conversion_tools.json_schema_utils import get_base_schema


PathType = Union[str, Path, None]


class MultiBlackRockRecordingDatainterface(BlackrockRecordingExtractorInterface):

    def __init__(self, filename):
        self.nsx_loc = Path(filename)
        nsx_files_list = [str(i) for i in self.nsx_loc.glob('**/*.ns2')]
        files_stems = [i.stem.strip('datafile') for i in self.nsx_loc.glob('**/*.ns2')]
        super().__init__(filename=nsx_files_list[0])
        no_segments = 2
        self.raw_files_names = []
        for seg_num in range(no_segments):
            seg_no = seg_num + 1
            if f'A00{seg_no}' in files_stems:
                assert f'B00{seg_no}' in files_stems
                self.raw_files_names.append([f'A00{seg_no}',f'B00{seg_no}'])
        self.recording_extractor_list = []
        for no, data_part in enumerate(self.raw_files_names):
            for elec_no, electrode in enumerate((data_part)):
                nev_file = self.nsx_loc/f'datafile{electrode}.nev'
                print(f'reading: {nev_file.name}')
                rx = BlackrockRecordingExtractor(str(nev_file))
                if elec_no==1:
                    rx._channel_ids = list(range(97,193))
                self.recording_extractor_list.append(rx)

    @classmethod
    def get_source_schema(cls):
        base_source_schema = super().get_source_schema()
        base_source_schema['properties']['filename']['format'] = 'folder'
        return base_source_schema

    def get_metadata_schema(self):
        metadata_schema = NWBConverter.get_metadata_schema()
        metadata_schema['required'] = ['Ecephys']
        metadata_schema['properties']['Ecephys'] = get_base_schema()
        metadata_schema['properties']['Ecephys']['required'] = ['LFPElectricalSeries']
        return metadata_schema

    def get_metadata(self):
        file_names=[]
        for j in self.raw_files_names:
            file_names.extend(j)
        metadata = dict(
            Ecephys=dict(ElectricalSeries=[{'name': i,
                                            'description': f'LFP signal for array{i[0]}, '
                                                           f'segment{i[-1]}'} for i in file_names]))
        return metadata

    def run_conversion(self, nwbfile: NWBFile, metadata: dict, **kwargs):
        for no, extractor in enumerate(self.recording_extractor_list):
            metadata_loop = dict(
                Ecephys=dict(ElectricalSeries=
                            metadata['Ecephys']['ElectricalSeries'][no]))
            extractor._times = np.array([np.nan])
            NwbRecordingExtractor.add_electrical_series(recording=extractor,
                                                        nwbfile=nwbfile,
                                                        metadata=metadata_loop,
                                                        write_as_lfp=False)