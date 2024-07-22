from neuroconv.datainterfaces import BlackrockRecordingInterface
from spikeinterface.extractors import BlackrockRecordingExtractor
from neuroconv.utils import FilePathType
import numpy as np

class ShenoyBlackrockRecordingInterface(BlackrockRecordingInterface):
    Extractor = BlackrockRecordingExtractor

    def __init__(self, file_path: FilePathType, es_key: str = "ElectricalSeries"):
        super().__init__(file_path=file_path, es_key=es_key)
        if "B" in file_path.name:
            self._region = "M1 Motor Cortex"
            self.recording_extractor._main_ids = np.array([
                str(int(i) + 96) for i in self.recording_extractor._main_ids
            ])
            self.recording_extractor.set_channel_groups([2] * 96)
        else:
            self._region = "Pre-Motor Cortex, dorsal"
            self.recording_extractor.set_channel_groups([1] * 96)
        self.recording_extractor.set_property("filtering", ["1000Hz"]*96)
        self.recording_extractor.set_property("brain_area", [self._region]*96)

    def get_metadata(self):
        metadata = super().get_metadata()

        file_path = self.source_data["file_path"]
        es_key = self.es_key

        metadata["Ecephys"][es_key]["description"] = (
        f"LFP signal for array {file_path.stem[8]}, segment {file_path.stem[-1]}"
        f"data for both arrays A,B in the same segment should be, but is not of the same time length"
        f"and cannot be synced due to lack of time stamps. Ignore the starting times."
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
        return metadata