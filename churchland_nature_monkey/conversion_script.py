from churchlandnwbconverter import ChurchlandNWBConverter
from pathlib import Path
import pytz
from datetime import datetime


def convert(source_folder):
# retrieve the correct files from source path:
    nsx_file_names = [
        "datafileA001.ns2",
        "datafileB001.ns2",
        "datafileA002.ns2",
        "datafileB002.ns2",
        "datafileA003.ns2",
        "datafileB003.ns2",
        "datafileA004.ns2",
        "datafileB004.ns2",
    ]
    nsx_files = list(source_folder.glob("**/*.ns2"))
    assert len(nsx_files) >=2, f"at least 2 ns2 files need to be present: {nsx_file_names}"
    assert all(
        [i.name in nsx_file_names for i in nsx_files]
    ), f"one of {nsx_file_names} missing"
    nsx_list = [str(i.with_name(nsx_file_names[no])) for no, i in enumerate(nsx_files)]
    mat_file = str(list(source_folder.glob("**/R*.mat"))[0])
    subject_name = source_folder.parent.parent.name

    # construct argument for nwbconverter based on schema:
    arg_names = ['A1','B1','A2','B2','A3','B3','A4','B4']
    source_data = dict(
        Mat=dict(filename=mat_file, subject_name=subject_name[0]),
        subject_name=subject_name,
        date=pytz.timezone("US/Pacific").localize(
            datetime.strptime("2009" + source_folder.name, "%Y%m%d")
        ),
    )
    for no, filename in enumerate(nsx_list):
        source_data.update({arg_names[no]: dict(filename=filename)})

    ch = ChurchlandNWBConverter(source_data)
    nwbfile_saveloc = source_folder / f"{source_folder.name}_nwb_v3.nwb"
    conversion_options = {arg_names[no]:dict(es_key=f"ElectricalSeries{Path(i).stem[-4:]}")
                          for no, i in enumerate(nsx_list)}

    print("running conversion to nwb...")
    ch.run_conversion(
        metadata=ch.get_metadata(),
        nwbfile_path=str(nwbfile_saveloc), 
        overwrite=True,
        conversion_options=conversion_options,
    )
    print(f'converted for {source_folder}')

source_folder = Path(
    r"C:\Users\Saksham\Documents\NWB\shenoy\data\Nitschke\spikesorted"
)
for no, folder in enumerate(source_folder.iterdir()):
    convert(folder)
