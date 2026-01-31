import json

import pandas as pd
from .. import paths

def airports_json_to_parquet() -> None:
    """Parse and transforms airport data from a JSON file and write into a parquet file
    """
    # TODO: Cambiar al fichero CSV descargado desde OurAirports
    # https://ourairports.com/help/data-dictionary.html
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
        'latitude_deg':'latitude',
        'longitude_deg':'longitude',
        'elevation_ft':'elevation',
    }, axis=1)
    data['elevation'] = data.elevation.astype('int32[pyarrow]')
    data['latitude'] = data.latitude.astype('float32[pyarrow]')
    data['longitude'] = data.longitude.astype('float32[pyarrow]')

    if not paths.AIRPORTS_PATH.exists():
        paths.AIRPORTS_PATH.mkdir(parents=True)
    data.to_parquet(paths.AIRPORTS_PATH, index=False)