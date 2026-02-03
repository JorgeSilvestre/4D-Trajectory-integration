import pandas as pd
import json
import datetime

from .. import params, paths, utils

FLIGHT_ATTRIBUTE_NAMES = [
    'ifplId', 'icao24', 'callsign',
    'estimatedOffBlockTime', 'aerodromeOfDeparture', 'aerodromeOfDestination',
    'operator', 'operatingOperator', 'flightState',
    'estimatedTakeOffTime', 'estimatedTimeOfArrival', 'actualTakeOffTime',
    'actualTimeOfArrival', 'calculatedTakeOffTime', 'calculatedTimeOfArrival',
    'flightType', 'registrationMark', 'ssr', 'totalEstimatedElapsedTime',
    'wakeTurbulenceCategory', 'aircraftType', 'routeLength', ]

def nm_merge_fplan_fdata(date: str) -> None:
    """Merge NM flight plan and flight data from a given date

    Args:
        date: String with a date in format 'YYYY-MM-DD'
    """

    fplan = pd.read_parquet(paths.NM_PARQUET_FPLAN_PATH / f'nm.fplan.{date}.parquet',
                            engine='pyarrow', dtype_backend='pyarrow')
    fdata = pd.read_parquet(paths.NM_PARQUET_FDATA_PATH / f'nm.fdata.{date}.parquet',
                            engine='pyarrow', dtype_backend='pyarrow')
    fplan = fplan.drop('uuid', axis=1)
    fdata = fdata.drop(['uuid', 'timestamp'], axis=1)

    # Find last flight plan version
    last_fplan = (fplan.groupby('ifplId').timestamp.idxmax())
    fplan = fplan.loc[last_fplan]

    # Find last flight data version
    # Avoid those FDATA messages that change actualTimeOfArrival
    last_fdata = []
    for gr_id, gr in fdata.groupby('ifplId'):
        if len(gr[gr.flightState == 'TERMINATED'])>1:
            l = gr[gr.flightState == 'TERMINATED'].iloc[0]
        else:
            l = gr.loc[gr.flightDataVersionNr.idxmax()]
        last_fdata.append(l)
    fdata = pd.DataFrame(last_fdata)

    # Join FP-FD and consolidate duplicated columns
    flights = pd.merge(fplan, fdata, on='ifplId')
    flights['icao24'] = flights.icao24_y.combine_first(flights.icao24_x)
    flights = flights.drop(['icao24_x', 'icao24_y'], axis=1)
    flights['callsign'] = flights.callsign_y.combine_first(flights.callsign_x)
    flights = flights.drop(['callsign_x', 'callsign_y'], axis=1)
    flights['estimatedOffBlockTime'] = flights.estimatedOffBlockTime_y.combine_first(flights.estimatedOffBlockTime_x)
    flights = flights.drop(['estimatedOffBlockTime_x', 'estimatedOffBlockTime_y'], axis=1)
    flights['aerodromeOfDeparture'] = flights.aerodromeOfDeparture_y.combine_first(flights.aerodromeOfDeparture_x)
    flights = flights.drop(['aerodromeOfDeparture_x', 'aerodromeOfDeparture_y'], axis=1)
    flights['aerodromeOfDestination'] = flights.aerodromeOfDestination_y.combine_first(flights.aerodromeOfDestination_x)
    flights = flights.drop(['aerodromeOfDestination_x', 'aerodromeOfDestination_y'], axis=1)
    flights['operator'] = flights.operator_y.combine_first(flights.operator_x)
    flights = flights.drop(['operator_x', 'operator_y'], axis=1)
    flights['operatingOperator'] = flights.operatingOperator_y.combine_first(flights.operatingOperator_x)
    flights = flights.drop(['operatingOperator_x', 'operatingOperator_y'], axis=1)
    flights['aircraftType'] = flights.aircraftType_y.combine_first(flights.aircraftType_x)
    flights = flights.drop(['aircraftType_x', 'aircraftType_y'], axis=1)

    # Ensure that joined FP-FD pairs refer to the same flight (due to ifplId reutilization)
    flights = flights[
        (flights.actualTakeOffTime > flights.estimatedOffBlockTime - pd.Timedelta(days=1)) &
        (flights.actualTimeOfArrival < flights.estimatedOffBlockTime + pd.Timedelta(days=2))
    ]
    # flights = flights[
    #     (flights.actualTakeOffTime > flights.estimatedOffBlockTime - 24*3600) &
    #     (flights.actualTimeOfArrival < flights.estimatedOffBlockTime + 2*24*3600)
    # ]
    # Drop duplicate records
    flights = flights.drop_duplicates()
    # Drop timestamp and FDATA message version column
    flights = flights.drop(['timestamp', 'flightDataVersionNr'], axis=1)
    # Sort columns
    flights = flights[FLIGHT_ATTRIBUTE_NAMES]

    output_folder = paths.NM_PARQUET_FLIGHTS_PATH
    if not output_folder.exists():
        output_folder.mkdir(parents=True)
    output_file = paths.NM_PARQUET_FLIGHTS_PATH / f'nm.flights.{date}.parquet'
    flights.to_parquet(output_file, index=False)

def nm_integrate_flight_vectors(date: str, 
                                airports_dep: list|tuple = tuple(), 
                                airports_dest: list|tuple = tuple()) -> None:
    """Join flight data and state vectors to identify individual trajectories

    Args:
        date: String with a date in format 'YYYY-MM-DD'
        source: The data source for flight data
        airports: A list with the desired origin airports
    """

    integration_metrics = {}

    ## Load -------------------------------------------------------------------

    # Flight data
    filters = []
    filters.append(('flightState','in',('TERMINATED','ATC_ACTIVATED','TATC_ACTIVATED')))
    if airports_dep:
        filters.append(('aerodromeOfDeparture','in',airports_dep))
    if airports_dest:
        filters.append(('aerodromeOfDestination','in',airports_dep))
    flights = pd.read_parquet(paths.NM_PARQUET_FLIGHTS_PATH / f'nm.flights.{date}.parquet',
                              engine='pyarrow', dtype_backend='pyarrow', filters=filters)
    
    integration_metrics['num_flights_initial'] = len(flights)
    # Remove flights with the same origin and destination
    flights = flights[flights.aerodromeOfDeparture != flights.aerodromeOfDestination]
    integration_metrics['num_flights'] = len(flights)
    integration_metrics['returned_flights'] = integration_metrics['num_flights_initial'] - integration_metrics['num_flights']

    # OpenSky data
    # Include vectors from the next day (in case the flight takes place between two days)
    date_dt =  datetime.datetime.strptime(date, '%Y-%m-%d')
    date_next_dt = (date_dt + datetime.timedelta(days=1))
    date_next = date_next_dt.strftime('%Y-%m-%d')

    file_paths = []
    file_paths += list(paths.OPENSKY_PARQUET_VECTORS_PATH.glob(f'flightDate={date}/*.parquet'))
    first_day_files = len(file_paths)
    if (paths.OPENSKY_PARQUET_VECTORS_PATH / f'flightDate={date_next}').exists():
        file_paths += list(paths.OPENSKY_PARQUET_VECTORS_PATH.glob(f'flightDate={date_next}/*.parquet'))

    ## Integration --------------------------------------------------------------------------------

    print(f'#       {"Vectors":<15}{"Flights":<15}{"Join vectors":<15}' +
          f'{"% join vec":<18}{"Join flights":<15}{"% join fl":<18}')

    joined_flights_acc = []
    joined_vectors_acc = []
    integration_metrics['num_vectors'] = 0
    for idx, file_path in enumerate(file_paths):
        vectors = pd.read_parquet(file_path, engine='pyarrow', dtype_backend='pyarrow')
        num_initial_vectors = len(vectors)

        # Merge by icao24
        vectors_icao = vectors[vectors.icao24.isin(flights.icao24.unique())]
        del vectors
        if len(vectors_icao) == 0:
            continue
        joined = pd.merge(vectors_icao.drop('callsign', axis=1), flights, on='icao24', how='inner')
        joined = joined[
            (joined.timestamp >= joined.actualTakeOffTime - pd.Timedelta(seconds=params.TIME_EXPANSION)) &
            (joined.timestamp <= joined.actualTimeOfArrival + pd.Timedelta(seconds=params.TIME_EXPANSION))]
        # joined = joined[
        #     (joined.timestamp >= joined.actualTakeOffTime - params.TIME_EXPANSION) &
        #     (joined.timestamp <= joined.actualTimeOfArrival + params.TIME_EXPANSION)]
        joined = joined.loc[:, vectors_icao.columns.to_list()+['ifplId']].drop_duplicates()
        joined_icao24 = joined.ifplId.drop_duplicates()
        if len(joined)>0:
            joined_flights_acc.append(flights[flights.ifplId.isin(joined_icao24)])
            joined_vectors_acc.append(joined)

        # Merge by callsign
        # vectors_callsign = vectors[vectors.callsign.isin(flights.callsign.unique()) & ~vectors.index.isin(vectors_icao.index)].copy()
        # joined = pd.merge(vectors_callsign, flights.drop('icao24',axis=1), on='callsign', how='inner')
        # joined = joined[(joined.timestamp >= joined.actualTakeOffTime - params.TIME_SLACK) &
        #                 (joined.timestamp <= joined.actualTimeOfArrival + params.TIME_SLACK)]
        # joined_flights_acc.append(flights[flights.ifplId.isin(joined.ifplId.drop_duplicates())])
        # joined_vectors = joined[vectors_callsign.columns.to_list()+['ifplId']].drop_duplicates()
        # joined_vectors_acc.append(joined_vectors)

        # Metrics
        num_vec = num_initial_vectors
        num_flight = len(flights)
        num_joined_vec = len(joined)
        num_joined_flight = len(joined_flights_acc[-1])
        print(f'{idx+1:>3}/{len(file_paths)}  {num_vec:<15}{num_flight:<15}{num_joined_vec:<15}'+
              f'{num_joined_vec/num_vec*100:<18.2f}{num_joined_flight:<15}{num_joined_flight/num_flight*100:<18.2f}')
        if idx<first_day_files:
            integration_metrics['num_vectors'] += num_vec

    ## Write data ---------------------------------------------------------------------------------

    if joined_vectors_acc:
        joined_vectors = pd.concat(joined_vectors_acc).drop_duplicates()
        joined_vectors = joined_vectors.sort_values(by=['ifplId', 'timestamp']).reset_index(drop=True)
        del joined_vectors_acc
        integration_metrics['num_joined_vectors'] = len(joined_vectors)
        integration_metrics['num_joined_flights'] = len(joined_vectors.ifplId.unique())

        # Remove trajectories with too few vectors
        too_few_vectors = joined_vectors.groupby('ifplId').count()
        too_few_vectors = too_few_vectors[too_few_vectors.icao24>=params.MIN_VECTOR_NUMBER]
        joined_vectors = joined_vectors[joined_vectors.ifplId.isin(too_few_vectors.index)]
        integration_metrics['num_joined_vectors_final'] = len(joined_vectors)
        integration_metrics['num_joined_flights_final'] = len(too_few_vectors)
        integration_metrics['removed_short_trajectories'] = integration_metrics['num_joined_flights'] - len(too_few_vectors)
        del too_few_vectors

        # Write trajectory data
        folder = paths.NM_TRAJECTORIES_RAW_PATH
        if not folder.exists():
            folder.mkdir(parents=True)
        file_path = folder / f'tray.{date}.parquet'
        joined_vectors.reset_index(drop=True).to_parquet(file_path, index=False)

        # Write trajectory metadata
        folder = paths.NM_TRAJECTORIES_RAW_PATH / f'flightDate={date}'
        if not folder.exists():
            folder.mkdir(parents=True)
        for g, gdata in joined_vectors.groupby('ifplId'):
            flight = flights[flights.ifplId == g]

            metadata = dict(
                date=date,
                ifplId=g,
                callsign=flight.callsign.values[0],
                icao24=flight.icao24.values[0],
                aerodromeOfDeparture=flight.aerodromeOfDeparture.values[0],
                aerodromeOfDestination=flight.aerodromeOfDestination.values[0],
                airline=flight.operator.values[0] 
                        if pd.notna(flight.operator.values[0]) 
                        else flight.operatingOperator.values[0],
                estimatedTakeOffTime=(flight.estimatedTakeOffTime.values[0]),
                estimatedTimeOfArrival=(flight.estimatedTimeOfArrival.values[0]),
                actualTakeOffTime=(flight.actualTakeOffTime.values[0]),
                actualTimeOfArrival=(flight.actualTimeOfArrival.values[0]),
                num_vectores=len(gdata),
                ts_start=gdata.timestamp.min(),
                ts_end=gdata.timestamp.max(),
                data_source_surveillance='opensky',
                data_source_flights='nm',
                flightState=flight.flightState.values[0],
                trajectory_status='L2_cleaned',
            )
            with open(folder / f'tray.{g}.json', 'w+', encoding='utf8') as file:
                json.dump(metadata, file, indent=2, default=utils.custom_json_encoder)

        # Write integration metrics
        if not paths.INTEGRATION_METRICS_PATH.exists():
            paths.INTEGRATION_METRICS_PATH.mkdir(parents=True)
        file_path = paths.INTEGRATION_METRICS_PATH / f'integration.{date}.json'
        with open(file_path, 'w+', encoding='utf8') as file:
            json.dump(integration_metrics, file, indent=2, default=utils.custom_json_encoder)

    # if joined_flights_acc:
    #     joined_flights = pd.concat(joined_flights_acc)
    #     del joined_flights_acc
    #     joined_flights = joined_flights.drop_duplicates()
    #     return joined_flights

    return None