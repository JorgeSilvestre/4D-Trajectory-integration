import datetime

import pandas as pd

from .. import params, paths

# OpenSky flights not used
def opensky_integrate_flight_vectors(date: str, source: str, airports_dep: list|tuple = tuple()) -> None:
    """Join flight data and state vectors to identify individual trajectories

    Args:
        date: String with a date in format 'YYYY-MM-DD'
        source: The data source for flight data
        airports: A list with the desired origin airports
    """

    if source == 'opensky':
        # TODO Integración con OpenskyFlights
        flights = pd.read_parquet(paths.OPENSKY_PARQUET_FLIGHTS_PATH / f'flightDate={date}')
        # Filter by airports
        if airports_dep:
            flights = flights[flights.estDepartureAirport.isin(airports_dep) & flights.estArrivalAirport.isin(airports_dep)]
        # Remove flights with the same origin and destination
        flights = flights[flights.estDepartureAirport != flights.estArrivalAirport]
    elif source == 'nm':
        flights = pd.read_parquet(paths.NM_PARQUET_FLIGHTS_PATH / f'nm.flights.{date}.parquet')
        # flights = flights[flights.flightState == 'TERMINATED']
        # Filter by airports
        if airports_dep:
            flights = flights[flights.aerodromeOfDeparture.isin(airports_dep) & flights.aerodromeOfDestination.isin(airports_dep)]
        # Remove flights with the same origin and destination
        flights = flights[flights.aerodromeOfDeparture != flights.aerodromeOfDestination]
    else:
        print('Choose a valid flight data source.')
        return


    date_dt =  datetime.datetime.strptime(date, '%Y-%m-%d')
    date_prev_dt = date_dt - datetime.timedelta(days=1)
    date_prev = date_prev_dt.strftime('%Y-%m-%d')

    file_paths = []
    if (paths.OPENSKY_PARQUET_VECTORS_PATH / f'flightDate={date_prev}').exists():
        file_paths += list(paths.OPENSKY_PARQUET_VECTORS_PATH.glob(f'flightDate={date_prev}/*.parquet'))
    file_paths += list(paths.OPENSKY_PARQUET_VECTORS_PATH.glob(f'flightDate={date}/*.parquet'))

    print(f'#        {"Vectors":<15}{"Flights":<15}{"Join vectors":<15}'+
          f'{"% join vec":<18}{"Join flights":<15}{"% join fl":<18}')

    joined_flights = []
    joined_vectors_acc = []
    for idx, file_path in enumerate(file_paths):
        vectors = pd.read_parquet(file_path, engine='pyarrow', dtype_backend='pyarrow').dropna(subset=['timestamp'])

        num_initial_vectors = vectors.shape[0]
        vectors = vectors[vectors.icao24.isin(flights.icao24.unique())]
        if vectors.shape[0] == 0:
            continue

        joined = pd.merge(vectors.drop('callsign',axis=1), flights, on='icao24', how='inner')
        if source == 'opensky':
            joined = joined[(joined.timestamp >= joined.firstSeen) &
                            (joined.timestamp <= joined.lastSeen)]
            joined_flights.append(flights[flights.flightId.isin(joined.flightId.drop_duplicates())])
            joined_vectors = joined[vectors.columns.to_list()+['flightId']].drop_duplicates()
        elif source == 'nm':
            joined = joined[(joined.timestamp >= joined.actualTakeOffTime - params.TIME_EXPANSION) &
                            (joined.timestamp <= joined.actualTimeOfArrival + params.TIME_EXPANSION)]
            joined_flights.append(flights[flights.ifplId.isin(joined.ifplId.drop_duplicates())])
            joined_vectors = joined[vectors.columns.to_list()+['ifplId']].drop_duplicates()

            # joined_vectors = joined_vectors.rename(parameters.NM_FLIGHTS_RENAME, axis=1)

        # if source == 'opensky':
        #     folder = OPENSKY_JOINED_VECTORS_PATH / f'flightDate={date}'
        # elif source == 'nm':
        #     folder = NM_TRAJECTORIES_RAW_PATH / f'flightDate={date}'

        # if not folder.exists():
        #     folder.mkdir(parents=True)
        # if len(joined_vectors)>0:
        #     path = folder / f'vectors.{joined_vectors.timestamp.min()}.parquet'
        #     joined_vectors.to_parquet(path, index=False,)

        joined_vectors_acc.append(joined_vectors)

        nvec = num_initial_vectors
        nfl = flights.shape[0]
        # njvec = joined_vectors[-1].shape[0]
        njvec = joined_vectors.shape[0]
        njfl = joined_flights[-1].shape[0]
        print(f'{idx+1:>3}/{len(file_paths)}  {nvec:<15}{nfl:<15}{njvec:<15}'+
              f'{njvec/nvec*100:<18.2f}{njfl:<15}{njfl/nfl*100:<18.2f}')

    if joined_vectors_acc:
        joined_vectors = pd.concat(joined_vectors_acc)
        joined_vectors = joined_vectors.drop_duplicates()
        joined_vectors = joined_vectors.sort_values(by=['ifplId', 'timestamp']).reset_index(drop=True)
        folder = NM_TRAJECTORIES_RAW_PATH
        if len(joined_vectors)>0:
            path = folder / f'vectors.{date}.parquet'
            joined_vectors.to_parquet(path, index=False,)

    if joined_flights:
        joined_flights = pd.concat(joined_flights)
        joined_flights = joined_flights.drop_duplicates()

    return joined_flights

    if source == 'opensky':
        # TODO Integración con OpenskyFlights
        folder = paths.OPENSKY_JOINED_FLIGHTS_PATH / f'flightDate={date}'
        # Rename columns for later steps
        # joined_flights = joined_flights.rename(parameters.OP_FLIGHTS_RENAME, axis=1)
    elif source == 'nm':
        folder = paths.NM_JOINED_FLIGHTS_PATH / f'flightDate={date}'
        # Rename columns for later steps
        # joined_flights = joined_flights.rename(parameters.NM_FLIGHTS_RENAME, axis=1)
    if not folder.exists():
        folder.mkdir()
    path =  folder / f'flights.{date.replace("-", "")}.parquet'
    joined_flights.to_parquet(path, index=False)
