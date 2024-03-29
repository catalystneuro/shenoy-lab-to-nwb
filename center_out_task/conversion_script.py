from pathlib import Path

from joblib import Parallel, delayed

from .coutnwbconverter import COutNWBConverter

import cv2


def convert(source_folder):
    # retrieve the correct files from source path:
    nsx_files = list(source_folder.glob("**/*.ns3"))
    movie_file = list(source_folder.glob("**/*.avi"))
    mat_file = list(source_folder.glob("**/R*.mat"))[0]

    source_data = dict()
    conversion_options = dict()
    for nsx_file in nsx_files:
        if "M1" in nsx_file.parent.name:
            array = "A"
        else:
            array = "B"
        arg_name = array + nsx_file.stem[-1]
        source_data.update({arg_name: dict(filename="", nsx_override=str(nsx_file))})
        conversion_options.update(
            {
                arg_name: dict(
                    es_key=f"ElectricalSeries_{nsx_file.parent.stem + '_' + nsx_file.stem[-1]}",
                    write_as="lfp",
                )
            }
        )
    source_data.update(Mat=dict(filename=str(mat_file)))
    if len(movie_file) > 0:
        cap = cv2.VideoCapture(str(movie_file[0]))
        success, _ = cap.read()
        if success:
            source_data.update(Movie=dict(movie_filepath=str(movie_file[0])))
            conversion_options.update(Movie=dict(external_mode=True))

    ch = COutNWBConverter(source_data)
    nwbfile_saveloc = source_folder/f"{source_folder.name}_nwb_v4.nwb"

    print("running conversion to nwb...")
    ch.run_conversion(
        metadata=ch.get_metadata(),
        nwbfile_path=str(nwbfile_saveloc),
        overwrite=True,
        conversion_options=conversion_options,
    )
    print(f"converted for {source_folder}")


if __name__ == "__main__":
    source_folder = Path(
        r"C:\Users\Saksham\Documents\NWB\shenoy\data\centerOut\3Ring\2016-01-28 (1)"
    )
    convert(source_folder)


def run_parallel(pt):
    pt = Path(pt)
    Parallel(n_jobs=10)(delayed(convert)(loc) for loc in pt.glob("*/*"))
