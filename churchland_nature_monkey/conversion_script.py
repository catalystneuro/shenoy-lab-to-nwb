from churchland_nature_monkey.churchlanddatainterface import ChurchlandDataInterface
from pathlib import Path
#enter the path of the source folder containing the RC.mat file and nsx files.
source_path = Path(r'C:\Users\Saksham\Documents\NWB\shenoy\data\Jenkins\SpikeSorted\0928')
ch = ChurchlandDataInterface(source_path)
nwbfile_saveloc = source_path/f'{source_path.name}_nwb_v2.nwb'
ch.run_conversion(metadata=ch.get_metadata(),nwbfile_path=str(nwbfile_saveloc))