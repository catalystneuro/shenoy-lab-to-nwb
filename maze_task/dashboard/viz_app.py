import dash_core_components as dcc
import dash_html_components as html
import dash
from dash.dependencies import Input, Output, State
from pynwb import NWBHDF5IO
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from nwbwidgets.utils.timeseries import timeseries_time_to_ind


app = dash.Dash(__name__)
nwbfile = None


def trialize_time_series(trials,time_series):
    trl_ts = []
    for trial_no in range(len(trials)):
        start_id = timeseries_time_to_ind(time_series, trials['start_time'][trial_no])
        stop_id = timeseries_time_to_ind(time_series, trials['stop_time'][trial_no])
        nan_data = np.nan*np.ones(shape=time_series.data.shape[1])
        data = np.vstack([time_series.data[start_id:stop_id], nan_data])
        trl_ts.append(data)
    return trl_ts


app.layout = html.Div([
    html.H3("Display of task configurations for maze task"),
    html.Div(["NWB file location: ",
              dcc.Input(id="nwb-input",
                        type="text",
                        placeholder="input nwb file location on disk",
                        disabled=False)]),
    html.Br(),
    html.Div(['trial version selector',
        dcc.Dropdown(
            id="trial-version-dropdown",
            options=[],
            disabled=True,
            multi=True
    ),'trial type selector',
        dcc.Dropdown(
            id="trial-type-dropdown",
            options=[],
            disabled=True,
            multi=True
    ),'hit submit after selection',
        html.Button(
            id='submit-button-state',
            n_clicks=0,
            children='Submit')
    ]),
    dcc.Graph(id="trial-subplots")

])


@app.callback(
    Output('trial-version-dropdown','options'),
    Output('trial-type-dropdown','options'),
    Output('trial-version-dropdown','disabled'),
    Output('trial-type-dropdown','disabled'),
    Input('nwb-input','value')
)
def open_nwb(fileloc):
    if fileloc:
        print(fileloc)
        global nwbfile
        try:
            io = NWBHDF5IO(str(fileloc),'r')
            nwbfile = io.read()
            version_ops = [dict(label=str(i),value=i)
                           for i in set(nwbfile.trials['trial_version'].data)]
            type_ops = [dict(label=str(i), value=i)
                           for i in set(nwbfile.trials['trial_type'].data)]
        except Exception as e:
            return [],[],True,True
        return version_ops, type_ops, False, False
    else:
        return [],[],True,True


@app.callback(
    Output('trial-subplots','figure'),
    Input('submit-button-state','n_clicks'),
    State('trial-version-dropdown','value'),
    State('trial-type-dropdown','value')
)
def draw_graphs(n_clicks,versions,types):
    fig = go.Figure()
    global nwbfile
    if nwbfile is not None:
        trials = nwbfile.trials
        cursor = nwbfile.processing['behavior'].data_interfaces['Position'].spatial_series['Cursor']
        trials_version_data = trials['trial_version'].data[()]
        trials_type_data = trials['trial_type'].data[()]
        trialized_ts = trialize_time_series(trials,cursor)
        titles = [f'trial version {version}, trial type {type}'
                  for type in types for version in versions]
        fig = make_subplots(len(versions), len(types),
                            shared_xaxes=True,shared_yaxes=True,
                            vertical_spacing=0.2,
                            subplot_titles=titles,
                            horizontal_spacing=0.2)


        #plot the barriers and targets for the given trial version and trial type:
        tot_rows = len(versions)
        tot_cols = len(types)
        trial_rows = np.empty((tot_rows, tot_cols), dtype=object)
        trial_rows.fill(np.array([]))
        cursor_trajectory = np.empty((tot_rows, tot_cols), dtype=object)
        cursor_trajectory.fill(np.nan*np.ones((1, cursor.data.shape[1])))
        for trial_no in range(len(trials)):
            if trials_version_data[trial_no] in versions and trials_type_data[trial_no] in types:
                a = versions.index(trials_version_data[trial_no])
                b = types.index(trials_type_data[trial_no])
                trial_rows[a, b] = np.append(trial_rows[a, b], trial_no)
                cursor_trajectory[a, b] = np.vstack([cursor_trajectory[a, b], trialized_ts[trial_no]])

        for a in range(tot_rows):
            for b in range(tot_cols):

                trial_row = trial_rows[a, b][0]
                # plot target positions:
                target_pos = trials['target_positions'][trial_row]
                target_size = trials['target_size'][trial_row]
                fig.add_trace(go.Scattergl(x=target_pos[:, 0],
                                           y=target_pos[:, 1],
                                           showlegend=False,
                                           mode='markers',
                                           marker_size=target_size),
                              row=a + 1, col=b + 1)
                # plot barriers:
                barrier_pos = trials['barrier_info'][trial_row]
                for bar in barrier_pos:
                    fig.add_shape(type='rect',
                                  x0=bar[0] - bar[3], y0=bar[1] - bar[2],
                                  x1=bar[0] + bar[3], y1=bar[1] + bar[2],
                                  fillcolor='black',
                                  row=a + 1, col=b + 1)
                # plot trajectory:
                fig.add_trace(go.Scattergl(x=cursor_trajectory[a, b][:, 0],
                                           y=cursor_trajectory[a, b][:, 1],
                                           showlegend=False,
                                           line_color='red'),
                              row=a + 1, col=b + 1)

        fig.update_layout(height=1000,width=1000)
    return fig


if __name__ == '__main__':
    app.run_server(debug=True)