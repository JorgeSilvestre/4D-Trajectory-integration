import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import bson
import pymongo
from pyhive import hive
from tqdm import tqdm

from .. import paths

mapping_flightPlan = {
    'ifplId'                    :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.ifplId',
    'timestamp'                 :'ps:FlightPlanMessage.timestamp',
    'callsign'                  :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.aircraftId',
    'icao24'                    :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.aircraftAddress',
    'aerodromeOfDeparture'      :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aerodromeOfDeparture.icaoId',
    'aerodromeOfDestination'    :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aerodromesOfDestination.aerodromeOfDestination.icaoId',
    'estimatedOffBlockTime'     :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.estimatedOffBlockTime',
    'operator'                  :'ps:FlightPlanMessage.flightPlanData.structured.aircraftOperator',
    'operatingOperator'         :'ps:FlightPlanMessage.flightPlanData.structured.operatingAircraftOperator',
    'registrationMark'          :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.registrationMark',
    'ssr'                       :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.ssrInfo.code',
    'flightRules'               :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.flightRules',
    'flightType'                :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.flightType',
    'aircraftType'              :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftType.icaoId',
    'totalEstimatedElapsedTime' :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.totalEstimatedElapsedTime',
    'wakeTurbulenceCategory'    :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.wakeTurbulenceCategory',
    'uuid'                      :'ps:FlightPlanMessage.uuid',
}

mapping_flightData = {
    'ifplId'                  :'ps:FlightDataMessage.flightData.flightId.id',
    'timestamp'               :'ps:FlightDataMessage.timestamp',
    'callsign'                :'ps:FlightDataMessage.flightData.flightId.keys.aircraftId',
    'icao24'                  :'ps:FlightDataMessage.flightData.aircraftAddress',
    'aerodromeOfDeparture'    :'ps:FlightDataMessage.flightData.flightId.keys.aerodromeOfDeparture',
    'aerodromeOfDestination'  :'ps:FlightDataMessage.flightData.flightId.keys.aerodromeOfDestination',
    'estimatedOffBlockTime'   :'ps:FlightDataMessage.flightData.flightId.keys.estimatedOffBlockTime',
    'operator'                :'ps:FlightDataMessage.flightData.aircraftOperator',
    'operatingOperator'       :'ps:FlightDataMessage.flightData.operatingAircraftOperator',
    'estimatedTakeOffTime'    :'ps:FlightDataMessage.flightData.estimatedTakeOffTime',
    'estimatedTimeOfArrival'  :'ps:FlightDataMessage.flightData.estimatedTimeOfArrival',
    'actualOffBlockTime'      :'ps:FlightDataMessage.flightData.actualOffBlockTime',
    'actualTakeOffTime'       :'ps:FlightDataMessage.flightData.actualTakeOffTime',
    'actualTimeOfArrival'     :'ps:FlightDataMessage.flightData.actualTimeOfArrival',
    'calculatedTakeOffTime'   :'ps:FlightDataMessage.flightData.calculatedTakeOffTime',
    'calculatedTimeOfArrival' :'ps:FlightDataMessage.flightData.calculatedTimeOfArrival',
    'flightState'             :'ps:FlightDataMessage.flightData.flightState',
    'flightDataVersionNr'     :'ps:FlightDataMessage.flightData.flightDataVersionNr',
    'aircraftType'            :'ps:FlightDataMessage.flightData.aircraftType',
    'routeLength'             :'ps:FlightDataMessage.flightData.routeLength',
    'uuid'                    :'ps:FlightDataMessage.uuid',
}

def _configure_mongo_client() -> pymongo.MongoClient:
    with open('keys/mongodb_conf.json', 'r') as file:
        conf = json.load(file)
    client = pymongo.MongoClient(
        maxPoolSize = 20,
        **conf
    )
    return client

def _serialize_datetime(obj) -> str:
    if isinstance(obj, datetime):
            return obj.isoformat()
    if isinstance(obj, bson.objectid.ObjectId):
        return str(obj)
    raise TypeError("Type not serializable")

def extract_NMFPLAN_mongo(date: str, client: pymongo.MongoClient, 
                          airport_orig: list[str]=None, airport_dest: list[str]=None) -> None:
    sep_date = list(int(x) for x in date.split('-'))
    start = datetime(*sep_date,  0,  0,  0)
    end   = datetime(*sep_date, 23, 23, 59)

    query = {'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.estimatedOffBlockTime' : { '$gte' : start, '$lte' : end }}
    if airport_orig:
        query.update({'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aerodromeOfDeparture.icaoId' : { '$in' : airport_orig }})
    if airport_dest:
        query.update({'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aerodromesOfDestination.aerodromeOfDestination.icaoId' : { '$in' : airport_dest }})

    filters = {y:1 for _, y in mapping_flightPlan.items()}
    cursor = client.Boeing.NMFPL.find(query, filters, max_time_ms = 300000)

    temp = []
    for d in tqdm(cursor, desc=f'{datetime.now().strftime("%H:%M:%S")} FPlan {date}'):
        temp.append(d)
        # if len(temp)==100: break

    dir = paths.NM_JSON_FPLAN_PATH / f'flightDate={date}'
    if not dir.exists():
        dir.mkdir(parents=True)
    with open(dir / f'nm.fplan.{date}.json', 'w+', encoding='utf8') as file:
        json.dump(temp, file, default=_serialize_datetime) # , separators=['\n',':']


def extract_NMFDATA_mongo(date: str, client: pymongo.MongoClient, num_threads=0) -> None:
    sep_date = list(int(x) for x in date.split('-'))
    start = datetime(*sep_date,  0,  0,  0) - timedelta(days=2) #, tzinfo=pytz.timezone('UTC'))
    end   = datetime(*sep_date, 23, 23, 59) + timedelta(days=7) #, tzinfo=pytz.timezone('UTC'))
    records_per_file = 100000

    with open(paths.NM_JSON_FPLAN_PATH / f'flightDate={date}/nm.fplan.{date}.json', 'r', encoding='utf8') as file:
        data = json.load(file)
    fpIds = set()
    for i in data:
        elem = i['ps:FlightPlanMessage']['flightPlanData']['structured']['flightPlan'].get('ifplId', None)
        if elem:
            fpIds.add(elem)
        else:
            print('patata')
    fpIds = list(fpIds)

    dir = paths.NM_JSON_FDATA_PATH / f'flightDate={date}'
    if not dir.exists():
        dir.mkdir(parents=True)

    if num_threads: # Paralelizado - carga todos los resultados en memoria
        def extract_fpid_fdata(fpId):
            temp = []
            query = {
                # 'ps:FlightDataMessage.flightData.flightId.keys.aerodromeOfDeparture' : {'$in' : airport_list},
                # 'ps:FlightDataMessage.flightData.flightId.keys.aerodromeOfDestination' : {'$in' : airport_list},
                'ps:FlightDataMessage.flightData.flightId.keys.estimatedOffBlockTime' : { '$gte' : start, '$lte' : end },
                'ps:FlightDataMessage.flightData.flightId.id' : fpId}
            filters = {y:1 for x,y in mapping_flightData.items()}
            cursor = client.Boeing.NMFDATA_Snappy.find(query, filters, max_time_ms = 300000)
            for d in cursor:
                temp.append(d)

            return temp

        # print(f'Ejecutando paralelamente con {num_threads} hilos...')
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            results = list(tqdm(executor.map(extract_fpid_fdata, fpIds),
                                desc=f'{datetime.now().strftime("%H:%M:%S")} FData {date} | Extracción'))

        results = [y for x in results for y in x]
        temp = []
        counter = 0
        for d in tqdm(results, desc=f'{datetime.now().strftime("%H:%M:%S")} FData {date} | Escritura', ncols=125):
            temp.append(d)
            if len(temp)>=records_per_file:
                with open(dir / f'nm.fdata.{date}.{counter:0>3}.json', 'w+', encoding='utf8') as file:
                    json.dump(temp, file, default=_serialize_datetime)
                counter += 1
                temp = []
        with open(dir / f'nm.fdata.{date}.{counter:0>3}.json', 'w+', encoding='utf8') as file:
            json.dump(temp, file, default=_serialize_datetime)
    else: # Secuencial
        query = {
            'ps:FlightDataMessage.flightData.flightId.keys.estimatedOffBlockTime' : { '$gte' : start, '$lte' : end },
            'ps:FlightDataMessage.flightData.flightId.id' : {'$in' : fpIds}}
        filters = {y:1 for _, y in mapping_flightData.items()}
        cursor = client.Boeing.NMFDATA_Snappy.find(query, filters, max_time_ms = 7200000)

        counter = 0
        temp = []
        for d in tqdm(cursor, desc=f'{datetime.now().strftime("%H:%M:%S")} FData {date}', ncols=125):
            temp.append(d)
            if len(temp)>=records_per_file:
                with open(dir / f'nm.fdata.{date}.{counter:0>3}.json', 'w+', encoding='utf8') as file:
                    json.dump(temp, file, default=_serialize_datetime)
                counter += 1
                temp = []
        with open(dir / f'nm.fdata.{date}.{counter:0>3}.json', 'w+', encoding='utf8') as file:
            json.dump(temp, file, default=_serialize_datetime)