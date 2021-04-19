import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from pynwb import NWBHDF5IO, NWBFile
from pynwb.file import Subject
from datetime import datetime
import uuid
import neo
from tqdm import tqdm
import pynwb


def write_nwb(raw_file_loc,
              eye_positions, hand_positions, cursor_positions,
              trial_events, trial_details, trial_times, trial_spike_times,
              lfp_data):

    nwbfile_loc = raw_file_loc/f'{raw_file_loc.name}_nwb.nwb'

    with NWBHDF5IO(str(nwbfile_loc),'w') as io:
        session_date = datetime.strptime(raw_file_loc.name, '%Y-%m-%d')
        subject = Subject(sex='M', species='Macaca mulatta', subject_id=raw_file_loc.parent.name)
        nwbfile = NWBFile(session_description='',identifier=str(uuid.uuid4()),
                          session_start_time=session_date, experimenter='Matt Kaufmann',
                          experiment_description='',institution='Stanford',
                          related_publications='10.1038/nature11129',
                          subject=subject)
        #create electrode group:
        device = nwbfile.create_device(name='Utah Array',description='96 channel utah array',manufacturer='BlackRock')
        m1 = nwbfile.create_electrode_group(name='M1 array', description='', device=device, location='M1')
        pmd = nwbfile.create_electrode_group(name='PMd array', description='', device=device, location='PMd')
        #create electrodes tabls:
        for electrode_no in range(192):
            if electrode_no>95:
                group = m1
                location = 'M1'
            else:
                group = pmd
                location = 'PMd'
            nwbfile.add_electrode(x=np.nan,y=np.nan,z=np.nan,imp=np.nan,
                                  location=location,filtering='1000Hz',
                                  group=group,id=electrode_no)
        electrode_table_region = nwbfile.create_electrode_table_region(list(np.arange(192)), 'M1 and PMd electrodes combined')
        lfp_es = pynwb.ecephys.ElectricalSeries(name='lfp',data=lfp_data,electrodes=electrode_table_region,
                                                starting_time=0.0,rate=1000.0)
        #crate processing module:
        ephys_mod = nwbfile.create_processing_module('ecephys', 'ephys - filtered data')
        ephys_mod.add(pynwb.ecephys.LFP(electrical_series=lfp_es))
        #adding behavior: eye, cursor position, hand position.
        beh_mod = nwbfile.create_processing_module('behavior', 'contains monkey movement data')
        position_container = pynwb.behavior.Position()
        eye_position_concat = np.concatenate(eye_positions,axis=0)
        cursor_position_concat = np.concatenate(cursor_positions, axis=0)
        hand_position_concat = np.concatenate(hand_positions, axis=0)
        eye_ts = position_container.create_spatial_series('Eye',data=eye_position_concat[:,:2],
                                                 timestamps=eye_position_concat[:,2],
                                                          reference_frame='screen lower left corner 0,0')
        hand_ts = position_container.create_spatial_series('Hand', data=hand_position_concat[:, :2],
                                                 timestamps=hand_position_concat[:, 2],
                                                           reference_frame='screen lower left corner 0,0')
        cursor_ts = position_container.create_spatial_series('Cursor', data=cursor_position_concat[:, :2],
                                                 timestamps=cursor_position_concat[:, 2],
                                                             reference_frame='screen lower left corner 0,0')
        beh_mod.add(position_container)
        #create acquisition: target positions.

        #create trials table:
        for trial_no in range(trial_times.shape[0]):
            nwbfile.add_trial(start_time=trial_times[trial_no,0],
                              stop_time=trial_times[trial_no,1],
                              timeseries=[eye_ts, hand_ts, cursor_ts])
        for col_details in trial_events:
            nwbfile.add_trial_column(**col_details)
        for col_details in trial_details:
            nwbfile.add_trial_column(**col_details)
        nwbfile.add_trial_column(name='SpikeTimes',
                                 description='times of threshold crossings',
                                 data=trial_spike_times)

        # write file:
        io.write(nwbfile)