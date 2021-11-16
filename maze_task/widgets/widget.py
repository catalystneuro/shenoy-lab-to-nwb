from nwbwidgets.view import default_neurodata_vis_spec
from ipywidgets import widgets, Layout
from pynwb import TimeSeries
from pynwb.epoch import TimeIntervals
import numpy as np
import plotly.graph_objects as go
from nwbwidgets.utils.timeseries import timeseries_time_to_ind
from nwbwidgets import base
import pynwb
import threading


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
        self.progress = widgets.FloatProgress(value=0.0, min=0.0, max=1.0, disabled=True)
        self.plot_button.on_click(self.plot_trials_async)
        self.set_children(go.FigureWidget())
        
    def set_children(self,fig):
        self.children = [widgets.HBox(children=(self.trial_type_dd,
                                                self.trial_version_dd)),
                         self.plot_button,
                         self.progress,
                         fig]

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

    def plot_trials_async(self, change):
        th = threading.Thread(target=self.plot_trials)
        th.start()

    def plot_trials(self):
        titles = [f'version {version},type {type}'
                  for type in self.types for version in self.versions]
        tot_rows = len(self.types)
        tot_cols = len(self.versions)
        fig = go.FigureWidget()
        fig.set_subplots(tot_rows,tot_cols,
                         shared_xaxes=False,
                         shared_yaxes=False,
                         subplot_titles=titles,
                         horizontal_spacing=0.2)
        fig.update_layout(autosize=True,height=350*tot_rows)
        trial_rows = np.empty((tot_rows,tot_cols),dtype=object)
        trial_rows.fill(np.array([]))
        cursor_trajectory = np.empty((tot_rows,tot_cols),dtype=object)
        cursor_trajectory.fill(np.nan*np.ones((1,self.time_series.data.shape[1])))
        for trial_no in range(len(self.trials)):
            if self.trials_version_data[trial_no] in self.versions and self.trials_type_data[trial_no] in self.types:
                b = self.versions.index(self.trials_version_data[trial_no])
                a = self.types.index(self.trials_type_data[trial_no])
                trial_rows[a,b] = np.append(trial_rows[a,b], trial_no)
                cursor_trajectory[a,b] = np.vstack([cursor_trajectory[a,b], self.trialized_ts[trial_no]])

        c = 0
        self.progress.disabled = False
        for a in range(tot_rows):
            for b in range(tot_cols):
                c+=1
                self.progress.value = c/(tot_rows*tot_cols)
                self.progress.description = f'Ploting {self.progress.value*100:.0f} %'
                if len(trial_rows[a,b]) == 0:
                    continue
                trial_row = trial_rows[a,b][0]
                #plot target positions:
                target_pos = self.trials['target_positions'][trial_row]
                target_size = self.trials['target_size'][trial_row]
                fig.add_trace(go.Scattergl(x=target_pos[:, 0],
                                           y=target_pos[:, 1],
                                           showlegend=False,
                                           mode='markers',
                                           marker_size=target_size),
                                      row=a + 1, col=b + 1)
                #plot barriers:
                barrier_pos = self.trials['barrier_info'][trial_row]
                for bar in barrier_pos:
                    fig.add_shape(type='rect',
                                  x0=bar[0] - bar[3], y0=bar[1] - bar[2],
                                  x1=bar[0] + bar[3], y1=bar[1] + bar[2],
                                  fillcolor='black',
                                  row=a + 1, col=b + 1)
                #plot trajectory:
                fig.add_trace(go.Scattergl(x=cursor_trajectory[a,b][:, 0],
                                           y=cursor_trajectory[a,b][:, 1],
                                           showlegend=False,
                                           line_color='red'),
                                      row=a + 1, col=b + 1)
                fig.update_xaxes(constrain='domain',row=a + 1, col=b + 1)
                x_str = 'x' if a == 0 and b == 0 else f'x{tot_cols*(a) + (b+1)}'
                fig.update_yaxes(scaleanchor=x_str, scaleratio=1, row=a+1, col=b+1)
        self.set_children(fig)


def load_maze_task_widget(node):
    default_neurodata_vis_spec[pynwb.epoch.TimeIntervals] = dict({
            "trials table":base.render_dataframe,
            "task_plot":MazeTaskWidget
        })
    return base.nwb2widget(node, default_neurodata_vis_spec)
