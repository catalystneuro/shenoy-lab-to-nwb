from pathlib import Path

from monkey_neuropixel.converter import NpxNWBConverter
from nwb_conversion_tools.utils.json_schema import (
    dict_deep_update
)
# retrieve metadata that is common:
from . import metadata_location_path
import json
with open(str(metadata_location_path), "r") as io:
    metadata_retrieved = json.load(io)

pt = Path(
    r"C:\Users\Saksham\Documents\NWB\shenoy\data\PrimateNeuropixel\P20180323.behavior.mat"
)
nwbfile_saveloc = pt.with_suffix(".nwb")
mt = NpxNWBConverter(dict(Mat=dict(filename=str(pt))))
metadata  = mt.get_metadata()
metadata = dict_deep_update(metadata, metadata_retrieved)
conversion_options = dict()
mt.run_conversion(
    nwbfile_path=str(nwbfile_saveloc),
    overwrite=True,
    metadata=metadata,
    conversion_options=conversion_options,
)

# conversion on smaug script ---------------
sess_names = [
    "P20180327",
    "P20180607",
    "P20180608",
    "P20180609",
    "P20180612",
    "P20180613",
    "P20180614",
    "P20180615",
    "P20180620",
    "P20180622",
    "P20180704",
    "P20180705",
    "P20180707",
    "P20180710",
    "P20180711",
    "V20180814",
    "V20180815",
    "V20180817",
    "V20180818",
    "V20180819",
    "V20180820",
    "V20180821",
    "V20180822",
    "V20180823",
    "V20180919",
    "V20180920",
    "V20180921",
    "V20180922",
    "V20180923",
    "V20180925",
    "V20180926",
    "V20180927",
    "V20180928",
    "V20181128",
    "V20181204",
]

from monkey_neuropixel.converter import NpxNWBConverter
from pathlib import Path
from joblib import Parallel, delayed

mat_pt_list = []
bin_pt_list = []
for name in sess_names:
    mat_pt = Path(
        fr"/mnt/scrap/catalyst_neuro/sakshamsharda/shenoy/PrimateNeuropixel/{name}/{name}.behavior.mat"
    )
    bin_pt = Path(
        fr"/mnt/scrap/catalyst_neuro/sakshamsharda/shenoy/PrimateNeuropixel/{name}/{name}_g0_t0.imec0.ap.bin"
    )
    if mat_pt.exists() and bin_pt.exists():
        mat_pt_list.append(mat_pt)
        bin_pt_list.append(bin_pt)


def converter(mat_pt, bin_pt):
    arg = dict(Mat=dict(filename=str(mat_pt)), Sgx=dict(file_path=str(bin_pt)))
    nc = NpxNWBConverter(arg)
    with open(str(metadata_location_path), "r") as io:
        metadata_retrieved = json.load(io)
    metadata = nc.get_metadata()
    metadata = dict_deep_update(metadata, metadata_retrieved)
    nwb_pt = bin_pt.parent / Path(bin_pt.name.split(".")[0] + ".nwb")

    nc.run_conversion(nwbfile_path=str(nwb_pt), overwrite=True, metadata=metadata,conversion_options=dict())
    print(
        f'**************************conversion run for {mat_pt.name.split(".")[0]}............................'
    )


Parallel(n_jobs=20)(
    delayed(converter)(mat_pt, bin_pt)
    for mat_pt, bin_pt in zip(mat_pt_list, bin_pt_list)
)
