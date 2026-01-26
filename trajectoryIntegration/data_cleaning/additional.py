import json

import pandas as pd
from .. import paths

def airports_json_to_parquet() -> None:
    """Parse and transforms airport data from a CSV file and write into a parquet file
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

