from pathlib import Path
from typing import Union
from nwb_conversion_tools import BlackrockRecordingExtractorInterface

PathType = Union[str, Path]


class COutBlackrockIODataInterface(BlackrockRecordingExtractorInterface):

    def __init__(self, nsx_override: PathType, filename: PathType = ''):
        self.nsx_loc = Path(nsx_override)
        super().__init__(filename=filename, nsx_override=nsx_override)
        if "M1" in self.nsx_loc.parent.name:
            self._region = 'M1 Motor Cortex'
            self.recording_extractor.set_channel_groups([1]*96)
        elif "PMd" in self.nsx_loc.parent.name:
            self._region = 'Pre-Motor Cortex, dorsal'
            self.recording_extractor.set_channel_groups([2]*96)
            self.recording_extractor._channel_ids = [
                i + 96 for i in self.recording_extractor._channel_ids
            ]
        self.recording_extractor.clear_channels_property("name")
        for chan_id in self.recording_extractor.get_channel_ids():
            self.recording_extractor.set_channel_property(chan_id, 'filtering', '2000Hz')
            self.recording_extractor.set_channel_property(chan_id, 'brain_area', self._region)

    def get_metadata_schema(self):
        metadata_schema = super().get_metadata_schema()
        metadata_schema['properties']['Ecephys']['additionalProperties'] = True
        return metadata_schema

    def get_metadata(self):
        metadata = dict(
            Ecephys=dict(
                Device=[dict(name="Device_ecephys", description="no description")],
                ElectrodeGroup=[],
            )
        )
        ephys_name = self.nsx_loc.parent.stem+'_'+self.nsx_loc.stem[-1]
        metadata["Ecephys"].update(
            {
                f"ElectricalSeries_{ephys_name}": dict(
                    name=ephys_name,
                    description=f"LFP signal for array {ephys_name}, segment {self.nsx_loc.stem[-1]}"
                                f"data for both arrays A,B in the same segment should be, but is not of the same time length"
                                f"and cannot be synced due to lack of time stamps. Ignore the starting times.",
                )
            }
        )
        metadata["Ecephys"]["Device"] = [
            dict(
                name="Utah Array(PMd)",
                description="96 channel utah array",
                manufacturer="BlackRock Microsystems",
            ),
            dict(
                name="Utah Array(M1)",
                description="96 channel utah array",
                manufacturer="BlackRock Microsystems",
            ),
        ]
        metadata["Ecephys"]["ElectrodeGroup"] = [
            dict(
                name="2",
                description="array corresponding to device implanted at PMd",
                location="Caudal, dorsal Pre-motor cortex, Left hemisphere",
                device="Utah Array(PMd)",
            ),
            dict(
                name="1",
                description="array corresponding to device implanted at M1",
                location="M1 in Motor Cortex, left hemisphere",
                device="Utah Array(M1)",
            ),
        ]

        return metadata