"""Network Manager data integration (L1 → L2).

This module integrates Network Manager flight metadata with OpenSky surveillance data
to construct raw 4D trajectories (L2). The integration process involves two main steps:

1. Merging flight plan (FPLAN) and flight data (FDATA) into consolidated flight records
2. Matching flight records with state vectors to identify individual trajectories

The module produces L2 trajectory outputs consisting of:
- State vectors partitioned by flight (parquet format)
- Flight metadata per trajectory (JSON format)
- Integration metrics (JSON format)

The integration is performed per date and follows the data maturity model:
- Input: L1 cleaned flight plans, flight data, and state vectors
- Output: L2 raw trajectories with matched surveillance data
"""

import pandas as pd
import json
import datetime

from .. import params, paths, utils

# Flight attribute schema for consolidated flight records
FLIGHT_ATTRIBUTE_NAMES = [
    'ifplId', 'icao24', 'callsign',
    'estimatedOffBlockTime', 'aerodromeOfDeparture', 'aerodromeOfDestination',
    'operator', 'operatingOperator', 'flightState',
    'estimatedTakeOffTime', 'estimatedTimeOfArrival', 'actualTakeOffTime',
    'actualTimeOfArrival', 'calculatedTakeOffTime', 'calculatedTimeOfArrival',
    'flightType', 'registrationMark', 'ssr', 'totalEstimatedElapsedTime',
    'wakeTurbulenceCategory', 'aircraftType', 'routeLength', ]

def nm_merge_fplan_fdata(date: str) -> None:
    """Merge Network Manager flight plan and flight data into consolidated flight records.

    Combines information from flight plan messages (FPLAN) and flight data messages
    (FDATA) for a given date. The function resolves message versioning, consolidates
    duplicate attributes, and validates temporal consistency between the two sources.

    The merged dataset contains both planned information (from FPLAN) and actual
    operational data (from FDATA), providing a complete view of each flight.

    Args:
        date: Processing date in format 'YYYY-MM-DD'.

    Returns:
        None. Writes consolidated flight records to:
            `data/L1/nmFlights/nm.flights.{date}.parquet`

    Notes:
        - Both FPLAN and FDATA may contain multiple messages per flight (updates/amendments)
        - The function selects the last version of each message type
        - Duplicate attributes are resolved by preferring FDATA over FPLAN
        - Temporal validation ensures FPLAN and FDATA refer to the same flight
        - Output schema is defined in FLIGHT_ATTRIBUTE_NAMES
    """
    # Load cleaned L1 data
    fplan = pd.read_parquet(
            paths.NM_PARQUET_FPLAN_PATH / f'nm.fplan.{date}.parquet',
            engine='pyarrow', dtype_backend='pyarrow'
        ).drop('uuid', axis=1)
    fdata = pd.read_parquet(
            paths.NM_PARQUET_FDATA_PATH / f'nm.fdata.{date}.parquet',
            engine='pyarrow', dtype_backend='pyarrow'
        ).drop(['uuid', 'timestamp'], axis=1)

     # Select last flight plan version per flight
    last_fplan = (fplan.groupby('ifplId').timestamp.idxmax())
    fplan = fplan.loc[last_fplan]

    # Select last flight data version per flight
    # Special handling for TERMINATED flights: use first TERMINATED message
    # to avoid using messages with updated actualTimeOfArrival after landing
    last_fdata = []
    for gr_id, gr in fdata.groupby('ifplId'):
        # Multiple TERMINATED messages: use first to freeze arrival time
        if len(gr[gr.flightState == 'TERMINATED'])>1:
            l = gr[gr.flightState == 'TERMINATED'].iloc[0]
        # Single or no TERMINATED: use latest version
        else:
            l = gr.loc[gr.flightDataVersionNr.idxmax()]
        last_fdata.append(l)
    fdata = pd.DataFrame(last_fdata)

    # Merge FPLAN and FDATA on flight identifier
    flights = pd.merge(fplan, fdata, on='ifplId')

    # Consolidate duplicate columns (prefer FDATA values)
    consolidate_columns = [
        'icao24', 'callsign', 'estimatedOffBlockTime',
        'aerodromeOfDeparture', 'aerodromeOfDestination',
        'operator', 'operatingOperator', 'aircraftType'
    ]
    for col in consolidate_columns:
        flights[col] = flights[f'{col}_y'].combine_first(flights[f'{col}_x'])
        flights = flights.drop([f'{col}_x', f'{col}_y'], axis=1)

    # Validate temporal consistency between FPLAN and FDATA
    # Ensure they refer to the same flight by checking actual times align with estimated times
    flights = flights[
        (flights.actualTakeOffTime > flights.estimatedOffBlockTime - pd.Timedelta(days=1)) &
        (flights.actualTimeOfArrival < flights.estimatedOffBlockTime + pd.Timedelta(days=2))
    ]

    # Clean up
    flights = flights.drop_duplicates()
    flights = flights.drop(['timestamp', 'flightDataVersionNr'], axis=1)

    # Reorder columns to match standard schema
    flights = flights[FLIGHT_ATTRIBUTE_NAMES]

    output_dir = paths.NM_PARQUET_FLIGHTS_PATH
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    output_file = paths.NM_PARQUET_FLIGHTS_PATH / f'nm.flights.{date}.parquet'
    flights.to_parquet(output_file, index=False)

def nm_integrate_flight_vectors(date: str,
                                airports_dep: list|tuple = tuple(),
                                airports_dest: list|tuple = tuple()) -> None:
    """Integrate Network Manager flights with OpenSky state vectors to construct trajectories.

    Matches consolidated flight records with surveillance state vectors based on aircraft
    identifiers (icao24) and temporal alignment. The function produces raw 4D trajectories
    (L2) consisting of matched state vectors and flight metadata.

    Integration process:
    1. Load consolidated NM flight records and filter by airports/flight state
    2. Load OpenSky state vectors for the date (and next day for overnight flights)
    3. Match vectors to flights by icao24 and temporal overlap
    4. Filter trajectories with insufficient vectors
    5. Write trajectory data (vectors + metadata) and integration metrics

    Args:
        date: Processing date in format 'YYYY-MM-DD'.
        airports_dep: List of departure airport ICAO codes for filtering.
            Empty tuple means no filtering.
        airports_dest: List of destination airport ICAO codes for filtering.
            Empty tuple means no filtering.

    Returns:
        None. Writes outputs to:
            - `data/L2/nmTrajectories/tray.{date}.parquet`: All state vectors
            - `data/L2/nmTrajectories/flightDate={date}/tray.{ifplId}.json`:
              Metadata per trajectory
            - `reports/L2_integration_metrics/integration.{date}.json`:
              Integration statistics

    Notes:
        - Vectors are matched using TIME_EXPANSION parameter for temporal tolerance
        - Trajectories with fewer than MIN_VECTOR_NUMBER vectors are discarded
        - Integration metrics track success rates and data volume at each step
        - Overnight flights require loading vectors from the next day
    """

    integration_metrics = {}

    ## Load -------------------------------------------------------------------

    # Flight data
    filters = [('flightState','in',('TERMINATED','ATC_ACTIVATED','TATC_ACTIVATED'))]
    if airports_dep:
        filters.append(('aerodromeOfDeparture','in',airports_dep))
    if airports_dest:
        filters.append(('aerodromeOfDestination','in',airports_dep))
    flights = pd.read_parquet(
        paths.NM_PARQUET_FLIGHTS_PATH / f'nm.flights.{date}.parquet',
        engine='pyarrow', dtype_backend='pyarrow', filters=filters)

    integration_metrics['num_flights_initial'] = len(flights)

    # Remove return flights (same origin and destination)
    flights = flights[flights.aerodromeOfDeparture != flights.aerodromeOfDestination]

    integration_metrics['num_flights'] = len(flights)
    # integration_metrics['returned_flights'] = (
    #     integration_metrics['num_flights_initial'] - integration_metrics['num_flights'])

    # OpenSky data
    # Include vectors from next day for flights that cross midnight
    date_dt =  datetime.datetime.strptime(date, '%Y-%m-%d')
    date_next_dt = (date_dt + datetime.timedelta(days=1))
    date_next = date_next_dt.strftime('%Y-%m-%d')
    # Collect parquet files for current date
    file_paths = list(paths.OPENSKY_PARQUET_VECTORS_PATH.glob(f'flightDate={date}/*.parquet'))
    first_day_files = len(file_paths)
    # Add next day files if they exist (for overnight flights)
    if (paths.OPENSKY_PARQUET_VECTORS_PATH / f'flightDate={date_next}').exists():
        file_paths += list(paths.OPENSKY_PARQUET_VECTORS_PATH.glob(f'flightDate={date_next}/*.parquet'))

    ## Integration --------------------------------------------------------------------------------

    print(f'#       {"Vectors":<15}{"Flights":<15}{"Join vectors":<15}' +
          f'{"% join vec":<18}{"Join flights":<15}{"% join fl":<18}')

    joined_flights_acc = []
    joined_vectors_acc = []
    integration_metrics['num_vectors'] = 0
    unique_icao24_flights = flights.icao24.unique()

    # Process each vector file
    for idx, file_path in enumerate(file_paths):
        vectors = pd.read_parquet(file_path, engine='pyarrow', dtype_backend='pyarrow')
        num_initial_vectors = len(vectors)

        # Pre-filter vectors by icao24 (reduces join size)
        vectors_icao = vectors[vectors.icao24.isin(unique_icao24_flights)]
        if len(vectors_icao) == 0:
            continue
        del vectors

        # Join vectors with flights on icao24
        joined_vectors = pd.merge(
            flights,
            vectors_icao, #.drop('callsign', axis=1),
            on='icao24', how='inner')
        # Filter by temporal overlap: vector must be within flight execution window
        # Apply TIME_EXPANSION tolerance for vectors near takeoff/landing
        joined_vectors = joined_vectors[
            (joined_vectors.timestamp >= joined_vectors.actualTakeOffTime - pd.Timedelta(seconds=params.TIME_EXPANSION)) &
            (joined_vectors.timestamp <= joined_vectors.actualTimeOfArrival + pd.Timedelta(seconds=params.TIME_EXPANSION))]
        if len(joined_vectors)>0:
            # Consolidate missing callsigns in vector data
            joined_vectors['callsign'] = joined_vectors.callsign_y.combine_first(joined_vectors.callsign_x)
            # Extract matched vectors with flight identifier
            joined_vectors = joined_vectors.loc[:, vectors_icao.columns.to_list()+['ifplId']].drop_duplicates()
            joined_vectors_acc.append(joined_vectors)
            joined_flights_acc.append(flights[flights.ifplId.isin(joined_vectors.ifplId.drop_duplicates())])

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
        num_joined_vec = len(joined_vectors)
        num_joined_flight = len(joined_flights_acc[-1])
        print(f'{idx+1:>3}/{len(file_paths)}  {num_vec:<15}{num_flight:<15}{num_joined_vec:<15}'+
              f'{num_joined_vec/num_vec*100:<18.2f}{num_joined_flight:<15}{num_joined_flight/num_flight*100:<18.2f}')
        # Track vectors from primary date only (not next day)
        if idx<first_day_files:
            integration_metrics['num_vectors'] += num_vec

    ## Write data ---------------------------------------------------------------------------------

    if len(joined_vectors_acc)>0:
        joined_vectors = pd.concat(joined_vectors_acc).drop_duplicates()
        joined_vectors = joined_vectors.sort_values(by=['ifplId', 'timestamp']).reset_index(drop=True)
        del joined_vectors_acc

        integration_metrics['num_joined_vectors'] = len(joined_vectors)
        integration_metrics['num_joined_flights'] = len(joined_vectors.ifplId.unique())

        # Remove trajectories with insufficient vectors
        vector_counts = joined_vectors.groupby('ifplId').size()
        sufficient_vectors = vector_counts[vector_counts >= params.MIN_VECTOR_NUMBER]
        joined_vectors = joined_vectors[joined_vectors.ifplId.isin(sufficient_vectors.index)]

        integration_metrics['num_joined_vectors_final'] = len(joined_vectors)
        integration_metrics['num_joined_flights_final'] = len(sufficient_vectors)
        integration_metrics['removed_short_trajectories'] = integration_metrics['num_joined_flights'] - len(sufficient_vectors)
        del sufficient_vectors

        def get_metadata(flight_id):
            flight = flights[flights.ifplId == flight_id]
            flight_vectors = joined_vectors[joined_vectors.ifplId == flight_id]
            metadata = dict(
                date=date,
                ifplId=flight_id,
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
                num_vectores=len(flight_vectors),
                ts_start=flight_vectors.timestamp.min(),
                ts_end=flight_vectors.timestamp.max(),
                data_source_surveillance='opensky',
                data_source_flights='nm',
                flightState=flight.flightState.values[0],
                trajectory_status='L2_cleaned',
            )
            return metadata

        folder = paths.NM_TRAJECTORIES_RAW_PATH / f'flightDate={date}'
        if not folder.exists():
            folder.mkdir(parents=True)
        # Write trajectory data
        file_path = folder / f'vectors.{date}.parquet'
        joined_vectors.reset_index(drop=True).to_parquet(file_path, index=False)
        # Write trajectory metadata
        metadata = list(map(get_metadata, joined_vectors.ifplId.drop_duplicates()))
        file_path = folder / f'flights.{date}.parquet'
        pd.DataFrame(metadata).to_parquet(file_path, index=False)

        # Write integration metrics
        if not paths.INTEGRATION_METRICS_PATH.exists():
            paths.INTEGRATION_METRICS_PATH.mkdir(parents=True)
        file_path = paths.INTEGRATION_METRICS_PATH / f'integration.{date}.json'
        with open(file_path, 'w+', encoding='utf8') as file:
            json.dump(integration_metrics, file, indent=2, default=utils.custom_json_encoder)

    return None