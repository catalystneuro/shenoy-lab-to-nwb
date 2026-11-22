from neuroconv import NWBConverter
from .shenoyblackrockrecordingdatainterface import ShenoyBlackrockRecordingInterface
from .shenoymatdatainterface import ShenoyMatDataInterface

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
        Mat=ShenoyMatDataInterface,
    )

    def temporally_align_data_interfaces(self, metadata=None, conversion_options=None):
        # Trial times are on the clock of each array A recording file, which restarts at zero with
        # every segment. Place each segment's recordings at the offset its trials were shifted by.
        # Array B was recorded by a second system with its own clock, which is mapped onto array A's
        # clock using the trial start times recorded on both.
        mat_extractor = self.data_interface_objects["Mat"].mat_extractor
        segment_keys = sorted(
            (key for key in self.data_interface_objects if key.startswith("A")), key=lambda key: int(key[1:])
        )
        mat_extractor.segment_durations = [
            self.data_interface_objects[key].recording_extractor.get_total_duration() for key in segment_keys
        ]
        _, segment_offsets = mat_extractor.extract_trial_times()
        array_b_clock_map = mat_extractor.extract_array_b_clock_map()
        for segment, offset in enumerate(segment_offsets, start=1):
            self.data_interface_objects[f"A{segment}"].set_aligned_starting_time(offset)
            if f"B{segment}" in self.data_interface_objects:
                interface = self.data_interface_objects[f"B{segment}"]
                slope, intercept = array_b_clock_map[segment - 1]
                interface.set_aligned_timestamps(offset + intercept + slope * interface.get_timestamps())
