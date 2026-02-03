"""
Flight data cleaning (L0 → L1).

This module processes raw data (L0) from two complementary sources (Network Manager and OpenSky
Flight) into their cleaned and normalized form as defined in L1. Network Manager has two endpoints
that must be processed separately. OpenSky Flights is currently not used in the project, but it
is kept as legacy due to being an open data source.

Each pipeline performs source-specific schema normalization, basic data cleaning and
semantic consolidation (e.g. version resolution), producing L1 parquet datasets
ready for downstream integration.

The module is responsible for both processing logic and I/O, following a data
maturity model where L0 is raw data and L1 corresponds to cleaned, source-level data.
"""

import datetime
import json
import os
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import pytz
from tqdm import tqdm

from .. import paths

# Maps Network Manager Flight Plans API field names to our standardized attribute names
NAME_MAPPING_FPLAN = {
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.ifplId': 'ifplId',
    'ps:FlightPlanMessage.timestamp': 'timestamp',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.aircraftId': 'callsign',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.aircraftAddress': 'icao24',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aerodromeOfDeparture.icaoId': 'aerodromeOfDeparture',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aerodromesOfDestination.aerodromeOfDestination.icaoId': 'aerodromeOfDestination',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.estimatedOffBlockTime': 'estimatedOffBlockTime',
    'ps:FlightPlanMessage.flightPlanData.structured.aircraftOperator': 'operator',
    'ps:FlightPlanMessage.flightPlanData.structured.operatingAircraftOperator': 'operatingOperator',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.registrationMark': 'registrationMark',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.ssrInfo.code': 'ssr',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.flightRules': 'flightRules',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.flightType': 'flightType',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftType.icaoId': 'aircraftType',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.totalEstimatedElapsedTime': 'totalEstimatedElapsedTime',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.wakeTurbulenceCategory': 'wakeTurbulenceCategory',
    'ps:FlightPlanMessage.uuid': 'uuid',
}

# Maps Network Manager Flight Plans API field names to our standardized attribute names
NAME_MAPPING_FDATA = {
    'ps:FlightDataMessage.flightData.flightId.id': 'ifplId',
    'ps:FlightDataMessage.timestamp': 'timestamp',
    'ps:FlightDataMessage.flightData.flightId.keys.aircraftId': 'callsign',
    'ps:FlightDataMessage.flightData.aircraftAddress': 'icao24',
    'ps:FlightDataMessage.flightData.flightId.keys.aerodromeOfDeparture': 'aerodromeOfDeparture',
    'ps:FlightDataMessage.flightData.flightId.keys.aerodromeOfDestination': 'aerodromeOfDestination',
    'ps:FlightDataMessage.flightData.flightId.keys.estimatedOffBlockTime': 'estimatedOffBlockTime',
    'ps:FlightDataMessage.flightData.aircraftOperator': 'operator',
    'ps:FlightDataMessage.flightData.operatingAircraftOperator': 'operatingOperator',
    'ps:FlightDataMessage.flightData.estimatedTakeOffTime': 'estimatedTakeOffTime',
    'ps:FlightDataMessage.flightData.estimatedTimeOfArrival': 'estimatedTimeOfArrival',
    'ps:FlightDataMessage.flightData.actualOffBlockTime': 'actualOffBlockTime',
    'ps:FlightDataMessage.flightData.actualTakeOffTime': 'actualTakeOffTime',
    'ps:FlightDataMessage.flightData.actualTimeOfArrival': 'actualTimeOfArrival',
    'ps:FlightDataMessage.flightData.calculatedTakeOffTime': 'calculatedTakeOffTime',
    'ps:FlightDataMessage.flightData.calculatedTimeOfArrival': 'calculatedTimeOfArrival',
    'ps:FlightDataMessage.flightData.flightState': 'flightState',
    'ps:FlightDataMessage.flightData.flightDataVersionNr': 'flightDataVersionNr',
    'ps:FlightDataMessage.flightData.aircraftType': 'aircraftType',
    'ps:FlightDataMessage.flightData.routeLength': 'routeLength',
    'ps:FlightDataMessage.uuid': 'uuid',
}

def flatten_dict(data: list[dict], paths: list[str]) -> list:
    """ Extract elements from a nested dictionary

    Network Manager provides highly nested JSON that we need to parse efficiently. Each dictionary
    is flattened by traveling the paths of the selected attributes in the JSON structure, and
    encoding their values as a sequence. Designed for deeply nested NM JSON payloads.
    Missing paths yield None values.

    Args:
        data: List of JSON-like records (e.g. NM messages).
        paths: List with keys representing the attribute paths to be extracted with dot notation

    Returns:
        List of sequences with the extracted values in their corresponding position.

    Example:
        data = [
            {"a": {"b": {"c": 1, "e": 2}}, "d": 4},
            {"a": {"b": {"c": 1}}, "d": 4, "f": 3}
        ]
        paths = ["a.b.c", "d", "f"]
        result = flatten_dict(data, paths)
        # result will be [[1, 2, None], [1, 4, 3]]
    """
    paths = [x.split('.') for x in paths]
    def extract_attributes(record):
        def extract_attribute_rec(path: list[str], elem: dict = record, pos: int = 0):
            elem = elem.get(path[pos], None)
            if isinstance(elem, dict):
                return extract_attribute_rec(path, elem, pos+1)
            else:
                return elem
        return list(map(extract_attribute_rec, paths))
    return list(map(extract_attributes, data))

def convert_time_column(column: pd.Series) -> pd.Series:
    """
    Convert ISO8601 timestamps to Unix epoch seconds.

    The conversion assumes UTC timestamps and applies a global timezone displacement
    defined in params.TIMEZONE_DISPLACEMENT.

    Args:
        column (pd.Series): Series containing ISO8601 timestamp strings.

    Returns:
        pd.Series: Integer epoch timestamps in seconds.
    """

    column = pd.to_datetime(column.sort_values(), format='ISO8601', cache=True)
    if column.dt.tz is not None:
        column = column.dt.tz_convert(pytz.utc)
    else:
        column = column.dt.tz_localize(pytz.timezone('Europe/Madrid'))
        column = column.dt.tz_convert(pytz.utc)

    return column #.astype('int64[pyarrow]')

### FLIGHT PLANS ----------------------------------------------------------------------------------
def nm_fplan_process(date: str) -> None:
    """
    Process NM Flight Plan (FPLAN) messages for a given date into L1 parquet files.

    The pipeline flattens nested JSON messages, normalizes the schema, resolves
    multiple message versions per flight plan and propagates stable attributes
    across updates.

    Args:
        date: String with a date in format 'YYYY-MM-DD'
    """

    input_file = paths.NM_JSON_FPLAN_PATH / f'flightDate={date}' / f'flightDate={date}.json'
    with open(input_file, 'r', encoding='utf8') as file:
        data = [json.loads(x) for x in file]
    fplan = nm_fplan_normalize_schema(data)
    del data
    fplan = nm_fplan_clean(fplan)
    output_dir = paths.NM_PARQUET_FPLAN_PATH
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    output_file = output_dir / f'nm.fplan.{date}.parquet'
    fplan.to_parquet(output_file, index=False)

def nm_fdata_process(date: str) -> None:
    """
    Process NM Flight Data (FDATA) messages for a given date into L1 parquet files.

    Messages are ordered by flight data version number, normalized and cleaned to
    produce a consolidated snapshot per flight plan.

    Args:
        date: String with a date in format 'YYYY-MM-DD'
    """

    data = []
    file_list = list((paths.NM_JSON_FDATA_PATH / f'flightDate={date}').glob('*.json'))
    max_workers=os.cpu_count()
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for file_path in tqdm(file_list, desc=f'{date} FDATA   | Clean  ', ncols=125):
            with open(file_path, 'r', encoding='utf8') as file:
                chunk = [json.loads(x) for x in file]
            chunk = nm_fdata_normalize_schema(chunk)
            chunk = nm_fdata_clean(chunk)
            data.append(chunk)
        fdata = pd.concat(data)
        del data
    output_dir = paths.NM_PARQUET_FDATA_PATH
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    output_file = output_dir / f'nm.fdata.{date}.parquet'
    fdata.to_parquet(output_file, index=False)

def nm_fdata_process(date: str) -> None:
    """
    Process NM Flight Data (FDATA) messages for a given date into L1 parquet files.

    Messages are ordered by flight data version number, normalized and cleaned to
    produce a consolidated snapshot per flight plan.

    Args:
        date: String with a date in format 'YYYY-MM-DD'
    """

    data = []
    file_list = list((paths.NM_JSON_FDATA_PATH / f'flightDate={date}').glob('*.json'))
    for file_path in tqdm(file_list, desc=f'{date} FDATA   | Clean  ', ncols=125):
        buffer = []
        with open(file_path, 'r', encoding='utf8') as file:
            for line in file:
                buffer.append(json.loads(line))
                if len(buffer) == 100_000:
                    chunk = nm_fdata_normalize_schema(buffer)
                    chunk = nm_fdata_clean(chunk)
                    data.append(chunk)
                    buffer = []
            else:
                chunk = nm_fdata_normalize_schema(buffer)
                chunk = nm_fdata_clean(chunk)
                data.append(chunk)
    fdata = pd.concat(data)
    del data
    output_dir = paths.NM_PARQUET_FDATA_PATH
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    output_file = output_dir / f'nm.fdata.{date}.parquet'
    fdata.to_parquet(output_file, index=False)

def _parallelize_nm_fdata_process(str):
    pass

def nm_fplan_normalize_schema(data: list[dict]) -> pd.DataFrame:
    """
    Process NM Flight Plan (FPLAN) messages for a given date into L1 parquet files.

    The pipeline flattens nested JSON messages, normalizes the schema, resolves
    multiple message versions per flight plan and propagates stable attributes
    across updates.
    """

    data = flatten_dict(data, NAME_MAPPING_FPLAN.keys())
    column_names = NAME_MAPPING_FPLAN.values()
    fplan = pd.DataFrame(data, columns=column_names)
    del data
    # Change data types
    fplan['timestamp'] = convert_time_column(fplan.timestamp)
    fplan['estimatedOffBlockTime'] = convert_time_column(fplan.estimatedOffBlockTime)
    string_columns = [
        'ifplId', 'icao24', 'callsign', 'operator', 'operatingOperator',
        'aerodromeOfDeparture', 'aerodromeOfDestination', 'flightType',
        'wakeTurbulenceCategory', 'uuid', 'registrationMark', ]
    for c in string_columns:
        fplan[c] = fplan[c].astype('string[pyarrow]')

    return fplan

def nm_fdata_normalize_schema(data: list[dict]) -> pd.DataFrame:
    """
    Convert OpenSky flight event JSON files into L1 parquet format.

    Handles flights spanning multiple days and applies basic normalization and
    filtering based on event timestamps.
    """

    data = flatten_dict(data, NAME_MAPPING_FDATA.keys())
    column_names = NAME_MAPPING_FDATA.values()
    fdata = pd.DataFrame(data, columns = column_names)
    del data
    # Change data types
    fdata['routeLength'] = fdata.routeLength.astype('Int32[pyarrow]')
    fdata['flightDataVersionNr'] = fdata.flightDataVersionNr.astype('Int32[pyarrow]')
    time_columns = [
        'timestamp',
        'estimatedOffBlockTime', 'actualOffBlockTime',
        'estimatedTakeOffTime', 'actualTakeOffTime',
        'estimatedTimeOfArrival', 'actualTimeOfArrival',
        'calculatedTakeOffTime', 'calculatedTimeOfArrival' ]
    for c in time_columns:
        fdata[c] = convert_time_column(fdata[c])
    string_columns = [
        'ifplId', 'icao24', 'callsign', 'aerodromeOfDeparture',
        'aerodromeOfDestination', 'operator', 'operatingOperator',
        'flightState', 'aircraftType', 'uuid', ]
    for c in string_columns:
        fdata[c] = fdata[c].astype('string[pyarrow]')

    return fdata

def nm_fplan_clean(fplan: pd.DataFrame) -> pd.DataFrame:
    # Remove duplicates
    dups_columns = fplan.columns.difference(['uuid'])
    fplan = fplan.drop_duplicates(subset=dups_columns)

    # Sort messages by timestamp
    fplan = fplan.sort_values(by=['ifplId', 'timestamp']).reset_index(drop=True)

    # Data format
    fplan['icao24'] = fplan.icao24.str.upper().str.strip()
    fplan['callsign'] = fplan.callsign.str.upper().str.strip()
    fplan['aerodromeOfDeparture'] = fplan.aerodromeOfDeparture.str.strip()
    fplan['aerodromeOfDestination'] = fplan.aerodromeOfDestination.str.strip()
    # Expected format: HHMM (NM specification)
    fplan['totalEstimatedElapsedTime'] = fplan.totalEstimatedElapsedTime.apply(
        lambda x: (int(x[:2])*60+int(x[2:])) if not pd.isna(x) else x
    ).astype('int32[pyarrow]')

    # Fill missing attributes in the last fplan message
    fplan['ifplId_group'] = fplan.ifplId.copy()
    propagate_columns = [
        'icao24', 'registrationMark', 'ssr', 'flightType',
        'totalEstimatedElapsedTime', 'wakeTurbulenceCategory', ]
    for pc in propagate_columns:
        fplan[pc] = fplan.groupby('ifplId_group')[pc].ffill()
    fplan = fplan.drop('ifplId_group', axis=1)

    # Final clean
    fplan = fplan.drop_duplicates(subset=dups_columns, keep='last').reset_index(drop=True)

    return fplan

def nm_fdata_clean(fdata: pd.DataFrame) -> pd.DataFrame:
    # Remove duplicates
    dups_columns = fdata.columns.difference(['uuid'])
    fdata = fdata.drop_duplicates(subset=dups_columns)

    # Sort messages by flight plan version
    fdata = fdata.sort_values(by=['ifplId', 'flightDataVersionNr']).reset_index(drop=True)

    # Data format
    fdata['icao24'] = fdata.icao24.str.upper().str.strip()
    fdata['callsign'] = fdata.callsign.str.upper().str.strip()
    fdata['aerodromeOfDeparture'] = fdata.aerodromeOfDeparture.str.strip()
    fdata['aerodromeOfDestination'] = fdata.aerodromeOfDestination.str.strip()

    # Fill ICAO24 of the last version of flight data
    fdata['ifplId_group'] = fdata.ifplId.copy()
    propagate_columns = ['icao24', 'actualTakeOffTime', 'actualTimeOfArrival']
    for pc in propagate_columns:
        fdata[pc] = fdata.groupby('ifplId_group')[pc].ffill()
    fdata = fdata.drop('ifplId_group', axis=1)

    # Final clean
    fdata = fdata.drop_duplicates(keep='last').reset_index(drop=True)

    return fdata

### FLIGHTS ---------------------------------------------------------------------------------------

# OpenSky Flights
NAME_MAPPING_OPENSKY_FLIGHTS = {
    'firstSeen': 'flightStart',
    'estDepartureAirport': 'departureAirport',
    'lastSeen': 'flightEnd',
    'estArrivalAirport': 'destinationAirport',
}

def opensky_flights_json_to_parquet(date: str) -> None:
    """Parse OpenSky flight data from a JSON file and write into a parquet file

    Assigns each flight to the day in which it ends. Loads data from both data
    and the previous day, and filters them based on their lastSeen timestamp.

    Args:
        date: String with a date in format 'YYYY-MM-DD'
    """
    # TODO: Revisar
    date_dt = datetime.datetime.strptime(date, '%Y-%m-%d')
    date_prev_dt = date_dt - datetime.timedelta(days=1)
    date_prev = date_prev_dt.strftime('%Y-%m-%d')

    file_paths = []
    if (paths.OPENSKY_RAW_FLIGHTS_PATH / f'flightDate={date_prev}').exists():
        file_paths += list(paths.OPENSKY_RAW_FLIGHTS_PATH.glob(f'flightDate={date_prev}/*.json'))
    file_paths += list(paths.OPENSKY_RAW_FLIGHTS_PATH.glob(f'flightDate={date}/*.json'))

    data = []
    for file_path in file_paths:
        chunk_df = pd.read_json(file_path)
        data.append(chunk_df)
    data = pd.concat(data)
    data = data[data.lastSeen.between(
        date_dt.timestamp(),
        (date_dt+datetime.timedelta(days=1,seconds=-1)).timestamp()
    )]
    data['flightDate'] = date

    # Clean flights
    data = data.sort_values(by=['icao24','firstSeen'])
    # Data type
    data['firstSeen'] = data.firstSeen.astype(int)
    data['lastSeen'] = data.lastSeen.astype(int)

    # Data format
    data['icao24'] = data.icao24.str.strip().str.upper()
    data['callsign'] = data.callsign.str.upper()

    # Column projection
    data = data[['icao24','firstSeen','estDepartureAirport','lastSeen','estArrivalAirport','callsign','flightDate']].copy()

    # Duplicates
    data = data.drop_duplicates()

    # Unique ID
    data['flightId'] = data.flightDate.str.replace('-','') + '-' + data.index.astype(str).str.ljust(6, '0')

    folder = paths.OPENSKY_PARQUET_FLIGHTS_PATH
    if not folder.exists():
        folder.mkdir(parents=True)
    path = folder / f'os.flights.{date}.parquet'
    data.to_parquet(path, index=False)