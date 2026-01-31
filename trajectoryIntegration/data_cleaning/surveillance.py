"""
Flight data cleaning (L0 → L1).

This module processes raw OpenSky state vectors (L0) into cleaned and
normalized vectors (L1), suitable for trajectory integration.

The pipeline performs source-specific schema normalization, basic data cleaning, temporal ordering,
semantic consolidation (valid positions) and removal of duplicate state vectors, producing
L1 parquet datasets ready for downstream integration.

The module is responsible for both processing logic and I/O, following a data
maturity model where L0 is raw data and L1 corresponds to cleaned, source-level data.
"""

import pandas as pd
import json
from tqdm import tqdm
import pytz

from .. import params, paths

NAME_MAPPING_OPENSKY = {
    'hexid': 'icao24',
    'time_stamp': 'time_position',
    'time_stamp_velocity': 'last_contact',
    'track': 'true_track',
    'altitude': 'geo_altitude',
    'ground_speed': 'velocity',
}

# L1 - Column order
VECTOR_ATTRIBUTE_NAMES = [
    'timestamp',
    'icao24',
    'callsign',
    'time_position',
    'last_contact',
    'latitude',
    'longitude',
    'altitude',
    'baro_altitude',
    'geo_altitude',
    'velocity',
    'vertical_rate',
    'true_track',
    'on_ground',
    'squawk',
    # Removed: spi, sensors, position_source, origin_country
]

def opensky_vectors_process(date: str) -> None:
    """
    Processes raw OpenSky state vectors for a given date into L1 format.

    This function implements the L0 → L1 processing pipeline for OpenSky surveillance data.
    For the specified date:

    - reads raw OpenSky state vectors (L0) from disk,
    - normalizes the schema and data types,
    - applies semantic cleaning and validation,
    - writes cleaned state vectors (L1) back to disk.

    The output preserves the original file partitioning by date.

    Args:
        date (str): Flight date to be processed, formatted as 'YYYY-MM-DD'.

    Returns:
        None
    """
    input_files = list(paths.OPENSKY_RAW_VECTORS_PATH.glob(f'flightDate={date}/*.parquet'))

    output_dir = paths.OPENSKY_PARQUET_VECTORS_PATH / f'flightDate={date}'
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    for file_path in tqdm(input_files, desc=f'{date} VECTORS | Clean  ', ncols=125, disable=False):
        data = pd.read_parquet(file_path, engine='pyarrow', dtype_backend='pyarrow')
        data = opensky_vectors_normalize_schema(data)
        data = opensky_vectors_clean(data)
        data.to_parquet(output_dir / file_path.name, index=False)

def opensky_vectors_normalize_schema(data: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes the schema and data types of raw OpenSky state vectors.

    This function performs structural normalization: it removes unused OpenSky attributes,
    renames columns to the internal naming convention, enforces data types using pyarrow-backed
    pandas dtypes, and converts timestamps from nanoseconds to seconds since epoch.

    Args:
        data (pd.DataFrame): Raw OpenSky state vectors as read from L0 storage.

    Returns:
        pd.DataFrame: State vectors with normalized schema and data types.
    """
    # Remove unused columns
    data = data.drop(['sensors', 'spi', 'position_source', 'origin_country'], axis=1)

    # Rename vector attributes
    data = data.rename(columns=NAME_MAPPING_OPENSKY)

    # Data types
    data['icao24'] = data.icao24.astype('string[pyarrow]')
    data['callsign'] = data.callsign.astype('string[pyarrow]')
    data['squawk'] = data.squawk.astype('string[pyarrow]')
    data['longitude'] = data.longitude.astype('Float32[pyarrow]')
    data['latitude'] = data.latitude.astype('Float32[pyarrow]')
    data['baro_altitude'] = data.baro_altitude.astype('Float32[pyarrow]')
    data['geo_altitude'] = data.geo_altitude.astype('Float32[pyarrow]')
    data['true_track'] = data.true_track.astype('Float32[pyarrow]')
    data['velocity'] = data.velocity.astype('Float32[pyarrow]')
    data['vertical_rate'] = data.vertical_rate.astype('Float32[pyarrow]')
    # The provided timestamps were converted to nanoseconds, so they are converted
    # back into seconds since epoch.
    # data['time_position'] = data.time_position.astype('Int64[pyarrow]')//10**9
    # data['last_contact'] = data.last_contact.astype('Int64[pyarrow]')//10**9
    data['time_position'] = pd.to_datetime(data.time_position.sort_values(), format='%Y-%m-%d %H:%M:%S',
                                           unit='ns', cache=True).dt.tz_localize(pytz.utc)
    data = data.sort_values(by=['last_contact'])
    data['last_contact'] = pd.to_datetime(data.last_contact.sort_values(), format='%Y-%m-%d %H:%M:%S',
                                          unit='ns', cache=True).dt.tz_localize(pytz.utc)

    data['on_ground'] = data.on_ground.astype('Boolean[pyarrow]')

    return data

def opensky_vectors_clean(data: pd.DataFrame) -> pd.DataFrame:
    """
    Applies semantic cleaning to normalized OpenSky state vectors.

    This function removes invalid or inconsistent state vectors and
    enforces basic physical and formatting constraints. Specifically:

    - removal of vectors with missing or invalid latitude/longitude,
    - filtering of positions outside valid geographic bounds,
    - removal of duplicated state vectors per aircraft and timestamp,
    - normalization of aircraft identifiers (ICAO24, callsign),
    - temporal ordering of state vectors per aircraft,
    - construction of derived attributes required at L1 level.

    The resulting dataset represents OpenSky L1 state vectors.

    Args:
        data (pd.DataFrame): Normalized OpenSky state vectors.

    Returns:
        pd.DataFrame: Cleaned and ordered OpenSky state vectors (L1).
    """

    # Remove vectors with null or incorrect values
    to_remove = (
        data.longitude.isna() |
        data.latitude.isna() |
        data.icao24.isna() |
        (~data.longitude.between(-180,180)) |
        (~data.latitude.between(-90,90))
    )
    data = data[~to_remove].copy()

    # Remove duplicated state vectors caused by repeated position reports
    data = data.drop_duplicates(subset=['icao24','time_position','latitude','longitude'])

    # Clean trailing spaces in callsign
    data['callsign'] = data.callsign.str.strip(' ')

    # Format
    data['icao24'] = data.icao24.str.upper()
    data['callsign'] = data.callsign.str.upper()

    # Define NA value for text attributes
    data['callsign'] = data.callsign.replace('', pd.NA)

    # Sort vectors
    data = data.sort_values(by=['icao24','time_position'])

    # Add columns
    # Use latest position time as the state vector timestamp
    data['timestamp'] = data.time_position.copy()
    # Use geometric altitude as default altitude
    data['altitude'] = data.geo_altitude.copy()

    # Unique ID
    # data['vectorId'] = date.replace('-','') + '-' + data.icao24 + '-' + data.timestamp.astype(str)

    # Sort columns
    data = data[VECTOR_ATTRIBUTE_NAMES]

    return data


# OpenSky vectors are already in parquet format
# TODO: Actualizar
def vectors_json_to_parquet(date: str) -> None:
    """Parse OpenSky state vectors from a JSON file and write into a parquet file

    Args:
        date: String with a date in format 'YYYY-MM-DD'
    """
     # 'category'
    file_paths = paths.OPENSKY_RAW_VECTORS_JSON_PATH.glob(f'flightDate={date}/*.json')

    for file_path in list(file_paths):
        data = []
        with open(file_path, 'r', encoding='utf8') as file:
            # One-shot
            # Requires exploding into columns
            # chunk_df = pd.read_json(file, lines=True)

            # Iterative, line by line
            chunks = []
            for line in tqdm(file, desc=f'{date} VECTORS', ncols=125):
                record = json.loads(line)
                chunk = pd.DataFrame(record['states'], columns=params.vector_attribute_names)
                chunk['timestamp'] = record['time']
                chunks.append(chunk)
            chunks_df = pd.concat(chunks)
            data.append(chunks_df)
        data = pd.concat(data)

        # Clean vectors
        data = vectors_clean(data)

        folder = paths.OPENSKY_PARQUET_VECTORS_PATH / f'flightDate={date}'
        if not folder.exists():
            folder.mkdir(parents=True)
        data.to_parquet(folder / f'{file_path.stem}.parquet', index=False)