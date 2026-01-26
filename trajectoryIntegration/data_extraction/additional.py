import requests
from .. import paths

def extract_airports_ourAirports():
    url = r'https://davidmegginson.github.io/ourairports-data/airports.csv'
    if not paths.AIRPORTS_RAW_PATH.exists():
        paths.AIRPORTS_RAW_PATH.mkdir(parents=True)
    with open(paths.AIRPORTS_RAW_PATH / 'airports.csv', 'wb') as file:
        csv_file = requests.get(url)
        file.write(csv_file.content)

def extract_runways_ourAirports():
    url = r'https://davidmegginson.github.io/ourairports-data/runways.csv'
    if not paths.RUNWAYS_RAW_PATH.exists():
        paths.RUNWAYS_RAW_PATH.mkdir(parents=True)
    with open(paths.RUNWAYS_RAW_PATH / 'runways.csv', 'wb') as file:
        csv_file = requests.get(url)
        file.write(csv_file.content)

def extract_airports_fr24():
    url = r'https://www.flightradar24.com/_json/airports.php'
    if not paths.AIRPORTS_RAW_PATH.exists():
        paths.AIRPORTS_RAW_PATH.mkdir(parents=True)
    with open(paths.AIRPORTS_RAW_PATH / 'airports.json', 'wb') as file:
        csv_file = requests.get(url)
        file.write(csv_file.content)

def extract_airlines_fr24():
    url = r'https://www.flightradar24.com/_json/airlines.php'
    if not paths.AIRLINES_RAW_PATH.exists():
        paths.AIRLINES_RAW_PATH.mkdir(parents=True)
    with open(paths.AIRLINES_RAW_PATH / 'airlines.json', 'wb') as file:
        csv_file = requests.get(url)
        file.write(csv_file.content)