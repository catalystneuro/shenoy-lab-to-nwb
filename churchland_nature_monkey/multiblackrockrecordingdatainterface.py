from nwb_conversion_tools import BlackrockRecordingExtractorInterface
from spikeextractors import BlackrockRecordingExtractor, \
    MultiRecordingChannelExtractor, MultiRecordingTimeExtractor, NwbRecordingExtractor
from pathlib import Path
from pynwb.file import NWBFile
from typing import Union

PathType = Union[str, Path, None]


class MultiBlackRockRecordingDatainterface(BlackrockRecordingExtractorInterface):

    def __init__(self, filename):
        self.nsx_loc = Path(filename)
        nsx_files_list = [str(i) for i in self.nsx_loc.glob('**/*.ns2')]
        nsx_files_stems = [i.stem.strip('datafile') for i in self.nsx_loc.glob('**/*.ns2')]
        super().__init__(filename=nsx_files_list[0])
        no_segments = 2
        raw_files_names = []
        for seg_num in range(no_segments):
            seg_no = seg_num + 1
            if f'A00{seg_no}' in nsx_files_stems:
                assert f'B00{seg_no}' in nsx_files_stems
                raw_files_names.append([f'A00{seg_no}',f'B00{seg_no}'])
        multi_time_se = []
        for no, data_part in enumerate(raw_files_names):
            multi_channel_se = []
            for elec_no, electrode in enumerate((data_part)):
                nev_file = self.nsx_loc/f'datafile{electrode}.nev'
                print(f'reading: {nev_file.name}')
                multi_channel_se.append(BlackrockRecordingExtractor(str(nev_file)))
            multi_time_se.append(MultiRecordingChannelExtractor(multi_channel_se))
        self.recording_extractor = MultiRecordingTimeExtractor(multi_time_se)

    @classmethod
    def get_source_schema(cls):
        base_source_schema = super().get_source_schema()
        base_source_schema['properties']['filename']['format'] = 'folder'
        return base_source_schema

    def run_conversion(self, nwbfile: NWBFile=None, metadata: dict = None, save_path: PathType = None, **kwargs):
        if nwbfile is None and save_path is None:
            raise Exception('enter one of nwbfile(open file object) or a save_path for nwbfile on disc')
        if save_path is None:
            NwbRecordingExtractor.add_electrical_series(recording=self.recording_extractor,
                                                        nwbfile=nwbfile,
                                                        metadata=metadata,
                                                        write_as_lfp=True)
        else:
            NwbRecordingExtractor.write_recording(recording=self.recording_extractor,
                                                  save_path=save_path)