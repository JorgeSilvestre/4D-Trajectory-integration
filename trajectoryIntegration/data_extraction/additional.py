import requests
from .. import paths

def extract_airports_ourAirports():
    url = r'https://davidmegginson.github.io/ourairports-data/airports.csv'
    paths.ensure_dir_exists(paths.AIRPORTS_RAW_PATH)
    with open(paths.AIRPORTS_RAW_PATH / 'airports.csv', 'wb') as file:
        csv_file = requests.get(url)
        file.write(csv_file.content)

def extract_runways_ourAirports():
    url = r'https://davidmegginson.github.io/ourairports-data/runways.csv'
    paths.ensure_dir_exists(paths.RUNWAYS_RAW_PATH)
    with open(paths.RUNWAYS_RAW_PATH / 'runways.csv', 'wb') as file:
        csv_file = requests.get(url)
        file.write(csv_file.content)

def extract_airports_fr24():
    # Blocked by cloudflare, requires manual download
    url = r'https://www.flightradar24.com/_json/airports.php'
    paths.ensure_dir_exists(paths.AIRPORTS_RAW_PATH)
    with open(paths.AIRPORTS_RAW_PATH / 'airports.json', 'wb') as file:
        json_file = requests.get(url, params={'content-type': 'application/json'})
        file.write(json_file.content)

def extract_airlines_fr24():
    # Blocked by cloudflare, requires manual download
    url = r'https://www.flightradar24.com/_json/airlines.php'
    paths.ensure_dir_exists(paths.AIRLINES_RAW_PATH)
    with open(paths.AIRLINES_RAW_PATH / 'airlines.json', 'wb') as file:
        json_file = requests.get(url)
        file.write(json_file.content)