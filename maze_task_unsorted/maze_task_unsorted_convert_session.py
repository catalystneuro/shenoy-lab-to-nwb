from neuroconv.utils import FolderPathType, FilePathType, load_dict_from_file, dict_deep_update
from neuroconv.datainterfaces import BlackrockRecordingInterface
from neuroconv import NWBConverter
from pathlib import Path
import shutil
from pytz import timezone
from datetime import datetime
from spikeinterface.extractors import BlackrockRecordingExtractor

class ShenoyBlackrockRecordingInterface(BlackrockRecordingInterface):
    Extractor = BlackrockRecordingExtractor

    def __init__(self, file_path: FilePathType, es_key: str = "ElectricalSeries"):
        super().__init__(file_path=file_path, es_key=es_key)
        if "B" in file_path.name:
            self._region = "M1 Motor Cortex"
            self.recording_extractor._channel_ids = [
                i + 96 for i in self.recording_extractor._channel_ids
            ]
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

class MazeTaskUnsortedNWBConverter(NWBConverter):
    data_interface_classes = dict(
        BlackRock=ShenoyBlackrockRecordingInterface,
    )

def session_to_nwb(
    *,
    data_dir_path: FolderPathType,
    output_dir_path: FolderPathType,
    datafile_names: list[str],
    verbose: bool = True,
):
    data_dir_path = Path(data_dir_path)
    output_dir_path = Path(output_dir_path)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    datafile_name = datafile_names[0]
    file_path = data_dir_path / datafile_name
    es_key = f"ElectricalSeries{file_path.stem[-4:]}"
    source_data = dict(BlackRock=dict(file_path=file_path, es_key=es_key))

    converter = MazeTaskUnsortedNWBConverter(source_data=source_data)
    metadata = converter.get_metadata()

    editable_metadata_path = Path(__file__).parent / "maze_task_unsorted_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    pst = timezone("US/Pacific")
    metadata["NWBFile"]["session_start_time"] = datetime.strptime(data_dir_path.name, "%Y-%m-%d").replace(tzinfo=pst)

    nwbfile_path = output_dir_path / f"{file_path.stem}.nwb"

    converter.run_conversion(
        metadata=metadata,
        nwbfile_path=nwbfile_path,
    )

def main():
    data_dir_path = Path("/Volumes/T7/CatalystNeuro/NWB/Shenoy/2010-09-23")
    output_dir_path = Path("/Volumes/T7/CatalystNeuro/NWB/Shenoy/conversion_nwb")
    datafile_names = [
        "datafileA001.ns2",
    ]
    if output_dir_path.exists():
        shutil.rmtree(output_dir_path, ignore_errors=True)
    session_to_nwb(
        data_dir_path=data_dir_path,
        output_dir_path=output_dir_path,
        datafile_names=datafile_names,
    )

if __name__ == "__main__":
    main()
