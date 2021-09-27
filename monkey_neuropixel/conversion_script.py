from monkey_neuropixel.converter import NpxNWBConverter
from pathlib import Path
from nwb_conversion_tools import NWBConverter

pt = Path(r'C:\Users\Saksham\Documents\NWB\shenoy\data\PrimateNeuropixel\P20180323.behavior.mat')
nwbfile_saveloc = pt.with_suffix('.nwb')
mt = NpxNWBConverter(dict(Mat=dict(filename=str(pt))))
conversion_options=dict()
mt.run_conversion(
        nwbfile_path=str(nwbfile_saveloc),
        overwrite=True,
        conversion_options=conversion_options,
    )