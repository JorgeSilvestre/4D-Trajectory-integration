import json
import sys
from datetime import datetime, timedelta

import pandas as pd
import requests
from pyhive import hive

from .. import paths

def _configure_hive_client() -> hive.Connection:
    with open('keys/hive_conf.json', 'r') as file:
        conf = json.load(file)
    try:
        conn = hive.Connection(**conf[0])
        print ("Connected to Hive.")
    except ImportError as e:
        print ("cant connect to Hive: ", e)
        try:
            conn = hive.Connection(**conf[1])
            print ("Connected to Hive.")
        except ImportError as e:
            print ("Cant connect to Hive: ", e)
            sys.exit(1)
    return conn

def extract_OpenSky_flights(date: str, airport_orig: str = None, airport_dest: str = None) -> None:
    day_start = datetime.strptime(date, '%Y-%m-%d')
    results = []

    if airport_orig and airport_dest:
        print('No pueden fijarse los dos aeropuertos a la vez.')
    elif airport_orig or airport_dest:
        day_end = day_start + timedelta(hours=24)
        ts_start = int(day_start.timestamp())
        ts_end = int(day_end.timestamp())-1
        if airport_orig:
            query = f'https://opensky-network.org/api/flights/departure?airport={airport_orig}&begin={ts_start}&end={ts_end}'
        elif airport_dest:
            query = f'https://opensky-network.org/api/flights/arrival?airport={airport_dest}&begin={ts_start}&end={ts_end}'
        response = requests.get(query)
        if response.status_code == 200:
            results = response.json()
        else:
            print(f'WARNING: Status code {response.status_code}')
            print(query)
            print(response.content)
    else:
        cur_dt = day_start
        day_end = day_start + timedelta(hours=24)

        while cur_dt < day_end:
            ts_start = int(cur_dt.timestamp())
            cur_dt = cur_dt + timedelta(hours=2)
            ts_end = int(cur_dt.timestamp())-1
            query = f'https://opensky-network.org/api/flights/all?begin={ts_start}&end={ts_end}'
            response = requests.get(query)
            if response.status_code == 200:
                results.extend(response.json())
            else:
                print(f'WARNING: Status code {response.status_code}')
                print(response.content)
                break

    if results:
        dir = paths.OPENSKY_RAW_FLIGHTS_PATH / f'flightDate={date}'
        if not dir.exists():
            dir.mkdir(parents=True)
        with open(dir / f'os.flight.{date}.json', 'w+', encoding='utf8') as file:
            json.dump(results, file)


def extract_OpenSky_vectors_gold(date: str, only_eu=True) -> None:
    conn = _configure_hive_client()
    cursor = conn.cursor()
    query = f"SELECT * FROM gold_zone.opensky WHERE part_date_utc = {date}"
    if only_eu:
        # query = f"SELECT * FROM gold_zone.opensky WHERE part_date_utc = '{date}' AND longitude > -20 AND longitude < 50 AND latitude > 20 LIMIT 300000"
        query = f"SELECT * FROM gold_zone.opensky WHERE part_date_utc = '{date}'"
        query += " AND longitude > -10 AND longitude < 40 AND latitude > 30 AND latitude < 70"
    cursor.execute(query)
    colnames = [x[0].split('.')[1] for x in cursor.description]

    folder = paths.OPENSKY_RAW_VECTORS_PATH / f'flightDate={date}'
    if not folder.exists():
        folder.mkdir(parents=True)

    print()
    counter = 0
    while batch := cursor.fetchmany(2_000_000):
        print(f'{date} Batch: {counter:>2}, Length: {len(batch):>6}', end='\r')
        data = pd.DataFrame(batch, columns=colnames)
        data.to_parquet(folder / f'os.vectors.{date}.{counter:0>3}.parquet', index=False)
        del data
        counter += 1