from neuroconv.utils import FolderPathType, FilePathType, load_dict_from_file, dict_deep_update
from pathlib import Path
import shutil
from pytz import timezone
from datetime import datetime

from maze_task_unsorted.maze_task_unsorted_nwbconverter import MazeTaskUnsortedNWBConverter

def session_to_nwb(
    *,
    data_dir_path: FolderPathType,
    output_dir_path: FolderPathType,
    datafile_names: list[FilePathType],
    matfile_name: FilePathType,
    verbose: bool = True,
):
    data_dir_path = Path(data_dir_path)
    output_dir_path = Path(output_dir_path)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    source_data, conversion_options = {}, {}
    for datafile_name in datafile_names:
        file_path = data_dir_path / datafile_name
        es_key = f"ElectricalSeries{file_path.stem[-4:]}"
        datainterface_key = file_path.stem[-4] + file_path.stem[-1]
        source_data[datainterface_key] = dict(file_path=file_path, es_key=es_key)
        conversion_options[datainterface_key] = dict(write_as="processed")
    source_data["Mat"] = dict(filename=data_dir_path / matfile_name, subject_name="N")

    converter = MazeTaskUnsortedNWBConverter(source_data=source_data)
    metadata = converter.get_metadata()

    editable_metadata_path = Path(__file__).parent / "maze_task_unsorted_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    pst = timezone("US/Pacific")
    metadata["NWBFile"]["session_start_time"] = datetime.strptime(data_dir_path.name, "%Y-%m-%d").replace(tzinfo=pst)
    metadata["NWBFile"]["session_id"] = metadata["NWBFile"]["session_start_time"].strftime("%Y%m%d")

    nwbfile_path = output_dir_path / f"{data_dir_path.name}.nwb"

    converter.run_conversion(
        metadata=metadata,
        nwbfile_path=nwbfile_path,
        conversion_options=conversion_options,
    )

def main():
    data_dir_path = Path("/Volumes/T7/CatalystNeuro/NWB/Shenoy/2010-09-23")
    output_dir_path = Path("/Volumes/T7/CatalystNeuro/NWB/Shenoy/conversion_nwb")
    datafile_names = [
        "datafileA001.ns2",
        "datafileB001.ns2",
        "datafileA002.ns2",
        "datafileB002.ns2",
        "datafileA003.ns2",
        "datafileB003.ns2",
        "datafileA004.ns2",
        "datafileB004.ns2",
        "datafileA005.ns2",
        "datafileB005.ns2",
    ]
    matfile_name = "RC,2010-09-23,1-2-3-4-5.mat"
    if output_dir_path.exists():
        shutil.rmtree(output_dir_path, ignore_errors=True)
    session_to_nwb(
        data_dir_path=data_dir_path,
        output_dir_path=output_dir_path,
        datafile_names=datafile_names,
        matfile_name=matfile_name,
    )

if __name__ == "__main__":
    main()
