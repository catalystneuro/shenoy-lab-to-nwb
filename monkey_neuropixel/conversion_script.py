from pathlib import Path

from .converter import NpxNWBConverter
from nwb_conversion_tools.utils.json_schema import dict_deep_update

# retrieve default experiment metadata and sessions list (can be changed in the yaml file):
from . import metadata_location_path, session_list_location_path
import yaml

with open(str(metadata_location_path), "r") as io:
    metadata_default = yaml.load(io, Loader=yaml.FullLoader)


## 1. Run a single session conversion:
mat_path = Path(
    r"/mnt/scrap/catalyst_neuro/sakshamsharda/shenoy/PrimateNeuropixel/P20180323/P20180323.behavior.mat"
)
sglx_path = Path(
    r"/mnt/scrap/catalyst_neuro/sakshamsharda/shenoy/PrimateNeuropixel/P20180323/P20180323_g0_t0.imec0.ap.bin"
)
converter_args = dict(
    Mat=dict(filename=str(mat_path)), Sgx=dict(file_path=str(sglx_path))
)
# create NWBConverter class:
mt = NpxNWBConverter(converter_args)

# get and update metadata to go with the NWB file
metadata = mt.get_metadata()
metadata = dict_deep_update(metadata, metadata_default)
stub = True
conversion_options = dict(
    Sgx=dict(stub_test=stub)
)  # specify this as True if testing a conversion
nwb_path_append = "_stub" if stub else ""
nwbname = mat_path.parent/f"{mat_path.stem}_stub.nwb"
mt.run_conversion(
    nwbfile_path=str(nwbname),
    overwrite=True,
    metadata=metadata,
    conversion_options=conversion_options,
)

## 2. Convert multiple sessions using parallelization:

from .converter import NpxNWBConverter
from pathlib import Path
from joblib import Parallel, delayed
import yaml

with open(str(session_list_location_path), "r") as io:
    session_names_list = yaml.load(io, Loader=yaml.FullLoader)
mat_pt_list = []
bin_pt_list = []
for name in session_names_list:
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
    metadata = nc.get_metadata()
    metadata = dict_deep_update(metadata, metadata_default)
    stub = True
    nwb_path_append = "_stub" if stub else ""
    nwb_pt = bin_pt.parent / Path(bin_pt.name.split(".")[0] + f"{nwb_path_append}.nwb")
    conversion_options = dict(Sgx=dict(stub_test=stub))
    nc.run_conversion(
        nwbfile_path=str(nwb_pt),
        overwrite=True,
        metadata=metadata,
        conversion_options=conversion_options,
    )
    print(
        f'**************************conversion run for {mat_pt.name.split(".")[0]}............................'
    )


Parallel(n_jobs=20)(
    delayed(converter)(mat_pt, bin_pt)
    for mat_pt, bin_pt in zip(mat_pt_list, bin_pt_list)
)
