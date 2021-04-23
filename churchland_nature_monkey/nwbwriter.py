import numpy as np
from pathlib import Path
from pynwb import NWBHDF5IO, NWBFile
from pynwb.file import Subject
from datetime import datetime
import uuid
import pynwb
from hdmf.backends.hdf5.h5_utils import H5DataIO
from hdmf.data_utils import DataChunkIterator
from pynwb.base import DynamicTable
import pytz


def write_nwb(raw_file_loc,
              eye_positions, hand_positions, cursor_positions,
              trial_events, trial_details, trial_times, unit_spike_times, maze_details,
              lfp_data,
              unit_lookup, array_lookup):

    nwbfile_loc = raw_file_loc/f'{raw_file_loc.name}_nwb.nwb'

    with NWBHDF5IO(str(nwbfile_loc),'w') as io:
        session_date = pytz.timezone('US/Pacific').localize(datetime.strptime(raw_file_loc.name, '%Y-%m-%d'))
        subject = Subject(sex='M', species='Macaca mulatta', subject_id=raw_file_loc.parent.name)
        nwbfile = NWBFile(session_description='',identifier=str(uuid.uuid4()),
                          session_start_time=session_date, experimenter='Matt Kaufmann',
                          experiment_description='',institution='Stanford University',
                          related_publications='10.1038/nature11129',
                          subject=subject)
        #create electrode group:
        device_m1 = nwbfile.create_device(name='Utah Array(M1)',
                                       description='96 channel utah array',
                                       manufacturer='BlackRock Microsystems')
        device_pmd = nwbfile.create_device(name='Utah Array(PMd)',
                                       description='96 channel utah array',
                                       manufacturer='BlackRock Microsystems')
        m1 = nwbfile.create_electrode_group(name='M1 array', description='', device=device_m1, location='M1')
        pmd = nwbfile.create_electrode_group(name='PMd array', description='', device=device_pmd, location='PMd')
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
        #create lfp:

        def lfp_iterator():
            trim_len = [0]
            for blk_no, blk in enumerate(lfp_data):
                trim_len.append(np.min([i.shape[0] for i in blk]))
            #iterate over each time:
            for time_id in range(np.sum(trim_len)-1):
                active_blk = np.max(np.where(np.cumsum(trim_len) <= time_id)[0])
                time_id_corr = trim_len[active_blk]
                block = lfp_data[active_blk]
                out_val = []
                time_id_corrected = time_id - time_id_corr
                for channel_group in block:
                    out_val.append(channel_group[time_id_corrected, :].squeeze())
                yield np.concatenate(out_val)

        lfp_es = pynwb.ecephys.ElectricalSeries(name='lfp',
                                                data=H5DataIO(
                                                    DataChunkIterator(lfp_iterator(), buffer_size=100000)
                                                    ,compression=True,compression_opts=9),
                                                electrodes=electrode_table_region,
                                                starting_time=0.0,rate=1000.0)
        ephys_mod = nwbfile.create_processing_module('ecephys', 'ephys - filtered data')
        ephys_mod.add(pynwb.ecephys.LFP(electrical_series=lfp_es))
        #adding behavior: eye, cursor position, hand position.
        beh_mod = nwbfile.create_processing_module('behavior', 'contains monkey movement data')
        position_container = pynwb.behavior.Position()
        eye_data = np.concatenate(eye_positions,axis=0)
        cursor_data = np.concatenate(cursor_positions,axis=0)
        hand_data = np.concatenate(hand_positions,axis=0)
        eye_ts = position_container.create_spatial_series('Eye',
                                                          data=eye_data[:,:2],
                                                          timestamps=eye_data[:,2],
                                                          reference_frame='screen center',
                                                          conversion=np.nan)
        hand_ts = position_container.create_spatial_series('Hand',
                                                           data=hand_data[:,:2],
                                                           timestamps=hand_data[:, 2],
                                                           reference_frame='screen center',
                                                           conversion=np.nan)
        cursor_ts = position_container.create_spatial_series('Cursor',
                                                             data=cursor_data[:,:2],
                                                             timestamps=cursor_data[:, 2],
                                                             reference_frame='screen center',
                                                             conversion=np.nan)
        beh_mod.add(position_container)
        #create trials table:
        for col_details in trial_events+trial_details+maze_details:
            col_det = {i:col_details[i] for i in col_details if 'data' not in i}
            nwbfile.add_trial_column(**col_det)
        for trial_no in range(trial_times.shape[0]):
            col_details_dict = {i['name']:i['data'][trial_no] for i in trial_events+trial_details+maze_details}
            col_details_dict.update(start_time=trial_times[trial_no,0],
                                    stop_time=trial_times[trial_no,1],
                                    timeseries=[eye_ts, hand_ts, cursor_ts, lfp_es])
            nwbfile.add_trial(**col_details_dict)

        # create units table:
        unit_lookup_corrected = [list(np.array([ch_id-1]) + 96) if array_lookup[no] == 2 else [ch_id-1]
                                 for no, ch_id in enumerate(unit_lookup)]
        electrode_group_list = [pmd, m1]
        for unit_no in range(len(unit_spike_times)):
            nwbfile.add_unit(spike_times=unit_spike_times[unit_no],
                             electrodes=[unit_lookup_corrected[unit_no]],
                             electrode_group=electrode_group_list[array_lookup[unit_no]-1])
        # write file:
        print('writing to disc')
        io.write(nwbfile)