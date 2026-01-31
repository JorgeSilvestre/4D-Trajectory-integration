import datetime

import pandas as pd

from .. import paths

def _extract_temps(temp_records):
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

def _extract_sky_conditions(sky_record):
        if len(sky_record)==0:
            return [pd.NA]*3
        elif len(sky_record)>0:
            return [
                sky_record[0]['sky_cover'],
                sky_record[0]['cloud_base_ft_agl'],
                sky_record[0]['cloud_type'] if sky_record[0]['cloud_type'] else pd.NA
            ]

def taf_change_schema(data: pd.DataFrame)  -> pd.DataFrame:
    # Drop unused columns
    data = data.drop(['form', 'raw_text'], axis=1)

    # Data types
    data['station_id'] = data.station_id.astype('string[pyarrow]')
    data['change_indicator'] = data.change_indicator.astype('string[pyarrow]')
    data['wx_string'] = data.wx_string.astype('string[pyarrow]')

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
    temperatures = list(map(_extract_temps, data.temperature.values.tolist()))
    temperatures = pd.DataFrame(temperatures, columns=['max_temp','max_temp_timestamp','min_temp','min_temp_timestamp'])
    data[['max_temp','max_temp_timestamp','min_temp','min_temp_timestamp']] = temperatures.values
    data[['max_temp','min_temp']] = data[['max_temp','min_temp']].astype('int32[pyarrow]')

    # Sky condition
    sky_conditions = list(map(_extract_sky_conditions, data.sky_condition.values.tolist()))
    sky_conditions = pd.DataFrame(sky_conditions, columns=['sky_cover','cloud_base_ft_agl','cloud_type'])
    data[['sky_cover','cloud_base_ft_agl','cloud_type']] = sky_conditions.values
    data[['sky_cover','cloud_type']] = data[['sky_cover','cloud_type']].astype('string[pyarrow]')

    # Icing condition
    # Almost always empty, it is not worth

    return data

def taf_clean_parquet(month: str) -> None:
    """Parse TAF weather data (decoded) from a parquet file and write into a parquet file

    Args:
        month: String with a month in format 'YYYY-MM'
    """

    folder = paths.TAF_RAW_PATH / f'month={month}'
    data = pd.read_parquet(folder, engine='pyarrow', dtype_backend='pyarrow')

    data = taf_change_schema(data)

    # Fix column values
    data['wind_dir_degrees'] = data.wind_dir_degrees.astype('float') % 360
    # Si valid_time_from es nulo, asignamos issue_time + 1h
    data['valid_time_from'] = data.valid_time_from.combine_first(data.issue_time+datetime.timedelta(hours=1))
    # Si valid_time_to es nulo, asignamos valid_time_from + 30h
    data['valid_time_to'] = data.valid_time_from.combine_first(data.issue_time+datetime.timedelta(hours=30))

    # Fix NA values
    for col in ['sky_condition','turbulence_condition','icing_condition','temperature']:
        data[col] = data[col].apply(lambda x: x if len(x)>0 else pd.NA)

    output_folder = paths.TAF_PARQUET_PATH
    if not output_folder.exists():
        output_folder.mkdir(parents=True)
    output_file = output_folder / f'taf.{month}.parquet'
    data.to_parquet(output_file, index=False)

def taf_current_report(month: str):
    weather_data = ['wind_dir_degrees', 'wind_speed_kt', 'wing_gust_kt', 'wind_shear_hgt_ft_agl',
                'wind_shear_dir_degrees', 'wind_shear_speed_kt', 'visibility_statute_mi',
                'altim_in_hg', 'vert_vis_ft', 'wx_string', 'sky_condition',
                'turbulence_condition', 'icing_condition', 'temperature',
                'sky_cover','cloud_base_ft_agl','cloud_type','max_temp','min_temp',
                'max_temp_timestamp','min_temp_timestamp']

    folder = paths.TAF_PARQUET_PATH / f'taf.{month}.parquet'
    data = pd.read_parquet(folder, engine='pyarrow', dtype_backend='pyarrow',
                        #    filters=[('station_id', '=', 'LEMD')]
                           )

    # La situación "base" se define con los informes que dan una descripción detallada: base, AMD o COR
    bases = data[data.change_indicator.isna() | data.change_indicator.isin(['AMD', 'COR'])].sort_values('issue_time')

    # Sobreescritura de COR
    bases = bases.groupby(['station_id', 'valid_time_to']).agg({x:'last' for x in weather_data})

    # BECMG describe un cambio permanente en alguno de los factores del informe. Sobreescribe, con los campos informados,
    # los homólogos en la situación base a partir de su comienzo de validez
    stable = pd.concat([bases, data[data.change_indicator=='BECMG']]).sort_values(
        ['issue_time','valid_time_from','time_from', 'time_to'],
        na_position='first')

    stable = stable.groupby(['station_id', 'issue_time']).agg({x:'last' for x in weather_data})

    # TEMPO describe un cambio temporal en alguno de los factores del informe.Sobreescribe, con los campos informados,
    # los homólogos en la situación base a partir de su comienzo de validez y hasta su final de validez
    tempo = pd.concat([stable, data[data.change_indicator=='TEMPO']]).sort_values(
        ['issue_time','valid_time_from','time_from', 'time_to'],
        na_position='first')

    tempo = tempo.groupby(['station_id', 'issue_time']).agg({x:'last' for x in weather_data})

    data = tempo.drop_duplicates()


    return bases