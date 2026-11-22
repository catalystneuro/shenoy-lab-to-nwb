"""
Placement of recording segments on the session timeline in the maze_task_unsorted conversion, with made-up
segment durations, trial times and array B clock maps.
"""
import numpy as np
import pytest

from maze_task_unsorted.matextractor import MatDataExtractor


def _cerebus_info(start, end):
    info = np.empty((1, 1), dtype=[("startTime", object), ("endTime", object)])
    info[0, 0] = (np.array([[start]]), np.array([[end]]))
    return info


def make_extractor(trial_starts_a, clock_maps, trial_duration=2.0):
    """
    An extractor with one list of trial start times per segment, on that segment's array A clock. The array B
    start times follow from each segment's clock map (slope, intercept), with time_A = slope * time_B + intercept.
    """
    extractor = MatDataExtractor.__new__(MatDataExtractor)
    info_a, info_b = [], []
    for starts, (slope, intercept) in zip(trial_starts_a, clock_maps):
        for start in starts:
            info_a.append(_cerebus_info(start, start + trial_duration))
            start_b = (start - intercept) / slope
            info_b.append(_cerebus_info(start_b, start_b + trial_duration / slope))
    extractor.R = {"CerebusInfoA": info_a, "CerebusInfoB": info_b}
    extractor._good_trials = list(range(len(info_a)))
    extractor.segment_durations = None
    extractor.array_b_time_ranges = None
    return extractor


TRIAL_STARTS = [np.arange(10.0, 90.0, 4.0)] * 3  # mean inter-trial interval 2 s, last trial ends at 88 s
A_DURATIONS = [100.0, 100.0, 100.0]


def array_ranges(extractor, offsets):
    """(start, end) of each segment's array A and array B recording on the session timeline."""
    clock_map = extractor.extract_array_b_clock_map()
    ranges_a = [(offset, offset + duration) for offset, duration in zip(offsets, extractor.segment_durations)]
    ranges_b = [
        (offset + intercept + slope * b_start, offset + intercept + slope * b_end)
        for offset, (slope, intercept), (b_start, b_end) in zip(offsets, clock_map, extractor.array_b_time_ranges)
    ]
    return ranges_a, ranges_b


def offsets_without_array_b(extractor):
    array_b_time_ranges, extractor.array_b_time_ranges = extractor.array_b_time_ranges, None
    _, offsets = extractor.extract_trial_times()
    extractor.array_b_time_ranges = array_b_time_ranges
    return offsets


def assert_no_overlap(ranges):
    for previous, current in zip(ranges[:-1], ranges[1:]):
        assert current[0] >= previous[1] - 1e-9


def test_array_b_longer_than_array_a_does_not_overlap():
    clock_maps = [(1.0000145, 0.0219), (1.0000145, 0.0003), (1.0000145, 0.0027)]
    extractor = make_extractor(TRIAL_STARTS, clock_maps)
    extractor.segment_durations = A_DURATIONS
    extractor.array_b_time_ranges = [(0.0, 101.5), (0.0, 101.8), (0.0, 101.2)]

    old_offsets = offsets_without_array_b(extractor)
    np.testing.assert_allclose(old_offsets, [0.0, 100.0, 200.0])
    _, old_ranges_b = array_ranges(extractor, old_offsets)
    assert old_ranges_b[1][0] < old_ranges_b[0][1]  # the overlap this change removes

    trial_times, offsets = extractor.extract_trial_times()
    ranges_a, ranges_b = array_ranges(extractor, offsets)
    assert_no_overlap(ranges_a)
    assert_no_overlap(ranges_b)
    # array B is contiguous: each recording starts where the previous one ends
    np.testing.assert_allclose([r[0] for r in ranges_b[1:]], [r[1] for r in ranges_b[:-1]])
    assert np.all(np.diff(trial_times[:, 0]) > 0)
    assert np.all(trial_times[1:, 0] >= trial_times[:-1, 1])


def test_array_b_inside_array_a_keeps_offsets():
    clock_maps = [(1.0000096, 0.0056), (1.0000096, 0.0041), (1.0000096, 0.0070)]
    extractor = make_extractor(TRIAL_STARTS, clock_maps)
    extractor.segment_durations = A_DURATIONS
    extractor.array_b_time_ranges = [(0.0, 99.2), (0.0, 99.0), (0.0, 99.5)]

    trial_times, offsets = extractor.extract_trial_times()
    np.testing.assert_array_equal(offsets, offsets_without_array_b(extractor))
    np.testing.assert_allclose(offsets, [0.0, 100.0, 200.0])
    ranges_a, ranges_b = array_ranges(extractor, offsets)
    assert_no_overlap(ranges_a)
    assert_no_overlap(ranges_b)


def test_negative_intercept_with_array_b_inside_previous_segment_keeps_offsets():
    # like Jenkins 2009-09-12: array B of the second segment starts 1.5 ms before its array A recording, but array
    # B of the first segment ends long before that, so neither array overlaps itself
    clock_maps = [(1.0000096, 0.0056), (1.0000096, -0.0015)]
    extractor = make_extractor(TRIAL_STARTS[:2], clock_maps)
    extractor.segment_durations = A_DURATIONS[:2]
    extractor.array_b_time_ranges = [(0.0, 99.2), (0.0, 100.5)]

    _, offsets = extractor.extract_trial_times()
    np.testing.assert_array_equal(offsets, offsets_without_array_b(extractor))


def test_negative_intercept_moves_the_next_segment_by_the_intercept():
    # array B of the first segment ends exactly where array A does, and array B of the second segment starts
    # 10 ms before its array A recording, so the second segment moves 10 ms later
    intercept = -0.010
    clock_maps = [(1.0, intercept), (1.0, intercept)]
    extractor = make_extractor(TRIAL_STARTS[:2], clock_maps)
    extractor.segment_durations = A_DURATIONS[:2]
    extractor.array_b_time_ranges = [(0.0, 100.0 - intercept), (0.0, 50.0)]

    _, offsets = extractor.extract_trial_times()
    np.testing.assert_allclose(offsets, [0.0, 100.0 - intercept])
    _, ranges_b = array_ranges(extractor, offsets)
    assert ranges_b[1][0] == pytest.approx(ranges_b[0][1])
    assert ranges_b[1][0] == pytest.approx(100.0)  # the end of the first segment's array A recording


def test_long_gap_between_trials_keeps_offsets():
    # the next segment's first trial comes more than one recording length after the previous segment's last
    # trial, so the recordings do not move it
    clock_maps = [(1.0000145, -0.003), (1.0000145, -0.009)]
    extractor = make_extractor(TRIAL_STARTS[:2], clock_maps)
    extractor.segment_durations = [60.0, 60.0]
    extractor.array_b_time_ranges = [(0.0, 61.5), (0.0, 61.5)]

    _, offsets = extractor.extract_trial_times()
    np.testing.assert_allclose(offsets, [0.0, 88.0 + 2.0 - 10.0])
    np.testing.assert_array_equal(offsets, offsets_without_array_b(extractor))
