import json

from trajectoryIntegration.trajectory import Trajectory
from .. import paths
import pandas as pd
from datetime import datetime, timedelta

def taf_current_report(month: str) -> None:
    """Processes TAF current reports by aggregating base, stable, and tempo changes.

    Args:
        month (str): String with a month in format 'YYYY-MM'.
    """
    input_file = paths.TAF_PARQUET_PATH / f'taf.{month}.parquet'
    data = pd.read_parquet(input_file, engine='pyarrow', dtype_backend='pyarrow')

    weather_data = [
        'wind_dir_degrees', 'wind_speed_kt', 'wing_gust_kt', 'wind_shear_hgt_ft_agl',
        'wind_shear_dir_degrees', 'wind_shear_speed_kt', 'visibility_statute_mi',
        'altim_in_hg', 'vert_vis_ft', 'wx_string', 'sky_condition',
        'turbulence_condition', 'icing_condition', 'temperature',
        'sky_cover','cloud_base_ft_agl','cloud_type','max_temp','min_temp',
        'max_temp_timestamp','min_temp_timestamp', ]

    folder = paths.TAF_PARQUET_PATH / f'taf.{month}.parquet'
    data = pd.read_parquet(folder, engine='pyarrow', dtype_backend='pyarrow', filters=[('station_id', '=', 'LEMD')])
    # filters=[('station_id', '=', 'LEMD')]

    # La situación "base" se define con los informes que dan una descripción detallada: base, AMD o COR
    bases = data[data.change_indicator.isna() | data.change_indicator.isin(['AMD', 'COR'])
                ].sort_values('issue_time')
    # Sobreescritura de COR
    bases = bases.groupby(['station_id', 'valid_time_to']).agg({x:'last' for x in weather_data}).reset_index(drop=False)

    # BECMG describe un cambio permanente en alguno de los factores del informe. Sobreescribe, con los campos informados,
    # los homólogos en la situación base a partir de su comienzo de validez
    stable = pd.concat([bases, data[data.change_indicator=='BECMG']]).sort_values(
        ['issue_time','valid_time_from','time_from', 'time_to'], na_position='first')
    stable = stable.groupby(['station_id', 'issue_time']).agg({x:'last' for x in weather_data}).reset_index(drop=False)

    # TEMPO describe un cambio temporal en alguno de los factores del informe.Sobreescribe, con los campos informados,
    # los homólogos en la situación base a partir de su comienzo de validez y hasta su final de validez
    tempo = pd.concat([stable, data[data.change_indicator=='TEMPO']]).sort_values(
        ['issue_time','valid_time_from','time_from', 'time_to'], na_position='first')
    tempo = tempo.groupby(['station_id', 'issue_time']).agg({x:'last' for x in weather_data}).reset_index(drop=False)

    # data = tempo.drop_duplicates()

    output_folder = paths.TAF_INTEGRATED_PATH
    if not output_folder.exists():
        output_folder.mkdir(parents=True)
    output_file = output_folder / f'taf.{month}.parquet'
    data.to_parquet(output_file, index=False)

def taf_integrate_vectors(date: str) -> None:
    next_day = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    prev_day = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')

    file_paths = paths.NM_TRAJECTORIES_PATH.glob(f'flightDate={date}/*.json')
    traj_ids = [str(x).split('.')[1] for x in file_paths]
    trajectories = (Trajectory(x, date, 'clean') for x in traj_ids)

    result = []
    for traj in trajectories:
        if traj.aerodromeOfDestination != 'LEMD': continue
        vectors = traj.vectors[['ifplId', 'timestamp']].copy()
        taf_reports = pd.read_parquet(
            paths.TAF_INTEGRATED_PATH / f'taf.{date[:-3]}.parquet',
            engine='pyarrow', dtype_backend='pyarrow',
            filters=[('date', 'in', [prev_day, date, next_day]),
                     ('station_id','=',traj.aerodromeOfDestination),])
        estimated_time_of_arrival = datetime.strptime(traj.estimatedTimeOfArrival, '%Y-%m-%dT%T%z')
        taf_reports = taf_reports[
            (taf_reports.valid_time_from < estimated_time_of_arrival) | 
            (taf_reports.valid_time_to > estimated_time_of_arrival)]
        joined = pd.merge(vectors, taf_reports, how='cross')
        joined = joined[(joined.issue_time < joined.timestamp)]
    
        pass
                #  ('valid_time_from','<',datetime.strptime(traj.estimatedTimeOfArrival, '%Y-%m-%dT%T%z')),
                    #  ('valid_time_to','>',datetime.strptime(traj.estimatedTimeOfArrival, '%Y-%m-%dT%T%z'))

