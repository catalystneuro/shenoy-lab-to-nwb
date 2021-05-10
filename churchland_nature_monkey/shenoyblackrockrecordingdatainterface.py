from nwb_conversion_tools import BlackrockRecordingExtractorInterface

from pathlib import Path
from typing import Union

PathType = Union[str, Path, None]


class ShenoyBlackRockRecordingDataInterface(BlackrockRecordingExtractorInterface):

    def __init__(self, filename):
        self.nsx_loc = Path(filename)
        super().__init__(filename=filename)
        if 'B' in self.nsx_loc.name:
            self._group_name = ['M1 array']
            self.recording_extractor._channel_ids = [i + 96 for i in self.recording_extractor._channel_ids]
        else:
            self._group_name = ['PMd array']
        self.recording_extractor.clear_channels_property('name')

    def get_metadata(self):
        metadata = dict()
        metadata['Ecephys'] = dict(
            Device=[dict(
                name='Device_ecephys',
                description='no description'
            )],
            ElectrodeGroup=[],
        )
        metadata['Ecephys'].update(
            {f'ElectricalSeries{self.nsx_loc.stem[-4:]}': dict(
                name=self.nsx_loc.stem[-4:],
                description=f'LFP signal for array{self.nsx_loc.stem[8]} segment {self.nsx_loc.stem[-1]}')})
        metadata['Ecephys']['Device'] = [dict(name='Utah Array(PMd)',
                                              description='96 channel utah array',
                                              manufacturer='BlackRock Microsystems'),
                                         dict(name='Utah Array(M1)',
                                              description='96 channel utah array',
                                              manufacturer='BlackRock Microsystems')]
        metadata['Ecephys']['ElectrodeGroup'] = [dict(name='PMd array',
                                                      description='',
                                                      location='Caudal, dorsal Pre-motor cortex, Left hemisphere',
                                                      device_name='Utah Array(PMd)'),
                                                 dict(name='M1 array',
                                                      description='',
                                                      location='M1 in Motor Cortex, left hemisphere',
                                                      device_name='Utah Array(M1)')]
        metadata['Ecephys']['Electrodes'] = [dict(name='filtering',
                                                  description='filtering',
                                                  data=['1000Hz']*96),
                                             dict(name='group_name',
                                                  description='electrode group name',
                                                  data=self._group_name*96)
                                             ]

        return metadata
