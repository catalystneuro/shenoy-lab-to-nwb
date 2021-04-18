import pynwb.ecephys
from churchland_nature_monkey.matextractor import MatDataExtractor
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from pynwb import NWBHDF5IO, NWBFile
from pynwb.file import Subject
from datetime import datetime
import uuid
import neo
from tqdm import tqdm


rfileloc = r'C:\Users\Saksham\Documents\NWB\shenoy\data\Jenkins\SpikeSorted\0912\RC,2009-09-12,1-2.mat'

extractor = MatDataExtractor(rfileloc)
R_fields = extractor.R.dtype.names

trial_ids = extractor._get_trial_ids()
trial_spike_times = extractor._extract_unit_spike_times()
trial_times, split_id = extractor._extract_trial_times()
inter_trial_intervals = np.array([trial_times[i+1,0]-trial_times[i,1] for i in range(extractor._no_trials-1)])
trial_events = extractor._extract_trial_events()

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
nwbfile_loc = raw_file_loc/f'{raw_file_loc.name}_nwb.nwb'

with NWBHDF5IO(str(nwbfile_loc),'w') as io:
    session_date = datetime.strptime(raw_file_loc.name, '%Y-%m-%d')
    subject = Subject(sex='M', species='Macaca mulatta', subject_id=raw_file_loc.parent.name)
    nwbfile = NWBFile(session_description='',identifier=str(uuid.uuid4()),
                      session_start_time=session_date, experimenter='Matt Kaufmann',
                      experiment_description='',institution='Stanford',
                      related_publications='10.1038/nature11129')
    lfps=[None]*len(raw_files_names)
    # ts_all = [None]*len(raw_files_names)
    # getlfp:
    for no,data_part in enumerate(tqdm(raw_files_names)):
        electrodes = [None]*2
        for elec_no,electrode in enumerate((data_part)):
            nev_file = raw_file_loc/f'datafile{electrode}.nev'
            bk = neo.BlackrockIO(nev_file)
            electrodes[elec_no] = bk.get_analogsignal_chunk()
            # if ts_all[no] is None:
            #     ts = bk.get_signal_t_start(block_index=0, seg_index=0) + np.arange(electrodes[elec_no].shape[0]/1000.0)
            #     if no>1:
            #         ts=ts+ts_all[0][-1] + 1/1000.0
            #     ts_all[no] = ts
        lfps[no] = np.concatenate(electrodes,axis=1)
    lfp_data = np.concatenate(lfps,axis=0) if len(lfps)>1 else lfps[0]
    # ts = np.concatenate(ts_all)
    #create electrode group:
    device = pynwb.device.Device(name='Utah Array',description='96 channel utah array',manufacturer='BlackRock')
    m1 = pynwb.ecephys.ElectrodeGroup(name='Utah Array', description='', device=device, location='M1')
    pmd = pynwb.ecephys.ElectrodeGroup(name='Utah Array', description='', device=device, location='PMd')
    #create electrodes tabls:
    for electrode_no in range(192):
        if electrode_no<96:
            group = m1
            location = 'M1'
        else:
            group = pmd
            location = 'PMd'
        nwbfile.add_electrode(x=np.nan,y=np.nan,z=np.nan,
                              location=location,filtering='1000Hz',
                              group=group,id=electrode_no)
    lfp_es = pynwb.ecephys.ElectricalSeries(name='lfp',data=lfp_data,electrodes=np.arange(192),
                                            starting_time=0.0,rate=1000.0)
    nwbfile.add_acquisition(pynwb.ecephys.LFP(electrical_series=lfp_es))