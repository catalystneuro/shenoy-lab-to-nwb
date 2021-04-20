from churchland_nature_monkey.matextractor import MatDataExtractor
import numpy as np
from pathlib import Path


rfileloc = Path(r'C:\Users\Saksham\Documents\NWB\shenoy\data\Jenkins\SpikeSorted\0912\RC,2009-09-12,1-2.mat')
raw_file_loc = Path(r'C:\Users\Saksham\Documents\NWB\shenoy\data\Jenkins\2009-09-12')
extractor = MatDataExtractor(rfileloc, raw_file_loc)
R_fields = extractor.R.dtype.names

trial_ids = extractor._get_trial_ids()
trial_spike_times = extractor._extract_unit_spike_times()
trial_times, split_id = extractor._extract_trial_times()
inter_trial_intervals = np.array([trial_times[i+1,0]-trial_times[i,1] for i in range(extractor._no_trials-1)])
trial_events = extractor._extract_trial_events()
trial_details = extractor._extract_trial_details()
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
eye_positions, hand_positions, cursor_positions = extractor._create_behavioral_position()
lfp_data = extractor.extract_lfp()