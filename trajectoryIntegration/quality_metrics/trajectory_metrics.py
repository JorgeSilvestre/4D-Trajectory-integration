import datetime
import json

import numpy as np
import pandas as pd

from .. import params, paths, utils
from ..trajectory_processing import sorting_algorithms


def calculate_metrics_trajectories(date: str, trayType: str = 'raw'):
    if trayType == 'raw':
        folder = paths.NM_TRAJECTORIES_RAW_PATH
    elif trayType == 'clean':
        folder = paths.NM_TRAJECTORIES_PATH
    ifplIds = pd.read_parquet(folder / f'tray.{date}.parquet', columns=['ifplId'],
                              engine='pyarrow', dtype_backend='pyarrow', ).ifplId.drop_duplicates()

    for t_id in ifplIds.values:
        calculate_metrics_trajectory(date, t_id, trayType)

    # args = [(date, t_id, trayType) for t_id in ifplIds.values]
    # with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
    #     executor.map(lambda x: calculate_metrics_trajectory(*x), args, chunksize=100)

def calculate_metrics_trajectory(date: str, trajectoryId: str, trayType: str = 'raw'):
    if trayType == 'raw':
        folder = paths.NM_TRAJECTORIES_RAW_PATH
    elif trayType == 'clean':
        folder = paths.NM_TRAJECTORIES_PATH
    data = pd.read_parquet(folder / f'tray.{date}.parquet', filters=[('ifplId', '==', trajectoryId)],
                           engine='pyarrow', dtype_backend='pyarrow', )
    with open(folder / f'flightDate={date}' / f'tray.{trajectoryId}.json', 'r', encoding='utf8') as file:
        metadata = json.load(file)

    results = {}
    results['ifplId'] = trajectoryId
    ## Generic
    completitude = data[['timestamp', 'latitude', 'longitude', 'baro_altitude', 'geo_altitude',
                         'callsign', 'vertical_rate', 'velocity', 'altitude', 'true_track']].notnull().sum()
    results['completitude'] = {col:val/len(data) for col, val in completitude.items()}
    results['num_vectors'] = len(data)
    results['duration'] = int((data.timestamp.max() - data.timestamp.min()).total_seconds())
    results['distance'] = float(sorting_algorithms.path_length(data[['latitude', 'longitude']].to_numpy('float32')))

    ## Semantic
    results['distance_to_origin'] = calculate_distance_to_airport(data, metadata['aerodromeOfDeparture'], where='origin')
    results['distance_to_destination'] = float( calculate_distance_to_airport(data, metadata['aerodromeOfDestination'], where='destination'))
    results['missing_start'] = bool(results['distance_to_origin'] > params.THRESHOLD_DISTANCE_TO_AIRPORT)
    results['missing_end'] = bool(results['distance_to_destination'] > params.THRESHOLD_DISTANCE_TO_AIRPORT)
    results['airports_distance'] = calculate_distance_airports(metadata['aerodromeOfDeparture'], metadata['aerodromeOfDeparture'])
    results['effective_flight_time'] = int((
        datetime.datetime.fromisoformat(metadata['actualTimeOfArrival']) -
        datetime.datetime.fromisoformat(metadata['actualTakeOffTime'])
        ).total_seconds())
    # results['missing_taxi_start'] = bool(data[(data['distance_to_origin'] < AIRPORT_AREA) & data.on_ground])
    # results['missing_taxi_end'] = bool(data[(data['distance_to_destination'] < AIRPORT_AREA) & data.on_ground])
    results['last_altitude_before_ground'] = data.loc[data[~data.on_ground].timestamp.idxmax()].altitude

    ## Coverage and density
    results['density'] = results['num_vectors']/results['distance']
    results['mean_granularity'] = calculate_mean_granularity(data)
    results['std_granularity'] = calculate_std_granularity(data)
    results['mean_granularity_distance'] = calculate_mean_granularity_distance(data)
    results['std_granularity_distance'] = calculate_std_granularity_distance(data)
    results['gaps'] = identify_gaps(data)
    results['num_gaps'] = len(results['gaps'])
    results['segments'] = []
    latest = 0
    for g in results['gaps']:
        results['segments'].append(dict(start=latest, end=g['index']))
        latest = g['index']+1
    else:
        results['segments'].append(dict(start=latest, end=len(data)-1))
    results['num_segments'] = len(results['segments'])
    results['gap_time'] = int(calculate_gap_time(data))
    results['gap_ratio'] = results['gap_time']/results['duration'] if results['duration'] else 0
    results['continuity_time'] = int(calculate_continuity_time(data))
    results['continuity_ratio'] = results['continuity_time']/results['duration'] if results['duration'] else 0
    results['discontinuity_time'] = int(calculate_discontinuity_time(data))
    results['discontinuity_ratio'] = results['discontinuity_time']/results['duration'] if results['duration'] else 0
    results['thresholds'] = dict(
        THRESHOLD_DISTANCE_TO_AIRPORT = params.THRESHOLD_DISTANCE_TO_AIRPORT,
        THRESHOLD_GAP_TIME = params.THRESHOLD_GAP_TIME,
        THRESHOLD_CONTINUITY = params.THRESHOLD_CONTINUITY,
        AIRPORT_AREA=params.AIRPORT_AREA,
    )

    if pd.isna(results['last_altitude_before_ground']):
        results['last_altitude_before_ground'] = None

    if trayType == 'raw':
        if not paths.NM_TRAYS_METRICS_L2_PATH.exists():
            paths.NM_TRAYS_METRICS_L2_PATH.mkdir(parents=True)
        with open(paths.NM_TRAYS_METRICS_L2_PATH / f'tray.{date}.{trajectoryId}.json', 'w+', encoding='utf8') as file:
            json.dump(results, file, indent=2, default=utils.custom_json_encoder)
            # try:
            # except TypeError:
            #     print(results)
            #     exit()
    elif trayType == 'clean':
        results['sorted_vectors'] = get_resorted_vectors(data)
        results['timestamp_variation'] = get_timestamp_variation(data)
        if not paths.NM_TRAYS_METRICS_L3_PATH.exists():
            paths.NM_TRAYS_METRICS_L3_PATH.mkdir(parents=True)
        with open(paths.NM_TRAYS_METRICS_L3_PATH / f'tray.{date}.{trajectoryId}.json', 'w+', encoding='utf8') as file:
            json.dump(results, file, indent=2, default=utils.custom_json_encoder)

    return results

def calculate_distance_to_airport(data, airport: str, where: str = 'origin'):
    ap_location = pd.read_parquet(paths.AIRPORTS_PATH, engine='pyarrow',
                                  filters=[('icao_code', '==', airport)])
    if where == 'origin':
        vector = data.iloc[0]
    elif where == 'destination':
        vector = data.iloc[-1]
    return float(sorting_algorithms.haversine_distance(
        data[['latitude','longitude']].iloc[:1,:].to_numpy(dtype='float32'),
        ap_location[['latitude','longitude']].to_numpy(dtype='float32').reshape((1,2)))[0])
    return utils.haversine_np(vector.latitude, vector.longitude,
                               ap_location.latitude, ap_location.longitude)[0]

def calculate_distance_airports(airport_dep: str, airport_dest: str):
    airports = pd.read_parquet(paths.AIRPORTS_PATH)

    origin_airport = airports[airports.icao_code == airport_dep].iloc[0]
    destination_airport = airports[airports.icao_code == airport_dest].iloc[0]
    distance = utils.haversine_np(origin_airport.latitude,
                                  origin_airport.longitude,
                                  destination_airport.latitude,
                                  destination_airport.longitude)
    return distance

def calculate_mean_granularity(data):
    return np.mean(data.timestamp.diff().dt.total_seconds())

def calculate_std_granularity(data):
    return np.std(data.timestamp.diff().dt.total_seconds())

def calculate_mean_granularity_distance(data):
    return float(np.mean(sorting_algorithms.haversine_distance(
        data[['latitude', 'longitude']].iloc[1:].to_numpy('float32'),
        data[['latitude', 'longitude']].iloc[:-1].to_numpy('float32'))))
    return float(np.mean(utils.haversine_np(data.latitude[1:].values, data.longitude[1:].values,
                                            data.latitude[:-1].values, data.longitude[:-1].values)))

def calculate_std_granularity_distance(data):
    return float(np.std(sorting_algorithms.haversine_distance(
        data[['latitude', 'longitude']].iloc[1:].to_numpy('float32'),
        data[['latitude', 'longitude']].iloc[:-1].to_numpy('float32'))))

def identify_gaps(data):
    diffs = data.timestamp.diff().dt.total_seconds()
    gaps = [dict(index=i, size=int(diff))
            for i, diff in enumerate(diffs)
            if pd.notna(diff) and diff>params.THRESHOLD_GAP_TIME]

    return gaps

def calculate_continuity_time(data):
    diffs = data.timestamp.diff().dt.total_seconds()
    return sum(diffs[diffs<=params.THRESHOLD_CONTINUITY])

def calculate_discontinuity_time(data):
    diffs = data.timestamp.diff().dt.total_seconds()
    return sum(diffs[diffs.between(params.THRESHOLD_CONTINUITY, params.THRESHOLD_GAP_TIME)])

def calculate_gap_time(data):
    diffs = data.timestamp.diff().dt.total_seconds()
    return sum(diffs[diffs>params.THRESHOLD_GAP_TIME])

def calculate_distance_ratio(data):
    # TODO: Ratio de distancia cubierta en línea recta respecto a la distancia en línea recta que
    # separa los aeropuertos de origen y destino

    return


def get_outliers_position():
    # WIP
    pass

def get_outliers_altitude():
    # WIP
    pass

def get_resorted_vectors(data):
    return data.reordenado.sum()

def get_timestamp_variation(data):
    tmp = data[data.reordenado]
    if len(tmp)>0:
        return (tmp.timestamp - tmp.original_timestamp).mean()
    else:
        return 0
