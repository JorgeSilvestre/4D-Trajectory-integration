"""Cleaning utilities for auxiliary static datasets (L0 → L1).

This module currently provides airport reference ingestion from two raw sources:

- `fr24_airports_process`: JSON snapshot to parquet.
- `ourairports_airports_process`: CSV snapshot (filtered to large airports) to parquet.

Both utilities normalize geospatial/elevation fields and persist to the common
airport L1 parquet path used by downstream enrichment steps.
"""

import json

import pandas as pd

from .. import paths

def fr24_airports_process() -> None:
    """Convert FlightRadar24 airport JSON data into normalized parquet format.

    Reads a local JSON snapshot, normalizes geospatial column names, and writes
    the result to the common airport parquet target path.

    Returns:
        None.
    """
    with open(paths.AIRPORTS_RAW_PATH / 'airports.json', 'r', encoding='utf8') as file:
        data = json.load(file)['rows']
    data = pd.DataFrame.from_dict(data)
    data['alt'] = data.alt.astype(int)

    data = data.rename(dict(
        lat='latitude',
        lon='longitude',
        alt='altitude',
    ), axis=1)

    if not paths.AIRPORTS_PATH.parent.exists():
        paths.AIRPORTS_PATH.parent.mkdir(parents=True)
    data.to_parquet(paths.AIRPORTS_PATH, engine='pyarrow', index=False)

def ourairports_airports_process() -> None:
    """Convert an OurAirports CSV snapshot into normalized parquet format.

    The transformation keeps only `large_airport` records and projects a subset
    of identifier and geospatial columns used in this project.

    Returns:
        None.
    """
    file_path = paths.AIRPORTS_RAW_PATH / 'airports.csv'
    data = pd.read_csv(file_path)
    # Only large airports
    data = data[data.type=='large_airport']

    # Normalize schema
    data = data[[
        'ident', 'icao_code', 'iata_code',
        'name', 'latitude_deg', 'longitude_deg', 'elevation_ft',
        'continent', 'iso_country', 'iso_region',
    ]]
    data = data.rename({
        'latitude_deg': 'latitude',
        'longitude_deg': 'longitude',
        'elevation_ft': 'elevation',
    }, axis=1)
    data['elevation'] = data.elevation.astype('int32[pyarrow]')
    data['latitude'] = data.latitude.astype('float32[pyarrow]')
    data['longitude'] = data.longitude.astype('float32[pyarrow]')

    if not paths.AIRPORTS_PATH.parent.exists():
        paths.AIRPORTS_PATH.parent.mkdir(parents=True)
    data.to_parquet(paths.AIRPORTS_PATH, index=False)