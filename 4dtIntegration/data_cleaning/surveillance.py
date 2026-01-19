import pandas as pd
import json
from tqdm import tqdm

from .. import params, paths

mapping_opensky = {
    'hexid'               :'icao24',
    'time_stamp'          :'time_position',
    'time_stamp_velocity' :'last_contact',
    'track'               :'true_track',
    'altitude'            :'geo_altitude',
    'ground_speed'        :'velocity',
}

def vectors_clean_parquet(date: str) -> None:
    file_paths = list(paths.OPENSKY_RAW_VECTORS_PATH.glob(f'flightDate={date}/*.parquet'))

    dir = paths.OPENSKY_PARQUET_VECTORS_PATH / f'flightDate={date}'
    if not dir.exists():
        dir.mkdir(parents=True)
    for file_path in tqdm(file_paths, desc=f'{date} VECTORS | Clean  ', ncols=125, disable=False):
        data = pd.read_parquet(file_path, engine='pyarrow', dtype_backend='pyarrow')
        data = op_vectors_change_schema(data)
        data = vectors_clean(data)
        data.to_parquet(paths.OPENSKY_PARQUET_VECTORS_PATH / f'flightDate={date}' / file_path.name, index=False)

def op_vectors_change_schema(data: pd.DataFrame)  -> pd.DataFrame:
    # Remove unused columns
    data = data.drop(['sensors', 'spi', 'position_source'], axis=1)

    # Rename vector attributes
    data = data.rename(columns=mapping_opensky)

    # Data types
    data['longitude'] = data.longitude.astype('Float32[pyarrow]')
    data['latitude'] = data.latitude.astype('Float32[pyarrow]')
    data['baro_altitude'] = data.baro_altitude.astype('Float32[pyarrow]')
    data['geo_altitude'] = data.geo_altitude.astype('Float32[pyarrow]')
    data['true_track'] = data.true_track.astype('Float32[pyarrow]')
    data['velocity'] = data.velocity.astype('Float32[pyarrow]')
    data['vertical_rate'] = data.vertical_rate.astype('Float32[pyarrow]')
    data['time_position'] = data.time_position.astype('Int64[pyarrow]')//10**9
    data['last_contact'] = data.last_contact.astype('Int64[pyarrow]')//10**9
    data['on_ground'] = data.on_ground.astype('Boolean[pyarrow]')

    return data

def vectors_clean(data: pd.DataFrame) -> pd.DataFrame:
    """Processes individual vectors data problems

    Args:
        data: Dataframe with a day of vectors data
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

    # Remove vectors constructed with reused positions
    data = data.drop_duplicates(subset=['icao24','time_position','latitude','longitude'])

    # Clean trailing spaces in callsign
    data['callsign'] = data.callsign.str.strip(' ')

    # Format
    data['icao24'] = data.icao24.str.upper()
    data['callsign'] = data.callsign.str.upper()

    # Define NA value for text attributes
    data['callsign'] = data.callsign.replace('', pd.NA)
    data['origin_country'] = data.origin_country.replace('', pd.NA)

    # Sort vectors
    data = data.sort_values(by=['icao24','time_position'])

    # Add columns
    # Use latest position time as the state vector timestamp
    data['timestamp'] = data.time_position.copy()
    # Use baro_altitude as default altitude
    data['altitude'] = data.geo_altitude.copy()

    # Unique ID
    # data['vectorId'] = date.replace('-','') + '-' + data.icao24 + '-' + data.timestamp.astype(str)

    # Sort columns
    data = data[params.vector_attribute_names]

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
            folder.mkdir()
        data.to_parquet(folder / f'{file_path.stem}.parquet', index=False)