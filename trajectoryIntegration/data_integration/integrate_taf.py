from datetime import datetime, timedelta

import pandas as pd
from tqdm import tqdm

from .. import paths
from ..trajectory import Trajectory


def taf_current_report(month: str, airports: list = []) -> None:
    """Processes TAF current reports by aggregating base, stable, and tempo changes.

    Args:
        month (str): String with a month in format 'YYYY-MM'.
    """
    input_file = paths.TAF_PARQUET_PATH / f'taf.{month}.parquet'
    if len(airports)>0:
        taf_records = pd.read_parquet(input_file,
                            engine='pyarrow', dtype_backend='pyarrow',
                            filters=[('station_id', 'in', airports)])
    else:
        taf_records = pd.read_parquet(input_file, engine='pyarrow', dtype_backend='pyarrow')

    forecast_columns = [
        'wind_dir_degrees', 'wind_speed_kt', 'wing_gust_kt', 'wind_shear_hgt_ft_agl',
        'wind_shear_dir_degrees', 'wind_shear_speed_kt', 'visibility_statute_mi',
        'altim_in_hg', 'vert_vis_ft', 'wx_string', 'sky_condition',
        'turbulence_condition', 'icing_condition', 'temperature',
        'sky_cover','cloud_base_ft_agl','cloud_type','max_temp','min_temp',
        'max_temp_timestamp','min_temp_timestamp', 'date']

    results = []
    for airport in airports:
        data = taf_records[taf_records.station_id == airport]

        # La situación "base" se define con los informes que dan una descripción detallada: base, AMD o COR
        bases = data[data.change_indicator.isna() | data.change_indicator.isin(['AMD', 'COR'])]
        bases = bases.sort_values('issue_time')
        # Sobreescritura de COR
        bases = bases.groupby(['station_id','valid_time_to']).agg({x:'last' for x in forecast_columns})
        bases = bases.reset_index(drop=False)

        # BECMG describe un cambio permanente en alguno de los factores del informe. Sobreescribe, con los campos informados,
        # los homólogos en la situación base a partir de su comienzo de validez
        stable = pd.concat([bases, data[data.change_indicator=='BECMG']])
        stable = stable.sort_values(['issue_time','valid_time_from','time_from','time_to'], na_position='first')
        stable = stable.groupby(['station_id','issue_time']).agg({x:'last' for x in forecast_columns})
        stable = stable.reset_index(drop=False)

        # TEMPO describe un cambio temporal en alguno de los factores del informe.Sobreescribe, con los campos informados,
        # los homólogos en la situación base a partir de su comienzo de validez y hasta su final de validez
        tempo = pd.concat([stable, data[data.change_indicator=='TEMPO']])
        tempo = tempo.sort_values(['issue_time','valid_time_from','time_from','time_to'], na_position='first')
        tempo = tempo.groupby(['station_id','issue_time']).agg({x:'last' for x in forecast_columns})
        tempo = tempo.reset_index(drop=False)

        data = tempo #.drop_duplicates()

        results.append(data)

    data = pd.concat(results).sort_values(by=['station_id', 'issue_time'])
    del results
    data['situation_id'] = (data.station_id + data.issue_time.dt.total_seconds()
                                                    .astype('int64[pyarrow]')
                                                    .astype('string[pyarrow]'))

    output_dir = paths.TAF_INTEGRATED_PATH
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    output_file = output_dir / f'taf.{month}.parquet'
    data.to_parquet(output_file, index=False)

def taf_integrate_vectors(date: str) -> None:
    next_day = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    prev_day = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')

    file_path = paths.NM_TRAJECTORIES_PATH / f'flightDate={date}/flights.{date}.parquet'
    traj_ids = pd.read_parquet(file_path, columns=['ifplId'], engine='pyarrow').ifplId.to_list()
    trajectories = (Trajectory(x, date, 'clean') for x in traj_ids)

    result = []
    taf_reports = pd.read_parquet(
            paths.TAF_INTEGRATED_PATH / f'taf.{date[:-3]}.parquet',
            engine='pyarrow', dtype_backend='pyarrow',
            filters=[('date', 'in', (next_day, date, prev_day))])

    for traj in tqdm(trajectories, desc=f'{date} VECTORS-TAF', ncols=125, total=len(traj_ids)):
        vectors = traj.vectors
        station_reports = taf_reports[taf_reports.station_id == traj.aerodromeOfDestination]

        vectors['forecast'] = pd.cut(
            vectors.timestamp.dt.total_seconds(),
            station_reports.issue_time.dt.total_seconds(),
            labels=station_reports.situation_id[:-1]
        )
        result.append(traj)

    vectors = pd.concat([traj.vectors for traj in result])
    output_dir = paths.NM_TRAJECTORIES_PATH / f'flightDate={date}'
    vectors.to_parquet(output_dir / f'vectors.{date}.parquet', index=False)
    taf_reports.to_parquet(output_dir / f'taf.{date}.parquet', index=False)

