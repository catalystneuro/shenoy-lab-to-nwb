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


class ShenoyBlackRockRecordingDataInterface(BlackrockRecordingExtractorInterface):

    def __init__(self, filename):
        self.nsx_loc = Path(filename)
        super().__init__(filename=self.nsx_loc)
        if self.nsx_loc.name[0] == 'B':
            self._group_name = ['M1 array']
            self.recording_extractor._channel_ids += 96
        else:
            self._group_name = ['PMd array']

    def get_metadata(self):
        metadata = super().get_metadata()
        metadata['Ecephys']['ElectricalSeries'].update(
            name=self.nsx_loc.name,
            description=f'LFP signal for array{self.nsx_loc.name[0]} '
                        f'segment{self.nsx_loc.name[-1]}')
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
        metadata['Electrodes'] = [dict(name='filtering',
                                       data=['1000Hz']*96),
                                  dict(name='group_name',
                                       data=self._group_name * 96)
                                  ]

        return metadata
