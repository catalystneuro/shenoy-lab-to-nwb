from churchland_nature_monkey.matextractor import MatDataExtractor
import numpy as np
from pathlib import Path
from tqdm import tqdm
import neo

rfileloc = r'C:\Users\Saksham\Documents\NWB\shenoy\data\Jenkins\SpikeSorted\0912\RC,2009-09-12,1-2.mat'

extractor = MatDataExtractor(rfileloc)
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
        channel_ts.extend(trial_spike_times[trialno][chan])
    unit_spike_times.append(np.array(channel_ts))

eye_positions, hand_positions, cursor_positions = extractor._create_behavioral_position()

## write to NWB:
raw_files_names = [['A001','B001'],['A002','B002']]
raw_file_loc = Path(r'C:\Users\Saksham\Documents\NWB\shenoy\data\Jenkins\2009-09-12')
lfps=[None]*len(raw_files_names)
for no, data_part in enumerate(tqdm(raw_files_names)):
    electrodes = [None]*2
    for elec_no, electrode in enumerate((data_part)):
        nev_file = raw_file_loc/f'datafile{electrode}.nev'
        bk = neo.BlackrockIO(str(nev_file))
        electrodes[elec_no] = bk.get_analogsignal_chunk()
        # if ts_all[no] is None:
        #     ts = bk.get_signal_t_start(block_index=0, seg_index=0) + np.arange(electrodes[elec_no].shape[0]/1000.0)
        #     if no>1:
        #         ts=ts+ts_all[0][-1] + 1/1000.0
        #     ts_all[no] = ts
    elec_common_len = np.min([electrodes[i].shape[0] for i in range(2)])
    electrodes = [electrodes[i][:elec_common_len, :] for i in range(2)]
    lfps[no] = np.concatenate(electrodes, axis=1)
lfp_data = np.concatenate(lfps, axis=0) if len(lfps) > 1 else lfps[0]