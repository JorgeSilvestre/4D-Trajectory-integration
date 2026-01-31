import json

import pandas as pd
from tqdm import tqdm

from .. import paths, utils
from ..data_cleaning.flight_plans import (nm_fdata_normalize_schema,
                                          nm_fplan_normalize_schema)
from ..data_cleaning.surveillance import opensky_vectors_normalize_schema
from ..data_cleaning.weather import taf_change_schema

def calculate_metrics_openskyVectors(date: str, state: str = 'clean') -> None:
    if state == 'raw':
        data_path = paths.OPENSKY_RAW_VECTORS_PATH
        output_path = paths.OPENSKY_VECTORS_METRICS_L0_PATH / f'vectors.L0.{date}.json'
    elif state == 'clean':
        data_path = paths.OPENSKY_PARQUET_VECTORS_PATH
        output_path = paths.OPENSKY_VECTORS_METRICS_L1_PATH / f'vectors.L1.{date}.json'

    file_list = list((data_path / f'flightDate={date}').glob('*.parquet'))
    if not file_list:
        return None

    res = []
    for path in tqdm(file_list, desc=f'{date} VECTORS | Metrics', ncols=125):
        data = pd.read_parquet(path, engine='pyarrow', dtype_backend='pyarrow')
        if state == 'raw':
            data = opensky_vectors_normalize_schema(data)
        completitude_fields = data.columns

        partial_results = {}
        partial_results['num_vectors'] = len(data)
        completitude = data.notnull().sum()
        partial_results['completitude'] = {col:val/len(data) for col, val in completitude.items()}
        partial_results['duplicate_records'] = data.shape[0] - data.drop_duplicates().shape[0]
        partial_results['reused_position'] = data.shape[0] - data.drop_duplicates(subset=['icao24','time_position','latitude','longitude']).shape[0]
        partial_results['nulls'] = {
            'latitude': int(data.latitude.isna().sum()),
            'longitude': int(data.longitude.isna().sum()),
            'latlon': len(data) - len(data[['latitude','longitude']].dropna(how='all'))
        }
        res.append(partial_results)

    results = {}
    results['state'] = state
    results['level'] = 'L0' if state=='raw' else 'L1'
    results['date'] = date
    results['num_vectors'] = sum([r['num_vectors'] for r in res])
    results['reused_position'] = sum([r['reused_position'] for r in res])
    results['duplicate_records'] = sum([r['duplicate_records'] for r in res])
    results['completitude'] = {}
    for attr in completitude_fields:
        results['completitude'][attr] = sum([r['completitude'][attr]*r['num_vectors'] for r in res])/results['num_vectors']
    results['nulls'] = {}
    for attr in ['latitude','longitude','latlon']:
        results['nulls'][attr] = sum([x['nulls'][attr] for x in res])

    if state == 'raw':
        data = pd.read_parquet(file_list, columns=['hexid', 'callsign'],
                               engine='pyarrow', dtype_backend='pyarrow')
        data = data.rename(columns={'hexid':'icao24',})
    elif state == 'clean':
        data = pd.read_parquet(file_list, columns=['icao24', 'callsign'],
                               engine='pyarrow', dtype_backend='pyarrow')
    uniqueness = data[['icao24','callsign']].nunique()
    results['uniqueness'] = {col:val for col, val in uniqueness.items()}

    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True)
    with open(output_path, 'w+', encoding='utf8') as file:
        json.dump(results, file, indent=2, default=utils.custom_json_encoder)

def calculate_metrics_fplan(date: str, state: str = 'clean') -> None:
    if state == 'clean':
        filepath = paths.NM_FPLAN_METRICS_L1_PATH / f'fPlan.L1.{date}.json'
        data = pd.read_parquet(paths.NM_PARQUET_FPLAN_PATH / f'nm.fplan.{date}.parquet')
    elif state == 'raw':
        filepath = paths.NM_FPLAN_METRICS_L0_PATH / f'fPlan.L0.{date}.json'
        with open(paths.NM_JSON_FPLAN_PATH / f'flightDate={date}' / f'flightDate={date}.json', 'r', encoding='utf8') as file:
            data = [json.loads(x) for x in file]
        data = nm_fplan_normalize_schema(data)

    results = {}
    results['date'] = date
    results['state'] = state
    results['level'] = 'L0' if state=='raw' else 'L1'

    results['num_messages'] = len(data)
    results['num_flights'] = data.ifplId.nunique()
    completitude = data.notnull().sum()
    results['completitude'] = {col:val/len(data) for col, val in completitude.items()}
    uniqueness = data.drop(['timestamp','estimatedOffBlockTime','totalEstimatedElapsedTime'], axis=1).nunique()
    dups_columns = data.columns.difference(['uuid'])
    results['duplicate_records'] = data.shape[0]-data.drop_duplicates(subset=dups_columns).shape[0]
    results['uniqueness'] = {col:val for col, val in uniqueness.items()}
    results['ranges'] = {
        'timestamp_min':data.timestamp.min(),
        'timestamp_max':data.timestamp.max(),
        'offblockTime_min':data.estimatedOffBlockTime.min(),
        'offblockTime_max':data.estimatedOffBlockTime.max(),
    }

    results['avg_messages_per_flight'] = data.groupby('ifplId').count().timestamp.mean()

    results['flights_airport_dep'] = {col:val for col,val
        in data.drop_duplicates(subset=['ifplId']).groupby('aerodromeOfDeparture').count().ifplId.items()}
    results['flights_airport_dest'] = {col:val for col,val
        in data.drop_duplicates(subset=['ifplId']).groupby('aerodromeOfDestination').count().ifplId.items()}
    results['flights_airport_route'] = {'-'.join(col):val for col,val
        in data.drop_duplicates(subset=['ifplId']).groupby(['aerodromeOfDeparture', 'aerodromeOfDestination']).count().ifplId.items()}


    if not filepath.parent.exists():
        filepath.parent.mkdir(parents=True)
    with open(filepath, 'w+', encoding='utf8') as file:
        json.dump(results, file, indent=2, default=utils.custom_json_encoder)

def calculate_metrics_fdata(date: str, state: str = 'clean') -> None:
    if state == 'clean':
        filepath = paths.NM_FDATA_METRICS_L1_PATH / f'fData.L1.{date}.json'
        data = pd.read_parquet(paths.NM_PARQUET_FDATA_PATH / f'nm.fdata.{date}.parquet')
    elif state == 'raw':
        filepath = paths.NM_FDATA_METRICS_L0_PATH / f'fData.L0.{date}.json'
        data = []
        file_list = list((paths.NM_JSON_FDATA_PATH / f'flightDate={date}').glob('*.json'))
        for file_path in file_list:
            with open(file_path, 'r', encoding='utf8') as file:
                chunk = [json.loads(x) for x in file]
            chunk = nm_fdata_normalize_schema(chunk)
            data.append(chunk)
        data = pd.concat(data)

    results = {}
    results['date'] = date
    results['state'] = state
    results['level'] = 'L0' if state=='raw' else 'L1'
    results['num_messages'] = len(data)
    results['num_flights'] = data.ifplId.nunique()
    completitude = data.notnull().sum()
    results['completitude'] = {col:val/len(data) for col, val in completitude.items()}
    uniqueness = data.drop(['actualTakeOffTime','actualTimeOfArrival','estimatedOffBlockTime',
                            'estimatedTakeOffTime','estimatedTimeOfArrival','flightDataVersionNr',
                            'routeLength'], axis=1).nunique()
    dups_columns = data.columns.difference(['uuid'])
    results['duplicate_records'] = data.shape[0]-data.drop_duplicates(subset=dups_columns).shape[0]
    results['uniqueness'] = {col:val for col, val in uniqueness.items()}

    results['ranges'] = {
        'offblockTime_min':data.estimatedOffBlockTime.min(),
        'offblockTime_max':data.estimatedOffBlockTime.max(),
        'actualTakeOffTime_min':data.actualTakeOffTime.min(numeric_only=True),
        'actualTakeOffTime_max':data.actualTakeOffTime.max(),
        'actualTimeOfArrival_min':data.actualTimeOfArrival.min(),
        'actualTimeOfArrival_max':data.actualTimeOfArrival.max(),
        'estimatedTakeOffTime_min':data.estimatedTakeOffTime.min(),
        'estimatedTakeOffTime_max':data.estimatedTakeOffTime.max(),
        'estimatedTimeOfArrival_min':data.estimatedTimeOfArrival.min(),
        'estimatedTimeOfArrival_max':data.estimatedTimeOfArrival.max(),
    }

    results['avg_messages_per_flight'] = data.groupby('ifplId').count().estimatedOffBlockTime.mean()

    if state == 'clean':
        filepath = paths.NM_FDATA_METRICS_L1_PATH / f'fData.L1.{date}.json'
    elif state == 'raw':
        filepath = paths.NM_FDATA_METRICS_L0_PATH / f'fData.L0.{date}.json'
    if not filepath.parent.exists():
        filepath.parent.mkdir(parents=True)
    with open(filepath, 'w+', encoding='utf8') as file:
        json.dump(results, file, indent=2, default=utils.custom_json_encoder)

def calculate_metrics_taf(month: str, state: str = 'clean') -> None:
    if state == 'raw':
        folder = paths.TAF_RAW_PATH / f'month={month}'
        filepath = paths.TAF_METRICS_L0_PATH / f'taf.L0.{month}.json'
    elif state == 'clean':
        folder = paths.TAF_PARQUET_PATH / f'taf.{month}.parquet' # f'month={month}'
        filepath = paths.TAF_METRICS_L1_PATH / f'taf.L1.{month}.json'

    data = pd.read_parquet(folder, engine='pyarrow', dtype_backend='pyarrow')
    if state == 'raw':
        data = taf_change_schema(data)

    pepe = data.columns

    results = {}
    results['month'] = month
    results['state'] = state
    results['level'] = 'L0' if state=='raw' else 'L1'

    results['num_reports'] = len(data)
    results['num_stations'] = data.station_id.nunique()
    completitude = data.notnull().sum()
    results['completitude'] = {col:val/len(data) for col, val in completitude.items()}
    uniqueness = data.drop(['sky_condition','turbulence_condition','icing_condition','temperature'], axis=1).nunique()
    results['uniqueness'] = {col:val for col, val in uniqueness.items()}
    results['ranges'] = {
        'min_temp':data.min_temp.min(),
        'max_temp':data.max_temp.max(),
    }
    results['reports_per_type'] = {col:val for col,val
        in data.groupby('change_indicator').count().station_id.items()}

    if not filepath.parent.exists():
        filepath.parent.mkdir(parents=True)
    with open(filepath, 'w+', encoding='utf8') as file:
        json.dump(results, file, indent=2, default=utils.custom_json_encoder)
