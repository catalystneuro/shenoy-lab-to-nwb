from nwb_conversion_tools import BlackrockRecordingExtractorInterface
from pathlib import Path
from typing import Union

PathType = Union[str, Path]


class ShenoyBlackRockRecordingDataInterface(BlackrockRecordingExtractorInterface):
    def __init__(self, filename: PathType):
        self.nsx_loc = Path(filename)
        super().__init__(filename=filename)
        if "B" in self.nsx_loc.name:
            self._group_name = ["M1 array"]
            self._region = ['M1 Motor Cortex']
            self.recording_extractor._channel_ids = [
                i + 96 for i in self.recording_extractor._channel_ids
            ]
            self.recording_extractor.set_channel_groups([2]*96)
        else:
            self._group_name = ["PMd array"]
            self._region = ['Pre-Motor Cortex, dorsal']
            self.recording_extractor.set_channel_groups([1]*96)
        self.recording_extractor.clear_channels_property("name")

    def get_metadata(self):
        metadata = dict(
            Ecephys=dict(
                Device=[dict(name="Device_ecephys", description="no description")],
                ElectrodeGroup=[],
            )
        )
        metadata["Ecephys"].update(
            {
                f"ElectricalSeries{self.nsx_loc.stem[-4:]}": dict(
                    name=self.nsx_loc.stem[-4:],
                    description=f"LFP signal for array {self.nsx_loc.stem[8]}, segment {self.nsx_loc.stem[-1]}"
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
                name="1",
                description="array corresponding to device implanted at PMd",
                location="Caudal, dorsal Pre-motor cortex, Left hemisphere",
                device="Utah Array(PMd)",
            ),
            dict(
                name="2",
                description="array corresponding to device implanted at M1",
                location="M1 in Motor Cortex, left hemisphere",
                device="Utah Array(M1)",
            ),
        ]
        metadata["Ecephys"]["Electrodes"] = [
            dict(name="filtering", description="filtering", data=["1000Hz"] * 96)]

        return metadata

