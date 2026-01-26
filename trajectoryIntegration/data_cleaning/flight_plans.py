import datetime
import json

import pandas as pd
from tqdm import tqdm

from .. import params, paths

# Network Manager
mapping_flightPlan = {
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.ifplId' : 'ifplId',
    'ps:FlightPlanMessage.timestamp' : 'timestamp',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.aircraftId' : 'callsign',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.aircraftAddress' : 'icao24',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aerodromeOfDeparture.icaoId' : 'aerodromeOfDeparture',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aerodromesOfDestination.aerodromeOfDestination.icaoId' : 'aerodromeOfDestination',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.estimatedOffBlockTime' : 'estimatedOffBlockTime',
    'ps:FlightPlanMessage.flightPlanData.structured.aircraftOperator' : 'operator',
    'ps:FlightPlanMessage.flightPlanData.structured.operatingAircraftOperator' : 'operatingOperator',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.registrationMark' : 'registrationMark',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.ssrInfo.code' : 'ssr',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.flightRules' : 'flightRules',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.flightType' : 'flightType',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftType.icaoId' : 'aircraftType',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.totalEstimatedElapsedTime' : 'totalEstimatedElapsedTime',
    'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.wakeTurbulenceCategory' : 'wakeTurbulenceCategory',
    'ps:FlightPlanMessage.uuid' : 'uuid',
}

mapping_flightData = {
    'ps:FlightDataMessage.flightData.flightId.id' : 'ifplId',
    'ps:FlightDataMessage.timestamp' : 'timestamp',
    'ps:FlightDataMessage.flightData.flightId.keys.aircraftId' : 'callsign',
    'ps:FlightDataMessage.flightData.aircraftAddress' : 'icao24',
    'ps:FlightDataMessage.flightData.flightId.keys.aerodromeOfDeparture' : 'aerodromeOfDeparture',
    'ps:FlightDataMessage.flightData.flightId.keys.aerodromeOfDestination' : 'aerodromeOfDestination',
    'ps:FlightDataMessage.flightData.flightId.keys.estimatedOffBlockTime' : 'estimatedOffBlockTime',
    'ps:FlightDataMessage.flightData.aircraftOperator' : 'operator',
    'ps:FlightDataMessage.flightData.operatingAircraftOperator' : 'operatingOperator',
    'ps:FlightDataMessage.flightData.estimatedTakeOffTime' : 'estimatedTakeOffTime',
    'ps:FlightDataMessage.flightData.estimatedTimeOfArrival' : 'estimatedTimeOfArrival',
    'ps:FlightDataMessage.flightData.actualOffBlockTime' : 'actualOffBlockTime',
    'ps:FlightDataMessage.flightData.actualTakeOffTime' : 'actualTakeOffTime',
    'ps:FlightDataMessage.flightData.actualTimeOfArrival' : 'actualTimeOfArrival',
    'ps:FlightDataMessage.flightData.calculatedTakeOffTime' : 'calculatedTakeOffTime',
    'ps:FlightDataMessage.flightData.calculatedTimeOfArrival' : 'calculatedTimeOfArrival',
    'ps:FlightDataMessage.flightData.flightState' : 'flightState',
    'ps:FlightDataMessage.flightData.flightDataVersionNr' : 'flightDataVersionNr',
    'ps:FlightDataMessage.flightData.aircraftType' : 'aircraftType',
    'ps:FlightDataMessage.flightData.routeLength' : 'routeLength',
    'ps:FlightDataMessage.uuid' : 'uuid',
}

def flatten_dict(data: dict, paths: list) -> list:
    """ Extract elements from a nested dictionary

    The nested structure is

    Args:
        data: Nested dictionary
        paths: A list with keys representing the attribute paths to be extracted with dot notation

    Returns:
        A list of extracted elements

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

def convert_time_column(column):
    column = pd.to_datetime(column, format='ISO8601').astype('int64[pyarrow]')//10**9
    # TODO: Si no se hace esto, se generan fechas extrañas (año 1600). Comprobar
    # column = column.apply(lambda x: x if x>0 else pd.NA)
    column = column - params.TIMEZONE_DISPL

    return column

### FLIGHT PLANS ----------------------------------------------------------------------------------

def nm_fplan_change_schema(data: pd.DataFrame)  -> pd.DataFrame:
    data = flatten_dict(data, mapping_flightPlan.keys())
    column_names = mapping_flightPlan.values()
    fplan = pd.DataFrame(data, columns=column_names)
    del data

    ## Data cleaning ----------------------------------------------------------
    # Data type
    fplan['timestamp'] = convert_time_column(fplan.timestamp)
    fplan['estimatedOffBlockTime'] = convert_time_column(fplan.estimatedOffBlockTime)
    string_columns = [
        'ifplId', 'icao24', 'callsign', 'operator', 'operatingOperator',
        'aerodromeOfDeparture', 'aerodromeOfDestination', 'flightType',
        'wakeTurbulenceCategory', 'uuid', 'registrationMark']
    for c in string_columns:
        fplan[c] = fplan[c].astype('string[pyarrow]')
    
    return fplan

def nm_fdata_change_schema(data: pd.DataFrame)  -> pd.DataFrame:
    data = flatten_dict(data, mapping_flightData.keys())
    column_names = mapping_flightData.values()
    fdata = pd.DataFrame(data, columns = column_names)
    del data
    
    # Data type
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
        'ifplId', 'icao24', 'callsign', 'aerodromeOfDeparture', 'aerodromeOfDestination',
        'operator', 'operatingOperator', 'flightState', 'aircraftType', 'uuid']
    for c in string_columns:
        fdata[c] = fdata[c].astype('string[pyarrow]')

    return fdata

def nm_fplan_json_to_parquet(date: str) -> None:
    """Parse NM flight plan data from a JSON file and write into a parquet file

    Args:
        date: String with a date in format 'YYYY-MM-DD'
    """

    ## Load -------------------------------------------------------------------
    input_file = paths.NM_JSON_FPLAN_PATH / f'flightDate={date}' / f'flightDate={date}.json'
    with open(input_file, 'r', encoding='utf8') as file:
        data = [json.loads(x) for x in file]
    fplan = nm_fplan_change_schema(data)
    del data

    ## Cleaning ---------------------------------------------------------------

    # Remove duplicates
    dups_columns = fplan.columns.difference(['uuid'])
    fplan = fplan.drop_duplicates(subset=dups_columns)

    # Sort messages
    fplan = fplan.sort_values(by=['ifplId', 'timestamp']).reset_index(drop=True)

    # Data format
    fplan['icao24'] = fplan.icao24.str.upper().str.strip()
    fplan['callsign'] = fplan.callsign.str.upper().str.strip()
    fplan['aerodromeOfDeparture'] = fplan.aerodromeOfDeparture.str.strip()
    fplan['aerodromeOfDestination'] = fplan.aerodromeOfDestination.str.strip()
    fplan['totalEstimatedElapsedTime'] = fplan.totalEstimatedElapsedTime.apply(
        lambda x: (int(x[:2])*60+int(x[2:])) if x else x).astype('int32[pyarrow]')

    # Fill missing attributes in the last fplan message
    fplan['ifplId_group'] = fplan.ifplId.copy()
    propagate_columns = [
        'icao24', 'registrationMark', 'ssr', 'flightType',
        'totalEstimatedElapsedTime', 'wakeTurbulenceCategory']
    for pc in propagate_columns:
        fplan[pc] = fplan.groupby('ifplId_group')[pc].ffill()
    fplan = fplan.drop('ifplId_group', axis=1)

    # Final clean
    fplan = fplan.drop_duplicates(subset=dups_columns, keep='last').reset_index(drop=True)

    ## Save data -------------------------------------------------------------
    output_dir = paths.NM_PARQUET_FPLAN_PATH
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    output_file = output_dir / f'nm.fplan.{date}.parquet'
    fplan.to_parquet(output_file, index=False)

def nm_fdata_json_to_parquet(date: str) -> None:
    """Parse NM flight data from a JSON file and write into a parquet file

    Args:
        date: String with a date in format 'YYYY-MM-DD'
    """

    ## Load -------------------------------------------------------------------
    data = []
    file_list = list((paths.NM_JSON_FDATA_PATH / f'flightDate={date}').glob('*.json'))
    for file_path in tqdm(file_list, desc=f'{date} FDATA   | Clean  ', ncols=125):
        with open(file_path, 'r', encoding='utf8') as file:
            chunk = [json.loads(x) for x in file]
        chunk = nm_fdata_change_schema(chunk)
        data.append(chunk)
    fdata = pd.concat(data)
    del data

    ## Cleaning ---------------------------------------------------------------

    # Remove duplicates
    dups_columns = fdata.columns.difference(['uuid'])
    fdata = fdata.drop_duplicates(subset=dups_columns)

    # Sort messages
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

    ### Save data -------------------------------------------------------------
    output_dir = paths.NM_PARQUET_FDATA_PATH
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    output_file = output_dir / f'nm.fdata.{date}.parquet'
    fdata.to_parquet(output_file, index=False)

### FLIGHTS ---------------------------------------------------------------------------------------

# OpenSky Flights
OP_FLIGHTS_RENAME = {
    # 'icao24',
    'firstSeen' : 'flightStart',
    'estDepartureAirport' : 'departureAirport',
    'lastSeen' : 'flightEnd',
    'estArrivalAirport' : 'destinationAirport',
    # 'callsign',
    # 'flightDate',
    # 'flightId',
}

def op_json_to_parquet(date: str) -> None:
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