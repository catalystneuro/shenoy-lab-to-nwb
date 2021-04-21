from churchland_nature_monkey.matextractor import MatDataExtractor
from churchland_nature_monkey.nwbwriter import write_nwb
import numpy as np
from pathlib import Path

folder = r"C:\Users\Saksham\Documents\NWB\shenoy\data\Jenkins\SpikeSorted\0912"
extractor = MatDataExtractor(folder)
R_fields = extractor.R.dtype.names

trial_ids = extractor.get_trial_ids()
trial_spike_times = extractor.extract_unit_spike_times()
trial_times, split_id = extractor.extract_trial_times()
inter_trial_intervals = np.array([trial_times[i+1,0]-trial_times[i,1] for i in range(extractor._no_trials-1)])
trial_events = extractor.extract_trial_events()
trial_details = extractor.extract_trial_details()
maze_details = extractor.extract_maze_data()
# extract channel spike times independent of trial:
unit_spike_times = []
for chan in range(len(trial_spike_times[0])):
    channel_ts = []
    for trialno in range(extractor._no_trials):
        channel_ts.extend(trial_spike_times[trialno][chan]+trial_times[trialno,0])
        if trial_spike_times[trialno][chan].size>0:
            assert trial_spike_times[trialno][chan][-1]<trial_times[trialno,1]
    unit_spike_times.append(np.array(channel_ts))
unit_lookup = extractor.SU['unitLookup'][0,0][:,0]
array_lookup = extractor.SU['arrayLookup'][0,0][:,0]
eye_positions, hand_positions, cursor_positions = extractor.extract_behavioral_position()
lfp_data = extractor.extract_lfp()

write_nwb(extractor.nsx_loc,
              eye_positions, hand_positions, cursor_positions,
              trial_events, trial_details, trial_times, unit_spike_times, maze_details,
              lfp_data,
              unit_lookup, array_lookup)