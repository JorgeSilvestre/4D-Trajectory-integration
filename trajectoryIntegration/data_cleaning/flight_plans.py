""" Network Manager/OpenSky Flights cleaning pipelines (L0 → L1).

This module transforms flight-level raw feeds into L1 parquet datasets with
normalized schema and source-specific cleaning operations.

Four different pipelines are implemented:

- `nm_fplan_process`: flattens and cleans Network Manager Flight Plan messages
  (FPLAN), then consolidates one latest snapshot per `ifplId`.
- `nm_fdata_process`: flattens and cleans Network Manager Flight Data messages
  (FDATA), ordering by `flightDataVersionNr` and retaining the latest version.
- `nm_adrr_process`: normalizes and cleans the flight data records from ADRR Flights.
- `opensky_flights_json_to_parquet`: legacy conversion utility for OpenSky
  Flights JSON files (currently outside the core integration flow).

Common processing patterns include schema normalization, UTC-aware timestamp
conversion, identifier normalization, duplicate removal, and forward propagation
of attributes that may appear only in later message versions.
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

# Maps Network Manager Flight Data API field names to our standardized attribute names
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
    """ Convert timestamp-like values to UTC-aware second-resolution datetimes.

    Input values are parsed using pandas ISO8601 support. If timezone information
    is present, values are converted to UTC. Otherwise, values are interpreted as
    `Europe/Madrid` local time and then converted to UTC.

    Args:
        column: Series with timestamp strings or datetime-like values.

    Returns:
        Series of timezone-aware UTC datetimes at second resolution.
    """

    column = pd.to_datetime(column.sort_values(), format='ISO8601', cache=True)
    if column.dt.tz is not None:
        column = column.dt.tz_convert(pytz.utc)
    else:
        column = column.dt.tz_localize(pytz.timezone('Europe/Madrid'))
        column = column.dt.tz_convert(pytz.utc)

    return column.dt.as_unit('s')

### FLIGHT PLANS ----------------------------------------------------------------------------------

def nm_fplan_process(date: str|datetime.date) -> None:
    """ Process NM Flight Plan (FPLAN) messages for one date.

    The pipeline flattens nested JSON messages, normalizes the schema, resolves
    multiple message versions per flight plan, and propagates stable attributes
    across updates.

    Args:
        date: Date in "YYYY-MM-DD" format.
    """

    input_file = paths.NM_JSON_FPLAN_PATH / f'flightDate={date}' / f'flightDate={date}.json'
    with open(input_file, 'r', encoding='utf8') as file:
        data = (json.loads(x) for x in file)
        fplan = nm_fplan_normalize_schema(data)
    fplan = nm_fplan_clean(fplan)

    # Write data
    output_dir = paths.NM_PARQUET_FPLAN_PATH
    paths.ensure_dir_exists(output_dir)
    output_file = output_dir / f'nm.fplan.{date}.parquet'
    fplan.to_parquet(output_file, index=False)

def nm_fdata_process(date: str|datetime.date) -> None:
    """ Process NM Flight Data (FDATA) messages for one date.

    Messages are ordered by flight data version number, normalized, and cleaned
    to produce a consolidated snapshot per flight plan.

    Args:
        date: Date in "YYYY-MM-DD" format.
    """

    data = []
    input_files = list((paths.NM_JSON_FDATA_PATH / f'flightDate={date}').glob('*.json'))
    for file_path in tqdm(input_files, desc=f'{date} FDATA   | Clean  ', ncols=125):
        # Processed in chunks to reduce memory consumption
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
    del data, buffer, chunk

    output_dir = paths.NM_PARQUET_FDATA_PATH
    paths.ensure_dir_exists(output_dir)
    output_file = output_dir / f'nm.fdata.{date}.parquet'
    fdata.to_parquet(output_file, index=False)

def _process_nm_fdata_chunk(data: pd.DataFrame) -> pd.DataFrame:
    # TODO
    pass

def nm_fplan_normalize_schema(data: list[dict]) -> pd.DataFrame:
    """ Normalize raw NM FPLAN messages into a typed tabular schema.

    The function flattens nested JSON records according to `NAME_MAPPING_FPLAN`,
    renames fields to canonical names, and applies baseline dtypes for temporal
    and text attributes.

    Args:
        data: Iterable/list of raw Network Manager FPLAN JSON records.

    Returns:
        DataFrame with normalized FPLAN columns and UTC-aware temporal fields.
    """

    data = flatten_dict(data, NAME_MAPPING_FPLAN.keys())
    column_names = NAME_MAPPING_FPLAN.values()
    fplan = pd.DataFrame(data, columns=column_names, )
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
    """Normalize raw NM FDATA messages into a typed tabular schema.

    The function flattens nested JSON records according to `NAME_MAPPING_FDATA`,
    renames fields to canonical names, and applies dtype conversion for numeric,
    text, and temporal attributes.

    Args:
        data: Iterable/list of raw Network Manager FDATA JSON records.

    Returns:
        DataFrame with normalized FDATA columns and UTC-aware temporal fields.
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
    """Apply semantic cleaning and version consolidation to normalized FPLAN data.

    Duplicate records are removed, records are ordered by (ifplId, timestamp),
    key text fields are normalized, selected attributes are forward-filled within each
    ifplId, and the latest consolidated message per unique record is retained.

    Args:
        fplan: Normalized FPLAN DataFrame.

    Returns:
        Cleaned and consolidated FPLAN DataFrame.
    """
    # Remove duplicates - all attributes except uuid
    dups_columns = fplan.columns.difference(['uuid'])
    fplan = fplan.drop_duplicates(subset=dups_columns)

    # Sort messages by timestamp
    fplan = fplan.sort_values(by=['ifplId', 'timestamp']).reset_index(drop=True)

    # Data format
    fplan['icao24'] = fplan.icao24.str.upper().str.strip()
    fplan['callsign'] = fplan.callsign.str.upper().str.strip()
    fplan['aerodromeOfDeparture'] = fplan.aerodromeOfDeparture.str.strip()
    fplan['aerodromeOfDestination'] = fplan.aerodromeOfDestination.str.strip()
    fplan['operator'] = fplan.operator.str.strip()
    fplan['operatingOperator'] = fplan.operatingOperator.str.strip()
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
    """Apply semantic cleaning and version consolidation to normalized FDATA data.

    Duplicate records (ignoring message uuid) are removed, records are
    ordered by (ifplId, flightDataVersionNr), text identifiers are
    normalized, and selected attributes are forward-filled within each
    ifplId before retaining the latest consolidated message version.

    Args:
        fdata: Normalized FDATA DataFrame.

    Returns:
        Cleaned and consolidated FDATA DataFrame.
    """
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
    fdata['operator'] = fdata.operator.str.strip()
    fdata['operatingOperator'] = fdata.operatingOperator.str.strip()

    # Fill ICAO24 of the last version of flight data
    fdata['ifplId_group'] = fdata.ifplId.copy()
    propagate_columns = ['icao24', 'actualTakeOffTime', 'actualTimeOfArrival']
    for pc in propagate_columns:
        fdata[pc] = fdata.groupby('ifplId_group')[pc].ffill()
    fdata = fdata.drop('ifplId_group', axis=1)

    # Final clean
    fdata = fdata.drop_duplicates(subset=dups_columns, keep='last').reset_index(drop=True)

    return fdata

### FLIGHTS ---------------------------------------------------------------------------------------

# NM ADRR Flights

NAME_MAPPING_ADRR_FLIGHTS = {
    'ECTRL ID': 'ifplId',
    'ADEP': 'aerodromeOfDeparture',
    'ADES': 'aerodromeOfDestination',
    'FILED OFF BLOCK TIME': 'estimatedOffBlockTime',
    'FILED ARRIVAL TIME': 'estimatedTimeOfArrival',
    'ACTUAL OFF BLOCK TIME': 'actualOffBlockTime',
    'ACTUAL ARRIVAL TIME': 'actualTimeOfArrival',
    'AC Type': 'aircraftType',
    'AC Operator': 'operator',
    'AC Registration': 'callsign',
    'ICAO Flight Type': 'flightType',
    'Actual Distance Flown (nm)': 'routeLength',
}

def adrr_flights_process(date: str|datetime.date) -> None:
    """ Process Eurocontrol ADRR Flights records for one date.

    The pipeline normalizes the schema, removes duplicated records and persist the results.

    Args:
        date: Date in "YYYY-MM-DD" format.

    Raises:
        FileNotFoundError: If no raw data files exist for the specified date.
    """
    input_files = list((paths.NM_RAW_ADRR_PATH / f'month={date[:-3]}').glob('*.csv'))
    if len(input_files) == 0:
        raise FileNotFoundError
    input_file = input_files[0]

    data = pd.read_csv(input_file, engine='pyarrow', dtype_backend='pyarrow')
    data['date'] = data['FILED OFF BLOCK TIME'].apply(lambda x: '-'.join(x[:10].split('-')[::-1]))
    data = data[data.date == date].drop('date', axis=1)
    data = nm_adrr_normalize_schema(data)
    data = nm_adrr_clean(data)

    # Write data
    output_dir = paths.ADRR_PARQUET_FLIGHTS_PATH
    paths.ensure_dir_exists(output_dir)
    output_file = output_dir / f'adrr.flights.{date}.parquet'
    data.to_parquet(output_file, index=False)

def nm_adrr_normalize_schema(data: pd.DataFrame) -> pd.DataFrame:
    """ Normalize schema and data types of raw Eurocontrol ADRR Flights records.

    The function selects the relevant columns, renames them and apply adequate data types.

    Args:
        data: Dataframe with raw ADRR Flights records.

    Returns:
        DataFrame with normalized Flight records and UTC-aware temporal fields.
    """

    # Remove unused columns
    data = data.drop(['ADEP Latitude', 'ADEP Longitude',
                      'ADES Latitude', 'ADES Longitude',
                      'STATFOR Market Segment', 'Requested FL'],
                     axis=1)

    # Rename columns
    data = data.rename(columns=NAME_MAPPING_ADRR_FLIGHTS)

    # Convert time columns
    time_columns = ['estimatedOffBlockTime', 'estimatedTimeOfArrival',
                    'actualOffBlockTime', 'actualTimeOfArrival']
    for column in time_columns:
        data[column] = pd.to_datetime(data[column].sort_values(), format='%d-%m-%Y %T', cache=True)
        data[column] = data[column].dt.tz_localize(pytz.utc).dt.as_unit('s')

    return data

def nm_adrr_clean(data: pd.DataFrame) -> pd.DataFrame:
    """ Removes duplicate records.

    Args:
        data: Dataframe with normalized ADRR Flights records.

    Returns:
        Cleaned and consolidated ADRR Flights dataFrame.
    """

    data = data.drop_duplicates()

    return data

# OpenSky Flights
NAME_MAPPING_OPENSKY_FLIGHTS = {
    'firstSeen': 'flightStart',
    'estDepartureAirport': 'departureAirport',
    'lastSeen': 'flightEnd',
    'estArrivalAirport': 'destinationAirport',
}

def opensky_flights_json_to_parquet(date: str|datetime.date) -> None:
    """Legacy conversion of OpenSky Flights JSON data to parquet.

    Flights are assigned to the partition of their lastSeen day. To capture
    flights spanning midnight, records from the target date and previous date are
    loaded before temporal filtering.

    Args:
        date: Target date in YYYY-MM-DD format.

    Returns:
        None.
    """
    # TODO: Align to process/normalize/clean structure
    date_dt = datetime.datetime.strptime(date, '%Y-%m-%d')
    date_prev_dt = date_dt - datetime.timedelta(days=1)
    date_prev = date_prev_dt.strftime('%Y-%m-%d')

    input_files = []
    if (paths.OPENSKY_RAW_FLIGHTS_PATH / f'flightDate={date_prev}').exists():
        input_files += list(paths.OPENSKY_RAW_FLIGHTS_PATH.glob(f'flightDate={date_prev}/*.json'))
    input_files += list(paths.OPENSKY_RAW_FLIGHTS_PATH.glob(f'flightDate={date}/*.json'))

    data = []
    for file_path in input_files:
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
    paths.ensure_dir_exists(folder)
    path = folder / f'os.flights.{date}.parquet'
    data.to_parquet(path, index=False)