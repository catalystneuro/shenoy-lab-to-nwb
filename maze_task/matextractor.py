from pathlib import Path

import numpy as np
import scipy.io as scio


class MatDataExtractor:
    def __init__(self, input_dir, monkey_name="J"):
        self.monkey_name = monkey_name
        path_r_file = Path(input_dir)
        rfile = scio.loadmat(str(path_r_file))
        self.R = rfile["R"][0]
        self.SU = rfile["SU"]
        self._good_trials = self.good_trials()
        self._no_units = self.SU[0, 0]["unitLookup"].shape[0]
        # durations in seconds of the array A recording files (datafileA001, A002, ...), if known
        self.segment_durations = None

    def good_trials(self):
        good_trials = []
        for i in range(self.R.shape[0]):
            if self.R["CerebusInfoA"][i].shape[0] == 1:
                good_trials.append(i)
        return good_trials

    def get_trial_ids(self):
        return [
            self.R["CerebusInfoA"][i]["trialID"][0, 0][0, 0] for i in self._good_trials
        ]

    def extract_unit_spike_times(self, trial_nos=None):
        if trial_nos is None:
            trial_nos = self._good_trials
        units_list = []
        for trial_no in trial_nos:
            units_list.append(
                [
                    self.R["unit"][trial_no]["spikeTimes"][0][i].flatten() / 1e3
                    for i in range(self._no_units)
                ]
            )
        return units_list

    def extract_trial_times(self, trial_nos=None):
        """
        Times in seconds.

        CerebusInfoA start and end times are on the clock of the recording file the trial was
        recorded in (datafileA001, A002, ...), which restarts at zero with each file. Each segment
        after the first is shifted to start one mean inter-trial interval after the last trial of the
        previous segment, or, if the previous segment's recording is longer than that, at the end of
        that recording (see ``segment_durations``).

        Returns
        -------
        trial_times : np.ndarray
            (n_trials, 2) start and stop times on the session timeline.
        segment_offsets : np.ndarray
            For each recording segment, the time on the session timeline of t=0 in that segment's
            recording file.
        """
        if trial_nos is None:
            trial_nos = self._good_trials
        trial_times = np.array(
            [
                [
                    self.R["CerebusInfoA"][i]["startTime"][0, 0][0, 0],
                    self.R["CerebusInfoA"][i]["endTime"][0, 0][0, 0],
                ]
                for i in trial_nos
            ]
        )
        segment_starts = np.flatnonzero(np.diff(trial_times[:, 0]) < 0) + 1
        segment_bounds = np.r_[0, segment_starts, len(trial_times)]
        # mean interval between consecutive good trials within the same segment:
        inter_trial_intervals = trial_times[1:, 0] - trial_times[:-1, 1]
        within_segment = np.diff(self._good_trials) == 1
        within_segment[segment_starts - 1] = False
        mean_interval = inter_trial_intervals[within_segment].mean()
        segment_offsets = np.zeros(len(segment_bounds) - 1)
        for seg in range(1, len(segment_offsets)):
            start, stop = segment_bounds[seg], segment_bounds[seg + 1]
            offset = trial_times[start - 1, 1] + mean_interval - trial_times[start, 0]
            if self.segment_durations is not None:
                offset = max(offset, segment_offsets[seg - 1] + self.segment_durations[seg - 1])
            segment_offsets[seg] = offset
            trial_times[start:stop, :] += offset
        return trial_times, segment_offsets

    def extract_trial_events(self, trial_nos=None):
        """
        Time in seconds wrt trial start time
        """
        trial_times, _ = self.extract_trial_times()
        if trial_nos is None:
            trial_nos = self._good_trials
        trial_events_dict = []
        events = [
            [
                "actualFlyAppears",
                "target_presentation_time",
                "time of target presentation",
            ],
            ["actualLandingTime", "go_cue_time", "time of go cue"],
            ["onlineRT", "reaction_time", "reaction time"],
            ["moveBeginsTime", "move_begins_time", "movement onset time"],
            ["moveEndsTime", "move_ends_time", "movement stop time"],
        ]
        for event in events:
            if "onlineRT" not in event:
                trial_events_dict.append(
                    dict(
                        name=event[1],
                        data=np.array(
                            [
                                self.R[event[0]][i][0, 0] / 1e3 + trial_times[no, 0]
                                if self.R[event[0]][i].shape[0] != 0
                                else np.nan
                                for no, i in enumerate(trial_nos)
                            ]
                        ),
                        description=event[2],
                    )
                )
            else:
                trial_events_dict.append(
                    dict(
                        name=event[1],
                        data=np.array(
                            [
                                self.R[event[0]][i][0, 0] / 1e3
                                if self.R[event[0]][i].shape[0] != 0
                                else np.nan
                                for i in trial_nos
                            ]
                        ),
                        description=event[2],
                    )
                )
        return trial_events_dict

    def extract_trial_details(self, trial_nos=None):
        """
        Time in seconds wrt trial start time
        """
        if trial_nos is None:
            trial_nos = self._good_trials
        trial_details_dict = []
        events = [
            [
                "possibleRTproblem",
                "discard_trial",
                "flag that will usually be 0, but is set to 1 "
                "if there was a photo box problem (meaning RT can't be "
                "calculated accurately) or we had a hand tracking error "
                "during the movement. In general, throw those trials away.",
            ],
            [
                "success",
                "task_success",
                "indicates whether the monkey was successful on this trial",
            ],
            ["trialType", "trial_type", "trial type"],
            [
                "trialVersion",
                "trial_version",
                "should be 0 for a truly random maze "
                "(two random barriers). For a degenerate maze"
                " (real maze with some barriers randomly removed) "
                "trialVersion is >10",
            ],
            [
                "protoTrial",
                "proto_trial",
                "whether that trial was used as the prototype "
                "trial for figuring out which trials were consistent",
            ],
            [
                "primaryCondNum",
                "maze_condition",
                "The set of 27 (or 108) mazes included was composed of 3 (or 12) “subsets”. "
                "Each subset contained 3 related mazes. Each maze had 3 “versions”: the 3-target with barrier, "
                "the 1-target with barriers, and the 1-target with no barriers. These 3 versions shared the same "
                "target positions. The 3-target and 1-target versions also shared the same barrier positions. "
                "In the 3-target version, exactly one target was accessible ",
            ],
            [
                "isConsistent",
                "correct_reach",
                "tells you the result of our algorithm for determining whether this reach looked like the other reaches "
                "for this condition. To get it, we correlated the hand velocity for every pair of trials with that "
                "condition, accepted the reach with the most high correlations as prototypical, then marked as "
                "“consistent” only reaches that had a high enough correlation with the prototypical reach.",
            ],
        ]
        for event in events:
            if event[0] in self.R.dtype.fields.keys():
                trial_details_dict.append(
                    dict(
                        name=event[1],
                        data=np.array([self.R[event[0]][i][0, 0] for i in trial_nos]),
                        description=event[2],
                    )
                )

        return trial_details_dict

    def extract_behavioral_position(self, trial_nos=None):
        trial_times, _ = self.extract_trial_times()
        trial_nos = self._good_trials if trial_nos is None else trial_nos
        eye_positions = []
        hand_positions = []
        cursor_positions = []
        offset_hand_Y_jenkins = 8  # offset value, value saved is higher by this amount
        offset_hand_Y_nitschke = 24
        offset_val = (
            offset_hand_Y_nitschke if self.monkey_name == "N" else offset_hand_Y_jenkins
        )
        for no, trial_no in enumerate(trial_nos):
            timestamps = (
                trial_times[no, 0]
                + np.arange(len(self.R["EYE"][trial_no][0, 0]["X"].squeeze())) / 1000.0
            )
            eye_positions.append(
                np.array(
                    [
                        self.R["EYE"][trial_no][0, 0]["X"].squeeze(),
                        self.R["EYE"][trial_no][0, 0]["Y"].squeeze(),
                        timestamps,
                    ]
                ).T
            )
            hand_positions.append(
                np.array(
                    [
                        self.R["HAND"][trial_no][0, 0]["X"].squeeze(),
                        self.R["HAND"][trial_no][0, 0]["Y"].squeeze() - offset_val,
                        timestamps,
                    ]
                ).T
            )
            cursor_positions.append(
                np.array(
                    [
                        self.R["CURSOR"][trial_no][0, 0]["X"].squeeze(),
                        self.R["CURSOR"][trial_no][0, 0]["Y"].squeeze(),
                        timestamps,
                    ]
                ).T
            )
        return eye_positions, hand_positions, cursor_positions

    def extract_maze_data(self, trial_nos=None):
        if trial_nos is None:
            trial_nos = self._good_trials
        maze_details_list = []
        maze_details = [
            ["numFlies", "maze_num_targets", "number of targets presented"],
            ["numBarriers", "maze_num_barriers", "number of barriers presented"],
            ["novelMaze", "novel_maze", "novel maze"],
        ]
        for maze_data in maze_details:
            if maze_data[0] in self.R.dtype.fields.keys():
                maze_details_list.append(
                    dict(
                        name=maze_data[1],
                        data=np.array(
                            [self.R[maze_data[0]][i][0, 0] for i in trial_nos]
                        ),
                        description=maze_data[2],
                    )
                )
        # add target positions/size+frame locations:
        target_positions = []
        for i in trial_nos:
            target_positions.append(
                np.concatenate(
                    [
                        self.R["PARAMS"][i][0, 0]["flyX"],
                        self.R["PARAMS"][i][0, 0]["flyY"],
                    ],
                    axis=0,
                ).T
            )
        maze_details_list.append(
            dict(
                name="target_positions",
                data=target_positions,
                description="x,y position on screen of all targets presented",
                index=True,
            )
        )
        frame_positions = []
        for i in trial_nos:
            frame_positions.append(
                [
                    self.R["PARAMS"][i][0, 0]["frameLeft"],
                    self.R["PARAMS"][i][0, 0]["frameRight"],
                    self.R["PARAMS"][i][0, 0]["frameBottom"],
                    self.R["PARAMS"][i][0, 0]["frameTop"],
                    self.R["PARAMS"][i][0, 0]["frameWidth"],
                ]
            )
        maze_details_list.append(
            dict(
                name="frame_details",
                data=frame_positions,
                description="(frameLeft,right,bottom,top, width) "
                ":tell where the frame (outer rectangle of barriers) were. "
                "For those, the values are inner edges",
                index=True,
            )
        )
        hit_target_position = np.concatenate(
            [
                pos[self.R["whichFly"][no][0, 0] - 1, :][:, np.newaxis].T
                for no, pos in enumerate(target_positions)
            ]
        )
        maze_details_list.append(
            dict(
                name="hit_target_position",
                data=hit_target_position,
                description="x,y position on screen of the target hit",
            )
        )
        target_size = np.array(
            [self.R["PARAMS"][i][0, 0]["flySize"][0, 0] for i in trial_nos]
        )
        maze_details_list.append(
            dict(
                name="target_size",
                data=target_size,
                description="half width of the targets",
            )
        )
        barrier_data = []
        for trial_no in trial_nos:
            non_empty = True if len(self.R["BARRIER"][trial_no]) > 0 else False
            struct_len = self.R["BARRIER"][trial_no]["X"].shape[1] if non_empty else 0
            keys = ["X", "Y", "halfHeight", "halfWidth"]
            out_ar = np.zeros([struct_len, 4])
            for no, key in enumerate(keys):
                out_ar[:, no] = np.array(
                    [
                        self.R["BARRIER"][trial_no][key][0, i][0, 0]
                        for i in range(struct_len)
                    ]
                ).squeeze()
            barrier_data.append(out_ar)
        maze_details_list.append(
            dict(
                name="barrier_info",
                data=barrier_data,
                description="(x,y,halfwidth,halfheight)",
                index=True,
            )
        )
        return maze_details_list
