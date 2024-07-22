from neuroconv import NWBConverter
from .shenoyblackrockrecordingdatainterface import ShenoyBlackrockRecordingInterface

class MazeTaskUnsortedNWBConverter(NWBConverter):
    data_interface_classes = dict(
        A1=ShenoyBlackrockRecordingInterface,
        B1=ShenoyBlackrockRecordingInterface,
        A2=ShenoyBlackrockRecordingInterface,
        B2=ShenoyBlackrockRecordingInterface,
        A3=ShenoyBlackrockRecordingInterface,
        B3=ShenoyBlackrockRecordingInterface,
        A4=ShenoyBlackrockRecordingInterface,
        B4=ShenoyBlackrockRecordingInterface,
        A5=ShenoyBlackrockRecordingInterface,
        B5=ShenoyBlackrockRecordingInterface,
    )