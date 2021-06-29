import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np
from datetime import datetime
from pynwb import NWBHDF5IO, NWBFile
from ..maze_task.matextractor import MatDataExtractor
from hdmf.common.table import VectorIndex


class TestChurchlandConversion(unittest.TestCase):
    def setUp(self) -> None:
        datapath = Path(__file__).parents[2]/'data/Jenkins/SpikeSorted/0928'
        nwbfile_path = datapath/'0928_nwb_v5_beforemeeting.nwb'
        matfile_path = datapath/'RC,2009-09-28,1-2.mat'
        self.mat_extractor = MatDataExtractor(matfile_path)
        self._io = NWBHDF5IO(str(nwbfile_path),'r')
        self.nwbfile = self._io.read()
        # self.trial_events_map = {
        #     'actualFlyAppears': 'target_presentation_time',
        #     'actualLandingTime': 'go_cue_time',
        #     'onlineRT': 'move_begins_time',
        #     'moveEndsTime': 'move_ends_time',
        #     'possibleRTproblem': 'discard_trial',
        #     'success': 'task_success',
        #     'trialType': 'trial_type',
        #     'trialVersion': 'trial_version',
        #     'protoTrial': 'proto_trial',
        #     'primaryCondNum': 'maze_condition',
        #     'numFlies': 'maze_num_targets',
        #     'numBarriers': 'maze_num_barriers',
        #     'novelMaze': 'novel_maze'
        # }

    def tearDown(self) -> None:
        self._io.close()

    def test_trials(self):
        trials = self.nwbfile.trials
        trial_events = self.mat_extractor.extract_trial_events()
        trial_details = self.mat_extractor.extract_trial_details()
        maze_details = self.mat_extractor.extract_maze_data()
        for trial_col_details in trial_events+trial_details+maze_details:
            colname = trial_col_details['name']
            coldata = trial_col_details['data']
            if not isinstance(trials[colname],VectorIndex):
                assert np.allclose(coldata,trials[colname].data, equal_nan=True)
            else:
                for i in range(len(coldata)):
                    assert np.allclose(coldata[i],trials[colname][i], equal_nan=True)

    def test_spike_events(self):
        pass

    def test_behavior(self):
        eye_positions,hand_positions,cursor_positions = \
            self.mat_extractor.extract_behavioral_position()
        eye_data = np.concatenate(eye_positions, axis=0)
        cursor_data = np.concatenate(cursor_positions, axis=0)
        hand_data = np.concatenate(hand_positions, axis=0)
        beh_mod = self.nwbfile.get_processing_module('behavior').data_interfaces['Position']
        for name, data in zip(
                ["Eye", "Hand", "Cursor"], [eye_data, hand_data, cursor_data]
        ):
            assert np.allclose(beh_mod[name].timestamps,data[:,2],equal_nan=True)
            assert np.allclose(beh_mod[name].data, data[:,:2],equal_nan=True)

