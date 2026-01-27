import sys

sys.path.append('.')

from pathlib import Path

import plotly.express as px
import streamlit as st

from trajectoryIntegration import params, paths
from trajectoryIntegration.trajectory import Trajectory
from trajectoryIntegration.trajectory_processing import (sort_trajectory,
                                                         sorting_algorithms)

st.set_page_config(layout='wide', page_title='Sorting algorithms demo')

traj_ids = [
 'AT02603928',
 'AT02604203',
 'AT02607316',
 'AT02607961', # -> loop
 'AT02608297',
 'AT02608307',
 'AT02608879',
 'AT02608955',
 'AT02609163',
 'AT02609777',
 'AT02603204', # -> desordenada pero a trozos
 'AT02609895']
algorithm_list = {
    'Nearest neighbours': sorting_algorithms.nearest_neighbours,
    '2-Opt': sorting_algorithms.opt2,
    '2-Opt progressive': sorting_algorithms.opt2_progressive,
    '2-Opt restricted': sorting_algorithms.opt2_restricted,
}
algorithm_list = {v:k for k,v in algorithm_list.items()}
modes = {
    'complete': 'Complete',
    'segmented': 'Segmented',
}
algorithm_conf = {
    'complete': {
        'algorithm': sorting_algorithms.opt2_progressive,
        'options': {
            'n_closest' : 10,
            'window_size' : 100,
            'overlap' : 20,
            'distance_function' : 'haversine',
        },
    },
    'out': {
        'algorithm': sorting_algorithms.opt2,
        'options': {
            'distance_function' : 'haversine',
        },
    },
    'cruise': {
        'algorithm': sorting_algorithms.nearest_neighbours,
        'options': {
            'distance_function' : 'haversine',
        },
    },
    'in': {
        'algorithm': sorting_algorithms.opt2,
        'options': {
            'distance_function' : 'haversine',
        },
    },
}

@st.cache_data
def load_data():
    data_folder = Path(__file__).resolve().parent / 'demo_data'
    return {tr:Trajectory(tr, '2023-07-03', 'demo', data_folder)
            for tr in traj_ids}

trajectories = load_data()

# Layout
columns_content = st.columns([1,6])
with columns_content[1]:
    initial_graphs = st.container(border=True)
    final_graphs = st.container(border=True)
    df_container_old = st.container()
    df_container_new = st.container()
    with initial_graphs:
        original_traj_graphs = st.columns([1,1,1,1])
    with final_graphs:
        result_string = st.empty()
        sorted_traj_graphs = st.columns([1,1,1,1])

def config_parameters(algorithm, phase):
    algorithm_conf['name'] = algorithm

    distance_function = st.selectbox(
        label='Distance function', key=f'distance_function_{phase}',
        options=['Haversine', 'Euclidean'], index=0,
        help='Use Euclidean or Haversine distance to evaluate distances between points.',
    )
    algorithm_conf[phase]['options']['distance_function'] = distance_function.lower()

    if algorithm == sorting_algorithms.opt2_progressive:
        window_size = st.slider(
            'window_size', 0, 200, 50, 5, key=f'window_size_{phase}',
            help='Number of positions to sort in each iteration.'
        )
        algorithm_conf[phase]['options']['window_size'] = window_size
        overlap = st.slider(
            'overlap', 0, window_size, 20, 5, key=f'overlap_{phase}',
            help='Number of common positions between adjacent windows.'
        )
        algorithm_conf[phase]['options']['overlap'] = overlap
    elif algorithm == sorting_algorithms.opt2_restricted:
        n_closest = st.slider(
            'n_closest', 0, 100, 5, key=f'n_closest_{phase}',
            help='Maximum number of candidates to replace each position.'
        )
        algorithm_conf[phase]['options']['n_closest'] = n_closest

@st.fragment()
def config_algorithm():
    mode = st.selectbox(
        label=':material/route: Mode', key='mode',
        options=modes.keys(), index=0,
        format_func=lambda x: modes[x],
        help='Process the whole trajectory or each flight stage separately.',
    )
    with st.expander(label='Configure algorithm', expanded=True, icon=':material/settings:'):
        if mode == 'complete':
            algorithm = st.selectbox(
                label='Algorithm', key='algorithm',
                options=algorithm_list.keys(), index=0,
                format_func=lambda x: algorithm_list[x],
            )
            config_parameters(algorithm, 'complete')
        elif mode == 'segmented':
            st.markdown(':material/flight_takeoff: **Take-off**',
                        help='Between takeoff and exit of the TMA.')
            algorithm_out = st.selectbox(
                label='Algorithm', key='algorithm_out',
                options=algorithm_list.keys(), index=1,
                format_func=lambda x: algorithm_list[x],
            )
            config_parameters(algorithm_out, 'out')
            st.markdown(':material/connecting_airports: **Cruise**',
                        help='Cruise phase in open airspace.')
            algorithm_cru = st.selectbox(
                label='Algorithm', key='algorithm_cru',
                options=algorithm_list.keys(), index=0,
                format_func=lambda x: algorithm_list[x],
            )
            config_parameters(algorithm_cru, 'cruise')
            st.markdown(':material/flight_land: **Landing**',
                        help='Between entering the TMA and the landing.')
            algorithm_in = st.selectbox(
                label='Algorithm', key='algorithm_in',
                options=algorithm_list.keys(), index=1,
                format_func=lambda x: algorithm_list[x],
            )
            config_parameters(algorithm_in, 'in')
    return mode

with columns_content[0]:
    traj_id = st.selectbox(
        label=':material/flight_takeoff: Trajectory',
        options=traj_ids, index=0,
    )
    # reverse = st.checkbox('Reverse', value=False)
    mode = config_algorithm()
    go_button = st.button('Go', type='primary', width='stretch')

traj = trajectories[traj_id]

with original_traj_graphs[0]:
    fig_map_old = px.scatter_map(
        traj.vectors.reset_index(), lon='longitude', lat='latitude',
        height=450, map_style='open-street-map', zoom=4,
        color=traj.vectors.index, color_continuous_scale='balance')
    fig_map_old.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig_map_old, width='stretch', config={'scrollZoom': True})
with original_traj_graphs[1]:
    fig_latitude_old = px.line(
        traj.vectors.reset_index(), x='index', y='latitude',
        markers=True, hover_data=['index'], height=450)
    st.plotly_chart(fig_latitude_old, width='stretch')
with original_traj_graphs[2]:
    fig_longitude_old = px.line(
        traj.vectors.reset_index(), x='index', y='longitude',
        markers=True, hover_data=['index'], height=450)
    st.plotly_chart(fig_longitude_old, width='stretch')
with original_traj_graphs[3]:
    fig_altitude_old = px.line(
        traj.vectors.reset_index(), x='index', y='altitude',
        markers=True, hover_data=['index'], height=450)
    st.plotly_chart(fig_altitude_old, width='stretch')
with df_container_old:
    with st.expander(label='Original data'):
        st.dataframe(traj.vectors.reset_index())

if go_button:
    with final_graphs:
        with st.spinner(text="Sorting trajectory...", show_time=True):
            sorted_traj = sort_trajectory.process_trajectory(
                trajectory=traj,
                mode=mode,
                algorithm=algorithm_conf,
                presort=False,
            )
        old_dist = sorting_algorithms.path_length(traj.vectors[['latitude', 'longitude']].to_numpy(dtype='float32'),
                                                  distance_function='haversine')
        new_dist = sorting_algorithms.path_length(sorted_traj.vectors[['latitude', 'longitude']].to_numpy(dtype='float32'),
                                                  distance_function='haversine')
        with result_string:
            st.markdown(f'**Sorting results:** Original distance: {old_dist:.3f} Mi :material/arrow_circle_right: New distance: {new_dist:.3f} Mi (-{((old_dist-new_dist)/old_dist):.2%})')
    with sorted_traj_graphs[0]:
        fig_map_new = px.scatter_map(
            sorted_traj.vectors.reset_index(), lon='longitude', lat='latitude',
            height=450, map_style='open-street-map', zoom=4,
            hover_data={'distance_org':':.2f', 'distance_dst':':.2f'},
            color=sorted_traj.vectors.index, color_continuous_scale='balance')
        fig_map_new.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_map_new, width='stretch', config={'scrollZoom': True})
    with sorted_traj_graphs[1]:
        fig_latitude_new = px.line(
            sorted_traj.vectors.reset_index(), x='index', y='latitude',
            markers=True, hover_data=['index', 'old_index'], height=450)
        st.plotly_chart(fig_latitude_new, width='stretch')
    with sorted_traj_graphs[2]:
        fig_longitude_new = px.line(
            sorted_traj.vectors.reset_index(), x='index', y='longitude',
            markers=True, hover_data=['index', 'old_index'], height=450)
        st.plotly_chart(fig_longitude_new, width='stretch')
    with sorted_traj_graphs[3]:
        fig_altitude_new = px.line(
            sorted_traj.vectors.reset_index(), x='index', y='altitude',
            markers=True, hover_data=['index', 'old_index'], height=450)
        st.plotly_chart(fig_altitude_new, width='stretch')

    with df_container_new:
        with st.expander(label='Resorted data'):
            st.dataframe(sorted_traj.vectors.reset_index())

    with columns_content[0]:
        with st.expander('Sort results'):
            st.json(sorted_traj.sorting_metrics)

if __name__ == '__main__':
    pass
