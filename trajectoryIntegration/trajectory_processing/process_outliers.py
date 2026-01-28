import pandas as pd

from .. import params, paths
from ..trajectory import Trajectory
from ..utils import haversine_np, haversine_np_track

airports = pd.read_parquet(paths.AIRPORTS_PATH)

def outliers_median_filter(data: pd.Series, window, thresh) -> pd.Series:
    filled_sequence = data.interpolate(method='slinear', limit_area='inside')
    median_values = data.rolling(window, min_periods=5, center=True, closed='both').median()
    result = (filled_sequence - median_values).abs() > thresh

    return result.fillna(False)
    return data.where(result, median_values) # Where result, replace with median_values

def outliers_zscore(data: pd.Series, window, thresh=3) -> pd.Series:
    roll = data.rolling(window=window, min_periods=1, center=True)
    avg = roll.mean()
    std = roll.std(ddof=0)
    z = data.sub(avg).div(std)   
    m = z.between(-thresh, thresh)

    return m
    return data.where(m, avg) # Where m, replace with avg

def fix_altitude(trajectory: Trajectory):
    data = trajectory.vectors.copy()
    data['original_altitude'] = data.altitude.copy()

    # TODO: Esta operación debería hacerse sobre segmentos individuales evitando los gaps, 
    # para evitar valores raros en los extremos
    
    incorrect_altitude = (
        (data.altitude.isna() | 
        outliers_median_filter(data.altitude, params.ALTITUDE_CHECK_WINDOW_SIZE, params.DIFF_ALTITUDE_THRESHOLD)) &
        ~data.on_ground
    )
    interp_values = data.set_index('timestamp').altitude.copy()
    interp_values[incorrect_altitude.to_numpy()] = pd.NA
    interp_values = interp_values.interpolate(method='index', limit = 5, limit_area='inside').reset_index(drop=True)
    
    data['altitude'] = interp_values
    data['incorrect_altitude'] = incorrect_altitude

    trajectory.vectors = data
    return trajectory


def fix_altitude2(trajectory: Trajectory) -> pd.DataFrame:
    df = trajectory.vectors.copy()

    origin_airport = airports[airports.icao == trajectory.aerodromeOfDeparture].iloc[0]
    destination_airport = airports[airports.icao == trajectory.aerodromeOfDestination].iloc[0]

    # Fill ground vectors with airport's altitude
    df.loc[(df.distance_org<params.TMA_AREA_MIN)&(df.on_ground),'altitude'] = origin_airport.altitude
    df.loc[(df.distance_dst<params.TMA_AREA_MIN)&(df.on_ground),'altitude'] = destination_airport.altitude

    def calculate_altitudes(data: pd.DataFrame):
        if len(data)<5:
            data['original_altitude'] = data.altitude.copy()
            return data

        data['incorrect_altitude'] = data.altitude.isna()
        data['filtered_altitude'] = data.altitude.interpolate(method='slinear', limit_area='inside')
        # try:
        #     data['filtered_altitude'] = data.altitude.interpolate(method='slinear', limit_area='inside')
        # except ValueError:
        #     print(data.ifplId)
        #     exit()

        # data['filtered_altitude'] = data.altitude.interpolate(method='polynomial', limit_area='inside', order=5)
        data['median_value'] = (data.filtered_altitude
                                    .rolling(params.ALTITUDE_CHECK_WINDOW_SIZE, min_periods=3, center=True, closed='both')
                                    .median()
                                ).to_numpy()
        data['incorrect_altitude'] = (data.incorrect_altitude | 
                                      (abs(data.filtered_altitude - data.median_value) > params.DIFF_ALTITUDE_THRESHOLD))
        
        try:
            data.loc[[data.index[0], data.index[-1]], 'incorrect_altitude'] = False
        except IndexError:
            print(f'Error al procesar la altitud en {trajectory.ifplId}: {data.shape}')
            return None
        data['filtered_altitude'] = data[~data.incorrect_altitude].filtered_altitude

        # df['interpolated_altitude'] = df['filtered_altitude'].interpolate(method='linear', limit = 3, limit_area='inside')
        data['interpolated_altitude'] = (data.set_index('timestamp')['filtered_altitude']
                                             .interpolate(method='index', limit = 7, limit_area='inside')
                                             .to_numpy()) # .reset_index(drop=True)
        data['original_altitude'] = data['altitude'].copy()
        # data['altitude'] = data.filtered_altitude.combine_first(data.interpolated_altitude)
        data['altitude'] = data.interpolated_altitude
        data = data.drop(['incorrect_altitude', 'filtered_altitude', 'median_value', 'interpolated_altitude'], axis=1)
        
        return data
    
    latest = 0
    results = []
    # Gaps
    diffs = df.timestamp.iloc[1:].values - df.timestamp.iloc[:-1].values
    gaps = [dict(index=i, size=d) for i, d in enumerate(diffs) if d>60]
    for g in gaps:
        data = df.iloc[latest:g['index']+1].copy()
        latest = g['index']+1

        results.append(calculate_altitudes(data))
    else:
        data = df.iloc[latest:].copy()        
        results.append(calculate_altitudes(data))

    df = pd.concat(results)
    trajectory.vectors = df

    return df

# ONLY ON CONTINUOUS SEGMENTS??
def detect_outliers(trajectory: Trajectory) -> Trajectory:
    data = trajectory.vectors.copy()
    # The first vector is assumed to be correct
    first = data.iloc[0]
    latest = (first.latitude, first.longitude, first.timestamp, first.altitude, first.vspeed)
    flags = [False]

    for idx, row in list(data.iterrows())[1:]:
        # Time check
        diff_time = row.timestamp - latest[2]
        if diff_time == 0:
            flags.append(True)
            continue
        if diff_time > 60:
            flags.append(False)
            latest = (row.latitude, row.longitude, row.timestamp, row.altitude, row.vspeed)
            continue

        # Altitude check
        diff_altitude = abs(latest[3] - row.altitude) / diff_time
        exceeds_altitude = (diff_altitude > ((abs(latest[4]) + abs(row.vspeed)) / 120 + params.DIFF_ALTITUDE_THRESHOLD))
        if exceeds_altitude:
            flags.append(True)
            continue

        # Position check
        diff = haversine_np(float(row.latitude), float(row.longitude),
                            latest[0], latest[1]) / (row.timestamp - latest[2])
        exceeds_position = diff > params.DIFF_SPEED_THRESHOLD
        if exceeds_position:
            flags.append(True)
            continue

        latest = (row.latitude, row.longitude, row.timestamp, row.altitude, row.vspeed)
        flags.append(False)

    if suma := sum(flags):
        print(data.iloc[0].fpId, f'{suma:3}/{len(flags):5}/{data.shape[0]:5}')

    data['is_outlier'] = flags

    trajectory.vectors = data

    return trajectory