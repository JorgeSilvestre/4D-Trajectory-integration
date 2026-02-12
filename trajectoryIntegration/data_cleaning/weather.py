"""Module for processing and cleaning TAF (Terminal Aerodrome Forecast) weather data.

This module provides functions to extract, normalize, and clean weather data from TAF
forecasts and reports. It handles temperature, sky conditions, and other meteorological
parameters, preparing the data for integration into trajectory analysis.
"""

import datetime
import os
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import pytz

from .. import paths


def _extract_temps(temp_records: list) -> list:
    """Extracts max and min temperatures and their timestamps from temperature records.

    Args:
        temp_records (list): List of dictionaries containing temperature data.

    Returns:
        list: A list of four elements: [max_temp, max_timestamp, min_temp, min_timestamp].
              Elements are pd.NA if not available.
    """
    if len(temp_records)==0:
        return [pd.NA]*4
    elif len(temp_records)==1:
        if temp_records[0]['min_temp_c']:
            return [pd.NA,pd.NA,temp_records[0]['min_temp_c'],temp_records[0]['valid_time']]
        elif temp_records[0]['max_temp_c']:
            return [temp_records[0]['max_temp_c'],temp_records[0]['valid_time'],pd.NA,pd.NA]
        else:
            return [pd.NA]*4
    elif len(temp_records)>1:
        res = [pd.NA]*4
        for rec in temp_records[:2]:
            if rec['min_temp_c']:
                res[2] = rec['min_temp_c']
                res[3] = rec['valid_time']
            elif rec['max_temp_c']:
                res[0] = rec['max_temp_c']
                res[1] = rec['valid_time']
        return res

def _extract_sky_conditions(sky_record: list) -> list:
    """Extracts sky cover, cloud base, and cloud type from sky condition records.

    Args:
        sky_record (list): List of dictionaries containing sky condition data.

    Returns:
        list: A list of three elements: [sky_cover, cloud_base_ft_agl, cloud_type].
              Elements are pd.NA if not available.
    """
    if len(sky_record)==0:
        return [pd.NA]*3
    elif len(sky_record)>0:
        return [
            sky_record[0]['sky_cover'],
            sky_record[0]['cloud_base_ft_agl'],
            sky_record[0]['cloud_type'] if sky_record[0]['cloud_type'] else pd.NA
        ]

def taf_forecast_process(month: str) -> None:
    """Parse TAF weather data (decoded) from a parquet file and write into a parquet file

    Args:
        month: String with a month in format 'YYYY-MM'
    """

    input_dir = paths.TAF_RAW_PATH / f'month={month}'

    data = pd.read_parquet(input_dir, engine='pyarrow', dtype_backend='pyarrow')

    # Parallelized
    max_workers = os.cpu_count()
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        step = len(data) // (4*max_workers)
        sorted_chunks = list(executor.map(
            _parallelize_taf_forecast_process,
            (data.iloc[i*step:(i+1)*step] for i in range(4*max_workers+1)),
            chunksize=1, buffersize=max_workers))
    data = pd.concat(sorted_chunks, axis=0)
    del sorted_chunks

    # Sequential
    # data = taf_forecast_normalize_schema(data)
    # data = taf_forecast_clean(data)

    output_dir = paths.TAF_PARQUET_PATH
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    output_file = output_dir / f'taf.{month}.parquet'
    data.to_parquet(output_file, index=False)

def _parallelize_taf_forecast_process(data: pd.DataFrame) -> pd.DataFrame:
    return taf_forecast_clean(taf_forecast_normalize_schema(data))

def taf_forecast_normalize_schema(data: pd.DataFrame) -> pd.DataFrame:
    """Normalizes the schema of TAF forecast data by dropping columns, setting data types, and extracting nested fields.

    Args:
        data (pd.DataFrame): The raw TAF data DataFrame.

    Returns:
        pd.DataFrame: The normalized DataFrame with updated schema.
    """
    # Drop unused columns
    data = data.drop(['form', 'raw_text'], axis=1)

    # Data types
    data['station_id'] = data.station_id.astype('string[pyarrow]')
    data['change_indicator'] = data.change_indicator.astype('string[pyarrow]')
    data['wx_string'] = data.wx_string.astype('string[pyarrow]')

    data['issue_time'] = data.issue_time.dt.tz_localize(pytz.utc).dt.as_unit('s')
    data['valid_time_from'] = data.valid_time_from.dt.tz_localize(pytz.utc).dt.as_unit('s')
    data['valid_time_to'] = data.valid_time_to.dt.tz_localize(pytz.utc).dt.as_unit('s')
    data['time_from'] = data.time_from.dt.tz_localize(pytz.utc).dt.as_unit('s')
    data['time_to'] = data.time_to.dt.tz_localize(pytz.utc).dt.as_unit('s')

    data['probability'] = data.probability.astype('int32[pyarrow]')
    data['wind_dir_degrees'] = data.wind_dir_degrees.astype('int32[pyarrow]')
    data['wind_speed_kt'] = data.wind_speed_kt.astype('int32[pyarrow]')
    data['wing_gust_kt'] = data.wing_gust_kt.astype('int32[pyarrow]')
    data['wind_shear_hgt_ft_agl'] = data.wind_shear_hgt_ft_agl.astype('int32[pyarrow]')
    data['wind_shear_dir_degrees'] = data.wind_shear_dir_degrees.astype('int32[pyarrow]')
    data['wind_shear_speed_kt'] = data.wind_shear_speed_kt.astype('int32[pyarrow]')
    data['vert_vis_ft'] = data.vert_vis_ft.astype('int32[pyarrow]')

    data['altim_in_hg'] = data.altim_in_hg.astype('float32[pyarrow]')
    data['visibility_statute_mi'] = data.visibility_statute_mi.astype('float32[pyarrow]')

    # Add columns
    # Temperature
    temperatures = list(map(_extract_temps, data.temperature.tolist()))
    temp_columns = ['max_temp','max_temp_timestamp','min_temp','min_temp_timestamp']
    temperatures = pd.DataFrame(temperatures, columns=temp_columns)
    data[['max_temp','max_temp_timestamp','min_temp','min_temp_timestamp']] = temperatures.to_numpy()
    data['max_temp'] = data.max_temp.astype('int32[pyarrow]')
    data['min_temp'] = data.min_temp.astype('int32[pyarrow]')

    # Sky condition
    sky_conditions = list(map(_extract_sky_conditions, data.sky_condition.tolist()))
    sky_cond_columns = ['sky_cover','cloud_base_ft_agl','cloud_type']
    sky_conditions = pd.DataFrame(sky_conditions, columns=sky_cond_columns)
    data[['sky_cover','cloud_base_ft_agl','cloud_type']] = sky_conditions.to_numpy()
    data['sky_cover'] = data.sky_cover.astype('string[pyarrow]')
    data['cloud_type'] = data.cloud_type.astype('string[pyarrow]')

    # Icing condition
    # Almost always empty

    return data

def taf_forecast_clean(data: pd.DataFrame) -> pd.DataFrame:
    """Cleans the TAF forecast data by fixing column values and handling NA values.

    Args:
        data (pd.DataFrame): The normalized TAF data DataFrame.

    Returns:
        pd.DataFrame: The cleaned DataFrame.
    """
    # Fix column values
    data['wind_dir_degrees'] = data.wind_dir_degrees.astype('float') % 360
    # Si valid_time_from es nulo, asignamos issue_time + 1h
    data['valid_time_from'] = data.valid_time_from.combine_first(data.issue_time+datetime.timedelta(hours=1))
    # Si valid_time_to es nulo, asignamos valid_time_from + 30h
    data['valid_time_to'] = data.valid_time_from.combine_first(data.issue_time+datetime.timedelta(hours=30))

    # Fix NA values
    for col in ['sky_condition','turbulence_condition','icing_condition','temperature']:
        data[col] = data[col].apply(lambda x: x if len(x)>0 else pd.NA)

    # Add columns
    data['date'] = data.issue_time.dt.date.astype('string[pyarrow]')
    # data['report_id'] = data.station_id + '-' + data.issue_time.dt.total_seconds()

    return data

