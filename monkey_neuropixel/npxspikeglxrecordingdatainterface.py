from pathlib import Path
from typing import Union
from nwb_conversion_tools import SpikeGLXRecordingInterface

PathType = Union[str, Path]


class NpxSpikeGLXRecordingInterface(SpikeGLXRecordingInterface):

    def get_metadata(self):
        metadata = super().get_metadata()
        metadata["Ecephys"]["Device"] = [dict(name='Neuropixels',
                                              description='NHP version of neuropixels probe',
                                              manufacturer='Imec')]
        return metadata