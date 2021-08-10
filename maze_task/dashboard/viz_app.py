import dash_core_components as dcc
import dash_html_components as html
import dash
from dash.dependencies import Input, Output, State
from pynwb import NWBHDF5IO
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from nwbwidgets.utils.timeseries import timeseries_time_to_ind
import dash_labs as dl
from uuid import uuid4
import diskcache
from flask_caching import Cache

## Diskcache
import diskcache
launch_uid = uuid4()
cache = diskcache.Cache("./cache")
long_callback_manager = dl.plugins.DiskcacheCachingCallbackManager(
    cache, cache_by=[lambda: launch_uid], expire=60,
)

app = dash.Dash(
    __name__,
    plugins=[
        dl.plugins.FlexibleCallbacks(),
        dl.plugins.HiddenComponents(),
        dl.plugins.LongCallback(long_callback_manager),
    ],
)

CACHE_CONFIG = {
    # try 'filesystem' if you don't want to setup redis
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory',
}
cache = Cache()
cache.init_app(app.server, config=CACHE_CONFIG)


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
            children='Submit',
            disabled=True),
        html.Button(
            id='cancel-button-state',
            n_clicks=0,
            children='Cancel Plot',
            disabled=True),
        html.Progress(id="progress_bar_extraction"),
        # html.Progress(id="progress_bar_plotting")
    ]),
    dcc.Graph(id="trial-subplots"),
])


@cache.memoize()
def global_store(fileloc):
    try:
        io = NWBHDF5IO(str(fileloc), 'r')
        nwbfile = io.read()
        version_ops = [dict(label=str(i), value=i)
                       for i in set(nwbfile.trials['trial_version'].data)]
        type_ops = [dict(label=str(i), value=i)
                    for i in set(nwbfile.trials['trial_type'].data)]
    except Exception as e:
        return None, [], []
    return nwbfile, version_ops, type_ops


@app.callback(
    output=(
        dl.Output('trial-version-dropdown','options'),
        dl.Output('trial-type-dropdown','options'),
        dl.Output('trial-version-dropdown','disabled'),
        dl.Output('trial-type-dropdown','disabled'),
    ),
    args=(
        dl.Input('nwb-input','value'),
    )
)
def open_nwb(fileloc):
    if fileloc:
        try:
            io = NWBHDF5IO(str(fileloc), 'r')
            nwbfile = io.read()
            version_ops = [dict(label=str(i), value=i)
                           for i in set(nwbfile.trials['trial_version'].data)]
            type_ops = [dict(label=str(i), value=i)
                        for i in set(nwbfile.trials['trial_type'].data)]
            return (version_ops, type_ops, False, False)
        except Exception as e:
            print(e)
    return ([],[], True,True)


@app.long_callback(
    output=dl.Output('trial-subplots','figure'),
    args=(dl.Input('submit-button-state','n_clicks'),
          dl.State('nwb-input','value'),
          dl.State('trial-version-dropdown','value'),
          dl.State('trial-type-dropdown','value')),
    running=[
        (dl.Output("submit-button-state", "disabled"), True, False),
        (dl.Output("cancel-button-state", "disabled"), False, True),
    ],
    cancel=[dl.Input("cancel-button-state", "n_clicks")],
    progress=dl.Output("progress_bar_extraction", ("value", "max"))
              # dl.Output("progress_bar_plotting", ("value", "max")))
)
def draw_graphs(set_progress,args):
    n_clicks, fileloc, versions, types = args
    print('long callback run')
    if versions is not None and types is not None:
        io = NWBHDF5IO(str(fileloc), 'r')
        nwbfile = io.read()
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
        trial_rows.fill(np.array([],dtype=int))
        cursor_trajectory = np.empty((tot_rows, tot_cols), dtype=object)
        cursor_trajectory.fill(np.nan*np.ones((1, cursor.data.shape[1])))
        for trial_no in range(len(trials)):
            # set_progress((str(trial_no + 1), str(len(trials))),('0',str(tot_rows+tot_cols)))
            if trials_version_data[trial_no] in versions and trials_type_data[trial_no] in types:
                a = versions.index(trials_version_data[trial_no])
                b = types.index(trials_type_data[trial_no])
                trial_rows[a, b] = np.append(trial_rows[a, b], trial_no)
                cursor_trajectory[a, b] = np.vstack([cursor_trajectory[a, b], trialized_ts[trial_no]])
        c = 0
        print(tot_rows,tot_cols)
        for a in range(tot_rows):
            for b in range(tot_cols):
                c += 1
                set_progress((str(c), str(tot_rows * tot_cols)))
                trial_row = trial_rows[a, b][0]
                # plot target positions:
                print(trial_row)
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
    else:
        return go.FigureWidget()


if __name__ == '__main__':
    app.run_server(debug=False)