import json
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from tqdm import tqdm

from .. import params, paths
from ..trajectory import Trajectory
from .process_outliers import fix_altitude
from .sorting_algorithms import haversine_distance, path_length


def process_trajectories(date: str) -> None:
    tray_ids = (paths.NM_TRAJECTORIES_RAW_PATH / f'flightDate={date}').glob('*.json')
    tray_ids = [str(x).split('.')[1] for x in tray_ids]
    trays = (Trajectory(x, date) for x in tray_ids)

    # Parallelized
    with ProcessPoolExecutor(max_workers=7) as executor:
        result = tqdm(executor.map(_process_trajectory_params, trays, chunksize=1, buffersize=15),
                      total=len(tray_ids), ncols=125, leave=True)
        result = list(result)

    ## Not Parallelized
    # result = []
    # for tray in tqdm(trays, total=len(tray_ids), ncols=125, leave=True):
    #     result.append(_process_trajectory_params(tray))

    result = [t.vectors for t in result]
    result = pd.concat(result)

    folder = paths.NM_TRAJECTORIES_PATH
    if len(result)>0:
        path = folder / f'tray.{date}.parquet'
        result.to_parquet(path, index=False,)

def _process_trajectory_params(trajectory: Trajectory) -> Trajectory:
    trajectory = process_trajectory(
        trajectory,
        mode=params.HOW_SORT,
        algorithm=params.SORT_ALG,
        presort=params.PRESORT_ALG,
        check_loop=params.DETECT_LOOP,
        log=True)

    return trajectory

def process_trajectory(trajectory: Trajectory, mode, algorithm, presort,
                       presort_algs={}, check_loop=True, log=False) -> Trajectory:
    trajectory = sort_trajectory(trajectory=trajectory,
                                mode=mode,
                                algorithm=algorithm,
                                presort=presort,
                                presort_algs=presort_algs,
                                check_loop=check_loop,
                                log=log)
    trajectory = identify_moved_vectors(trajectory)
    trajectory = recalculate_timestamp(trajectory)
    trajectory = fix_altitude(trajectory)
    # trajectory = fix_outliers(trajectory)

    # cleanup
    # trajectory.vectors.drop(['distance_org', 'distance_dst'], axis=1, inplace=True)
    trajectory.trajectory_status = 'L3_sorted'
    trajectory.save()

    return trajectory

def sort_trajectory(trajectory: Trajectory, mode, algorithm, presort,
                       presort_algs={}, check_loop=True, log=False) -> Trajectory:
    airports = pd.read_parquet(paths.AIRPORTS_PATH)

    ### Metrics ###############################################################
    ts_start = time.time()
    metrics = {}
    data = trajectory.vectors.copy()

    metrics['initial_num_vectors'] = len(data)
    metrics['initial_distance'] = float(path_length(data[['latitude','longitude']].to_numpy(dtype='float32')))
    metrics['dupl_vectors'] = int(data.drop('timestamp', axis=1).duplicated().sum())
    metrics['dupl_position_vectors'] = int(data.duplicated(subset=['latitude','longitude']).sum())
    metrics['dupl_position_vectors_pos_ts'] = int(data.duplicated(subset=['latitude','longitude','time_position']).sum())
    metrics['dupl_position_vectors_gen_ts'] = int(data.duplicated(subset=['latitude','longitude','last_contact']).sum())

    data = data.drop_duplicates(subset=['latitude','longitude']).reset_index(drop=True)
    data['old_index'] = pd.DataFrame(range(len(data)), dtype='Int32[pyarrow]')

    metrics['distance_duplVectors'] = float(path_length(data[['latitude','longitude']].to_numpy(dtype='float32')))

    ### Flight stages #########################################################
    # Calculate distances to airports
    origin_airport = airports[airports.icao_code == trajectory.aerodromeOfDeparture].iloc[0]
    origin_airport = origin_airport[['latitude','longitude']].to_numpy(dtype='float32')
    destination_airport = airports[airports.icao_code == trajectory.aerodromeOfDestination].iloc[0]
    destination_airport = destination_airport[['latitude','longitude']].to_numpy(dtype='float32')

    data['distance_org'] = haversine_distance(
        data[['latitude','longitude']].to_numpy(dtype='float32'),
        origin_airport.reshape((1,2)))
    data['distance_dst'] = haversine_distance(
        data[['latitude','longitude']].to_numpy(dtype='float32'),
        destination_airport.reshape((1,2)))

    distance_airports = haversine_distance(
        origin_airport.reshape((1,2)),
        destination_airport.reshape((1,2)))
    metrics['distance_airports'] = float(distance_airports[0])

    # Ground vectors in origin airport - By timestamp
    ground_org = data[(data.distance_org<params.AIRPORT_AREA) & (data.on_ground)].copy()
    # Ground vectors in destination airport - By timestamp
    ground_dst = data[(data.distance_dst<params.AIRPORT_AREA) & (data.on_ground)].copy()
    if len(ground_org)>0:
        data = data[~data.index.isin(ground_org.index)].copy()
    if len(ground_dst)>0:
        data = data[~data.index.isin(ground_dst.index)].copy()

    # Add virtual first and last vectors at the airports
    initial_vec = {
        'latitude':origin_airport[0],
        'longitude':origin_airport[1],
        'distance_org':0.0}
    final_vec = {
        'latitude':destination_airport[0],
        'longitude':destination_airport[1],
        'distance_dst':0.0}
    data.index = data.index+1
    data = pd.concat([
        pd.DataFrame(initial_vec, index=[0]),
        data,
        pd.DataFrame(final_vec, index=[data.index.max()+1]),
    ])

    ### Sorting ###############################################################
    if presort == True:
        if mode == 'complete':
            data = sort_trajectory_complete(data, presort_algs['presort_complete'])
        elif mode == 'segmented':
            data = sort_trajectory_segmented(data, presort_algs)
    metrics['distance_presort'] = float(path_length(data[['latitude','longitude']].to_numpy(dtype='float32')))

    temp = data[(data.distance_dst.between(params.TMA_AREA_MIN, params.TMA_AREA_MAX)) & (data.altitude>0)].copy()
    max_rotation = calculate_max_rotation(temp.true_track)
    del temp
    metrics['rotation'] = float(max_rotation)
    # If there is a holding, do not sort the last segment
    if check_loop and max_rotation>params.HOLDING_ROTATION:
        alg = {
            'out': algorithm['out'],
            'cruise': algorithm['cruise'],
        }
        data = sort_trajectory_segmented(data, alg)
    # If there is a loop, sort the last segment with specific method
    elif check_loop and max_rotation>params.LOOP_ROTATION:
        alg = {
            'out': algorithm['complete'] if mode=='complete' else algorithm['out'],
            'cruise': algorithm['complete']  if mode=='complete' else algorithm['cruise'],
            'in': params.LOOP_ALG,
        }
        data = sort_trajectory_segmented(data, alg)
    else:
        if mode == 'complete':
            data = sort_trajectory_complete(data, algorithm['complete'])
        elif mode == 'segmented':
            data = sort_trajectory_segmented(data, algorithm)

    data = pd.concat([
        ground_org,
        data,
        ground_dst,
    ]).dropna(subset='old_index').reset_index(drop=True)
    del ground_org, ground_dst

    data['new_index'] = range(len(data))
    trajectory.vectors = data

    metrics['final_distance'] = float(path_length(data[['latitude','longitude']].to_numpy(dtype='float32')))
    metrics['final_num_vectors'] = len(data)
    metrics['process_time'] = time.time() - ts_start

    # print results
    # print(metrics["initial_distance"], 'Mi ->', metrics["final_distance"], 
    #       f'Mi (-{((metrics["initial_distance"]-metrics["final_distance"])/metrics["initial_distance"]):.2%})')

    if log:
        folder = paths.SORT_TRAJECTORIES_METRICS_PATH
        if not folder.exists():
            folder.mkdir(parents=True)
        with open(folder / f'sortTray.{trajectory.date}.{trajectory.ifplId}.json', 'w+', encoding='utf8') as file:
            json.dump(metrics, file, indent=2)

    trajectory.sorting_metrics = metrics
    return trajectory

def sort_trajectory_complete(data: pd.DataFrame, algorithm_conf) -> pd.DataFrame:
    algorithm = algorithm_conf['algorithm']
    config = algorithm_conf['options']
    sorted_tray =  algorithm(data, **config)
    old_distance = path_length(
        data[['latitude', 'longitude']].to_numpy(dtype='float32')[1:-1,:],
        distance_function='haversine')
    new_distance = path_length(
        sorted_tray[['latitude', 'longitude']].to_numpy(dtype='float32')[1:-1,:],
        distance_function='haversine')
    # print(old_distance, 'Mi ->', new_distance, f'Mi (-{((old_distance-new_distance)/old_distance):.2%})')

    return sorted_tray if new_distance < old_distance else data

def sort_trajectory_segmented(data: pd.DataFrame, algorithm_conf) -> pd.DataFrame:
    origin = data.iloc[[0]]
    destination = data.iloc[[-1]]
    ### Maneuver segments - NV or by timestamp
    maneuver_org = data[data.distance_org<(params.TMA_AREA_MAX/2)].copy()
    ### Cruise segment - Distance to destination
    maneuver_dst = data[data.distance_dst<params.TMA_AREA_MAX].copy()
    ids = set(maneuver_org.index.to_list()+maneuver_dst.index.to_list())
    # ids.remove(0)
    # ids.remove(data.index.max())
    cruise = data[~(data.index.isin(ids))]

    overlap = 5

    ######################### Sort #########################
    if 'out' in algorithm_conf:
        maneuver_org = pd.concat([maneuver_org, destination])
        sort_trajectory_complete(maneuver_org, algorithm_conf['out']).iloc[:-1]
    if 'cruise' in algorithm_conf:
        cruise = pd.concat([maneuver_org[-overlap:], cruise, destination])
        cruise = sort_trajectory_complete(cruise, algorithm_conf['cruise']).iloc[:-1]
    if 'loop' in algorithm_conf:
        maneuver_dst = pd.concat([cruise[-overlap:], maneuver_dst])
        maneuver_dst = sort_trajectory_complete(maneuver_dst, algorithm_conf['in'])
    elif 'in' in algorithm_conf:
        maneuver_dst = pd.concat([cruise[-overlap:], maneuver_dst])
        maneuver_dst = sort_trajectory_complete(maneuver_dst, algorithm_conf['in'])

    data = pd.concat([
        maneuver_org.iloc[:-overlap],
        cruise.iloc[:-overlap],
        maneuver_dst,
    ])

    return data

def calculate_max_rotation(tracks: pd.Series):
    if len(tracks) < 2:
        return 0.0
    deltas = tracks.diff().dropna()
    # mod operation throws NotImplementedError from pyarrow -> cast to numpy
    deltas = (deltas.to_numpy('float32') + 180) % 360 - 180 

    turn_right = (deltas[deltas>0].sum())
    turn_left = -(deltas[deltas<0].sum())

    return max(turn_right, turn_left)

def identify_moved_vectors(trajectory: Trajectory):
    data = trajectory.vectors.copy()

    # acc para usarlo como objeto mutable y evitar el uso de una variable global
    # [found, missing]
    acc = (set(), set())
    # print(f'Tipo  (oFi  oIn | diff)    m|f oF-oI-acc Re Changes')    # Log
    data['is_moved'] = (data[['new_index','old_index']].astype('Int32[pyarrow]')
                                                         .apply(_is_moved, args=[acc], axis=1))

    trajectory.vectors = data
    return trajectory

def _is_moved(x:pd.DataFrame, acc_list: list, show_log: bool = False) -> bool:
    found, missing = acc_list
    removed, added = [], []
    # rem_f, rem_m = False, False
    reordenado = False
    tipo = ''

    f, m = len(found), len(missing)
    acc = f - m
    if x.old_index in missing:
        tipo += 'a'

        removed.append(f'm{x.old_index}')
        missing.remove(x.old_index)

    elif x.new_index - (f-m) in found:
        tipo += 'b'

        to_remove=[]
        for i in range(x.new_index - (f-m), x.old_index):
            if i not in found:
                break
            to_remove.append(i)
        removed.extend(f'f{i}' for i in to_remove)
        found.difference_update(to_remove)

    if (x.old_index + len(found) == x.new_index + len(missing)):
        tipo += '1'

        reordenado = False

    elif (x.old_index + len(found) < x.new_index + len(missing)):
        tipo += '2'

        reordenado = True
        # added.extend([f'm{x}' for x in range(x.new_index + len(missing), x.old_index + len(found))])
        # missing.update(set(range(x.new_index + len(missing), x.old_index + len(found))))
        added.append(f'm{x.old_index}')
        missing.add(x.old_index )

    elif (x.old_index + len(found) > x.new_index + len(missing)):
        tipo += '3'

        reordenado = True
        added.append(f'f{x.old_index}')
        found.add(x.old_index)

    if show_log:
        print(f'{tipo:<5} ({x.new_index:3}  {x.old_index:3} | {x.new_index - x.old_index:4})  {m:>3}|{f:<3}' + #    {acc:3}
              f'   {x.new_index - x.old_index - (f-m):4}  {"x" if reordenado else " "}  '  +
              f'{"+["+" ".join(added)+"]" if added else "":<7} {" -["+" ".join(removed)+"]" if removed else ""}')
    # if reordenado: print('\t', found, missing)

    return reordenado

def recalculate_timestamp(trajectory: Trajectory) -> Trajectory:
    data = trajectory.vectors.copy()
    data['original_timestamp'] = data['timestamp'].copy()

    positions = data[['latitude','longitude']].to_numpy(dtype='float32')
    cum_sum = np.cumsum(haversine_distance(positions[:-1], positions[1:]))
    cum_sum = np.concatenate([cum_sum, [0]])
    interp_values = (data.timestamp.astype('int64[pyarrow]')//10**9).copy()
    interp_values[data.is_moved.to_numpy()] = pd.NA
    interp_values.index = cum_sum
    interp_values = interp_values.interpolate(method='index', limit_direction='forward', limit_area='inside')
    interp_values = interp_values.interpolate(method='linear', limit_direction='both', limit_area='outside', order=1)
    interp_values = interp_values.round(0).astype('int64[pyarrow]').to_numpy()
    data['timestamp'] = pd.to_datetime(interp_values, unit='s')
    data['timestamp'] = data.timestamp.dt.tz_localize('utc')

    trajectory.vectors = data

    return trajectory