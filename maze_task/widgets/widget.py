from nwbwidgets.view import default_neurodata_vis_spec
from ipywidgets import widgets, Layout
from pynwb import TimeSeries
from pynwb.epoch import TimeIntervals
import numpy as np
import plotly.graph_objects as go
from nwbwidgets.utils.timeseries import timeseries_time_to_ind
from nwbwidgets import (
    base,
    ecephys,
)
import pynwb
from tqdm import tqdm_notebook


class MazeTaskWidget(widgets.VBox):
    def __init__(self,
                 trials: TimeIntervals,
                 timeseries: TimeSeries=None,
                 ):
        super().__init__()
        self.versions = None
        self.types = None
        self.trials = trials
        if timeseries is None:
            self.time_series = self.get_cursor_ts()
        else:
            self.time_series = timeseries
        self.trialized_ts = self.trialize_time_series()
        self.trials_version_data = self.trials['trial_version'].data[()]
        self.trials_type_data = self.trials['trial_type'].data[()]
        self.trial_type_dd = widgets.SelectMultiple(
            options=np.unique(self.trials_type_data),
            value=(),
            description="trial type selector",
            layout=Layout(max_width="120px"),
        )
        self.trial_type_dd.observe(self.trial_type_dd_observer)

        self.trial_version_dd = widgets.SelectMultiple(
            options=np.unique(self.trials_version_data),
            value=(),
            description="trial versions selector",
            layout=Layout(max_width="120px"),
        )
        self.trial_version_dd.observe(self.trial_version_dd_observer)

        self.plot_button = widgets.Button(
            description='Click to plot'
        )
        self.figure = go.FigureWidget()
        self.plot_button.on_click(self.plot_trials)
        # self.children = (widgets.VBox(children=(widgets.VBox(children=(self.trial_type_dd,
        #                                        self.trial_version_dd)),
        #                               self.plot_button,
        #                               self.figure)),)
        self.children = [self.trial_type_dd,
                         self.trial_version_dd,
                         self.plot_button,
                         self.figure]

    def trialize_time_series(self):
        trl_ts = []
        for trial_no in range(len(self.trials)):
            start_id = timeseries_time_to_ind(self.time_series, self.trials['start_time'][trial_no])
            stop_id = timeseries_time_to_ind(self.time_series, self.trials['stop_time'][trial_no])
            nan_data = np.nan*np.ones(shape=self.time_series.data.shape[1])
            data = np.vstack([self.time_series.data[start_id:stop_id],nan_data])
            trl_ts.append(data)
        return trl_ts

    def get_cursor_ts(self):
        nwbfile = self.trials.get_ancestor("NWBFile")
        try:
            cursor = nwbfile.processing['behavior'].data_interfaces['Position'].spatial_series['Cursor']
        except Exception as e:
            cursor = None
        return cursor

    def trial_type_dd_observer(self,change):
        if change['type'] == 'change':
            self.types = self.trial_type_dd.value

    def trial_version_dd_observer(self, change):
        if change['type'] == 'change':
            self.versions = self.trial_version_dd.value

    def plot_trials(self,change):
        self.figure = go.FigureWidget() if len(self.figure.data)>0 else self.figure
        titles = [f'trial version {version}, trial type {type}'
                  for type in self.types for version in self.versions]
        tot_rows = len(self.versions)
        tot_cols = len(self.types)
        self.figure.set_subplots(tot_rows,tot_cols,
                            shared_xaxes=False,
                            shared_yaxes=False,
                            subplot_titles=titles)

        # for a, trl_ver in enumerate(tqdm_notebook(self.versions)):
        #     for b,trl_type in enumerate(self.types):
        #         if np.sum(np.logical_and(self.trials_version_data==trl_ver,
        #                                  self.trials_type_data==trl_type))>0:
        #             rel_row = np.where(np.logical_and(self.trials_version_data==trl_ver,
        #                                               self.trials_type_data==trl_type))[0][0]
        #             target_pos = self.trials['target_positions'][rel_row]
        #             barrier_pos = self.trials['barrier_info'][rel_row]
        #             target_size = self.trials['target_size'][rel_row]
        #             self.figure.add_trace(go.Scattergl(x=target_pos[:, 0], y=target_pos[:, 1],showlegend=False),
        #                           row=a+1,col=b+1)
        #             with self.figure.batch_update():
        #                 for bar in barrier_pos:
        #                     self.figure.add_shape(type='rect',
        #                                   x0=bar[0]-bar[3],y0=bar[1]-bar[2],
        #                                   x1=bar[0]+bar[3],y1=bar[1]+bar[2],
        #                                   fillcolor='black',
        #                                   row=a+1,col=b+1)
        trial_rows = []
        cursor_trajectory = []
        for i in range(tot_rows*tot_cols):
            cursor_trajectory.append([])
            trial_rows.append([])
        for trial_no in range(len(self.trials)):
            if self.trials_version_data[trial_no] in self.versions and self.trials_type_data[trial_no] in self.types:
                a = self.versions.index(self.trials_version_data[trial_no])+1
                b = self.types.index(self.trials_type_data[trial_no])+1
                trial_rows[a*b-1].append(trial_no)
                cursor_trajectory[a*b-1].append(self.trialized_ts[trial_no])

        for a in range(tot_rows):
            for b in range(tot_cols):
                with self.figure.batch_update():
                    trial_row = trial_rows[(a+1)*(b+1)-1][0]
                    #plot target positions:
                    target_pos = self.trials['target_positions'][trial_row]

                    self.figure.add_trace(go.Scattergl(x=target_pos[:, 0], y=target_pos[:, 1], showlegend=False),
                                          row=a + 1, col=b + 1)
                    #plot barriers:
                    barrier_pos = self.trials['barrier_info'][trial_row]
                    for bar in barrier_pos:
                        self.figure.add_shape(type='rect',
                                              x0=bar[0] - bar[3], y0=bar[1] - bar[2],
                                              x1=bar[0] + bar[3], y1=bar[1] + bar[2],
                                              fillcolor='black',
                                              row=a + 1, col=b + 1)
                    #plot trajectory:
                    data = np.concatenate(cursor_trajectory[a*b],axis=0)
                    self.figure.add_trace(go.Scattergl(x=data[:, 0],
                                                       y=data[:, 1],
                                                       showlegend=False,
                                                       line_color='red'),
                                          row=a + 1, col=b + 1)
            # for trial_no in tqdm_notebook(range(len(self.trials))):
            #     if self.trials_version_data[trial_no] in self.versions and self.trials_type_data[trial_no] in self.types:
            #         a = self.versions.index(self.trials_version_data[trial_no])
            #         b = self.types.index(self.trials_type_data[trial_no])
            #         start_id = timeseries_time_to_ind(self.time_series,self.trials['start_time'][trial_no])
            #         stop_id = timeseries_time_to_ind(self.time_series, self.trials['stop_time'][trial_no])
            #         cursor_trajectory_trial = self.time_series.data[start_id:stop_id]
            #         self.figure.add_trace(go.Scattergl(x=cursor_trajectory_trial[:,0],
            #                                    y=cursor_trajectory_trial[:,1],
            #                                    showlegend=False,
            #                                    line_color='red'),
            #                       row=a+1,col=b+1)
        # self.figure.update_layout(height=1000,width=1000)


def load_maze_task_widget(node):
    default_neurodata_vis_spec[pynwb.epoch.TimeIntervals] = dict({
            "trials table":base.render_dataframe,
            "task_plot":MazeTaskWidget
        })
    return base.nwb2widget(node, default_neurodata_vis_spec)
