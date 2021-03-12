from churchland_nature_monkey.matextractor import MatDataExtractor
import numpy as np
import matplotlib.pyplot as plt

rfileloc = r'C:\Users\Saksham\Documents\NWB\shenoy\data\JMaze-LFADS\RC,2009-09-18,1-2,good-ss.mat'
nfileloc = r'C:\Users\Saksham\Documents\NWB\shenoy\data\JMaze-LFADS\N,2009-09-18,1-2,good-ss.mat'

extractor = MatDataExtractor(rfileloc, nfileloc)

trial_ids = extractor._get_trial_ids()
unit_spike_times = extractor._extract_unit_spike_times()
trial_times = extractor._extract_trial_times()
inter_trial_intervals = np.array([trial_times[i+1,0]-trial_times[i,1] for i in range(extractor._no_trials-1)])
trial_change_id = np.where(inter_trial_intervals<0)[0][0]
inter_trial_intervals = np.delete(inter_trial_intervals, trial_change_id)
trial_events = extractor._extract_trial_events()