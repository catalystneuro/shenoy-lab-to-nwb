from .coutnwbconverter import COutNWBConverter
from pathlib import Path


def convert(source_folder):
# retrieve the correct files from source path:
    nsx_files = list(source_folder.glob("**/*.ns3"))
    movie_file = list(source_folder.glob("**/*.avi"))[0]
    mat_file = list(source_folder.glob("**/R*.mat"))[0]

    assert len(nsx_files) >=2, "at least 2 ns2 files need to be present"
    source_data = dict()
    conversion_options = dict()
    for nsx_file in nsx_files:
        if 'M1' in nsx_file.parent.name:
            array = 'A'
        else:
            array = "B"
        arg_name = array+nsx_file.stem[-1]
        source_data.update({arg_name:nsx_file})
        conversion_options.update({arg_name:dict(
            es_key=f"ElectricalSeries_{nsx_file.parent.stem+'_'+nsx_file.stem[-1]}")})
    source_data.update(Mat=mat_file,Movie=movie_file)


    ch = COutNWBConverter(source_data)
    nwbfile_saveloc = source_folder / f"{source_folder.name}_nwb.nwb"

    print("running conversion to nwb...")
    ch.run_conversion(
        metadata=ch.get_metadata(),
        nwbfile_path=str(nwbfile_saveloc),
        overwrite=True,
        conversion_options=conversion_options,
    )
    print(f'converted for {source_folder}')

source_folder = Path(
    r"C:\Users\Saksham\Documents\NWB\shenoy\data\centerOut\24TargetCenterOut\2015-10-09"
)
convert(source_folder)