from neuroconv.utils import FolderPathType, load_dict_from_file, dict_deep_update
from pathlib import Path
import shutil
from pytz import timezone
from datetime import datetime

from maze_task_unsorted.maze_task_unsorted_nwbconverter import MazeTaskUnsortedNWBConverter

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
