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


# conversion on smaug script ---------------
from monkey_neuropixel.converter import NpxNWBConverter
from pathlib import Path
mat_pt = Path(r'/mnt/scrap/catalyst_neuro/sakshamsharda/shenoy/PrimateNeuropixel/P20180323/P20180323.behavior.mat')
bin_pt = Path(r'/mnt/scrap/catalyst_neuro/sakshamsharda/shenoy/PrimateNeuropixel/P20180323/P20180323_g0_t0.imec0.ap.bin')

arg = dict(Mat=dict(filename=str(mat_pt)), Sgx=dict(file_path=str(bin_pt)))
nwb_pt = bin_pt.parent/Path(bin_pt.name.split('.')[0]+'.nwb')

nc = NpxNWBConverter(arg)
metadata = nc.get_metadata()
metadata["Ecephys"]["ElectricalSeries_raw"]["description"] = \
    "(1) done ADC-bank-wise common average referencing along the lines of Siegle, Jia et al. 2021 " \
    "[ https://doi.org/10.1038/s41586-020-03171-x ], (2) cleared the unused bits in the sync channel that were " \
    "left floating, (3) concatenated each of the individual raw datasets we collected during the session into one " \
    "file and (4) excised problematic time windows where the monkey was asleep or distracted, or regions where the " \
    "monkey began a new behavioral task that is not considered part of this dataset. This last step was important for " \
    "achieving consistent, stable sorts with KiloSort 2.0 "
nc.run_conversion(nwbfile_path=str(nwb_pt), overwrite=True, conversion_options=dict(),metadata=metadata)