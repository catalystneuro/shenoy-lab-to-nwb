from churchlandnwbconverter import ChurchlandNWBConverter
from pathlib import Path
import pytz
from datetime import datetime
#enter the path of the source folder containing the RC.mat file and nsx files.
source_folder = Path(r'C:\Users\Saksham\Documents\NWB\shenoy\data\Jenkins\SpikeSorted\0928')

#retrieve the correct files from source path:
nsx_file_names = ['datafileA001.ns2','datafileB001.ns2','datafileA002.ns2','datafileB002.ns2']
nsx_files = list(source_folder.glob('**/*.ns2'))
assert len(nsx_files)==4, f'only 4 ns2 files expected with names: {nsx_file_names}'
assert all([i.name in nsx_file_names for i in nsx_files]), f'one of {nsx_file_names} missing'
nsx_list = [str(i.with_name(nsx_file_names[no])) for no, i in enumerate(nsx_files)]
mat_file = str(list(source_folder.glob('**/RC*.mat'))[0])
subject_name = source_folder.parent.parent.name

#construct argument for nwbconverter based on schema:
source_data = dict(Mat=dict(filename=mat_file,subject_name=subject_name[0]),
                   A1=dict(filename=nsx_list[0]),
                   B1=dict(filename=nsx_list[1]),
                   A2=dict(filename=nsx_list[2]),
                   B2=dict(filename=nsx_list[3]),
                   subject_name=subject_name,
                   date=pytz.timezone('US/Pacific').localize(datetime.strptime('2009'+source_folder.name, '%Y%m%d')))

ch = ChurchlandNWBConverter(source_data)
nwbfile_saveloc = source_folder/f'{source_folder.name}_nwb_v2.nwb'
conversion_options = dict(A1=dict(es_key=f'ElectricalSeries{Path(nsx_list[0]).stem[-4:]}'),
                          B1=dict(es_key=f'ElectricalSeries{Path(nsx_list[1]).stem[-4:]}'),
                          A2=dict(es_key=f'ElectricalSeries{Path(nsx_list[2]).stem[-4:]}'),
                          B2=dict(es_key=f'ElectricalSeries{Path(nsx_list[3]).stem[-4:]}'))
print('running conversion to nwb...')
ch.run_conversion(metadata=ch.get_metadata(),
                  nwbfile_path=str(nwbfile_saveloc),
                  conversion_options=conversion_options)