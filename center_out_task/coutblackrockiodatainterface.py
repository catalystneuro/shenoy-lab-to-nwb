from pathlib import Path
import numpy as np
from typing import Union
from nwb_conversion_tools import NWBConverter
from nwb_conversion_tools.basedatainterface import BaseDataInterface
from neo import BlackrockIO

PathType = Union[str, Path]


class COutBlackrockIODataInterface(BaseDataInterface):
    def __init__(self, file_name: Path):
        self.file_path = Path(file_name)
        assert self.file_path.suffix == ".nsx", "file_path should be a .ns3"
        assert self.file_path.exists(), "file_path does not exist"
        self.blackrock_io = BlackrockIO('',nsx_override=self.file_path)
        self.electrode_group = self.file_path.parent.name

    def get_metadata(self):
        metadata = dict(
            Ecephys=dict(
                Device=[dict(name="Device_ecephys", description="no description")],
                ElectrodeGroup=[],
            )
        )
        metadata["Ecephys"].update(
            {
                f"ElectricalSeries{self.nsx_loc.stem[-4:]}": dict(
                    name=self.nsx_loc.stem[-4:],
                    description=f"LFP signal for array {self.nsx_loc.stem[8]}, segment {self.nsx_loc.stem[-1]}"
                    f"data for both arrays A,B in the same segment should be, but is not of the same time length"
                    f"and cannot be synced due to lack of time stamps. Ignore the starting times.",
                )
            }
        )
        metadata["Ecephys"]["Device"] = [
            dict(
                name="Utah Array(PMd)",
                description="96 channel utah array",
                manufacturer="BlackRock Microsystems",
            ),
            dict(
                name="Utah Array(M1)",
                description="96 channel utah array",
                manufacturer="BlackRock Microsystems",
            ),
        ]
        metadata["Ecephys"]["ElectrodeGroup"] = [
            dict(
                name="1",
                description="array corresponding to device implanted at PMd",
                location="Caudal, dorsal Pre-motor cortex, Left hemisphere",
                device="Utah Array(PMd)",
            ),
            dict(
                name="2",
                description="array corresponding to device implanted at M1",
                location="M1 in Motor Cortex, left hemisphere",
                device="Utah Array(M1)",
            ),
        ]

        return metadata