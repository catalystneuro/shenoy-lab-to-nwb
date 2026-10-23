from neuroconv.utils import load_dict_from_file, dict_deep_update
from pathlib import Path
from pytz import timezone
from datetime import datetime

from maze_task_unsorted.maze_task_unsorted_nwbconverter import MazeTaskUnsortedNWBConverter

DATES_OF_BIRTH = dict(Nitschke=datetime(2005, 4, 14))


def session_to_nwb(*, data_dir_path, output_dir_path, subject_id: str):
    """
    Convert one maze task session.

    data_dir_path holds the session's mat file, named like "RC,2009-09-12,1-2.mat", and its
    datafileA001.ns2, datafileB001.ns2, ... recordings, one pair per segment.
    """
    data_dir_path = Path(data_dir_path)
    output_dir_path = Path(output_dir_path)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    (mat_file_path,) = data_dir_path.glob("R*.mat")
    session_date = mat_file_path.stem.split(",")[1]

    source_data, conversion_options = {}, {}
    for file_path in sorted(data_dir_path.glob("datafile[AB]*.ns2")):
        es_key = f"ElectricalSeries{file_path.stem[-4:]}"
        datainterface_key = file_path.stem[-4] + str(int(file_path.stem[-3:]))
        source_data[datainterface_key] = dict(file_path=file_path, es_key=es_key)
        conversion_options[datainterface_key] = dict(write_as="processed")
    source_data["Mat"] = dict(filename=mat_file_path, subject_name=subject_id[0])

    converter = MazeTaskUnsortedNWBConverter(source_data=source_data)
    metadata = converter.get_metadata(use_new_metadata_format=False)

    editable_metadata_path = Path(__file__).parent / "maze_task_unsorted_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    pst = timezone("US/Pacific")
    metadata["NWBFile"]["session_start_time"] = pst.localize(datetime.strptime(session_date, "%Y-%m-%d"))
    metadata["NWBFile"]["session_id"] = metadata["NWBFile"]["session_start_time"].strftime("%Y%m%d")
    metadata["Subject"]["subject_id"] = subject_id
    if subject_id in DATES_OF_BIRTH:
        metadata["Subject"]["date_of_birth"] = pst.localize(DATES_OF_BIRTH[subject_id])
    else:
        # age unknown: an ISO 8601 interval with both ends unspecified
        metadata["Subject"]["age"] = "/"

    nwbfile_path = output_dir_path / f"sub-{subject_id}_ses-{metadata['NWBFile']['session_id']}.nwb"

    converter.run_conversion(
        metadata=metadata,
        nwbfile_path=nwbfile_path,
        conversion_options=conversion_options,
        overwrite=True,
    )
    return nwbfile_path


def main():
    session_to_nwb(
        data_dir_path="/Volumes/T7/CatalystNeuro/NWB/Shenoy/2010-09-23",
        output_dir_path="/Volumes/T7/CatalystNeuro/NWB/Shenoy/conversion_nwb",
        subject_id="Nitschke",
    )


if __name__ == "__main__":
    main()
