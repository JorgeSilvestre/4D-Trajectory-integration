import time, datetime

from . import params
from .data_cleaning import additional as clean_additional
from .data_cleaning import flight_plans, surveillance, weather
from .data_extraction import additional as extract_additional
from .data_integration import integrate_nm_vectors, integrate_taf
from .quality_metrics import individual_metrics, trajectory_metrics
from .trajectory import Trajectory
from .trajectory_processing.sort_trajectory import (process_trajectories,
                                                    process_trajectory)
from .utils import get_dates_between


def run():

    date = '2023-06-03'
    month = '2023-07'

    # Integration process
    date_start, date_end = '2023-07-03','2023-07-05'
    dates = get_dates_between(date_start, date_end)
    dates = [x.strftime('%Y-%m-%d') for x in dates]

    # for date in dates:
        # pass
    if True:
        print(date)
        airport_orig = ['EHAM', 'EDDF', 'LIRF', 'LFPG', 'LGAV', 'EKCH', 'EGLL', 'LEMD']
        airport_dest = ['EHAM', 'EDDF', 'LIRF', 'LFPG', 'LGAV', 'EKCH', 'EGLL', 'LEMD']

        # L1
        # clean_additional.ourairports_airports_process()
        flight_plans.adrr_flights_process(date)

        # individual_metrics.calculate_metrics_openskyVectors(date, state='raw')
        # surveillance.opensky_vectors_process(date)
        # individual_metrics.calculate_metrics_openskyVectors(date, state='clean')

        # individual_metrics.calculate_metrics_taf(month, 'raw')
        # weather.taf_forecast_process(month)
        # individual_metrics.calculate_metrics_taf(month, 'clean')

        # individual_metrics.calculate_metrics_fplan(date, 'raw')
        # individual_metrics.calculate_metrics_fdata(date, 'raw')
        # flight_plans.nm_fplan_process(date)
        # flight_plans.nm_fdata_process(date)
        # individual_metrics.calculate_metrics_fplan(date, 'clean')
        # individual_metrics.calculate_metrics_fdata(date, 'clean')


        # L2

        # integrate_nm_vectors.nm_merge_fplan_fdata(date)
        # integrate_nm_vectors.nm_integrate_flight_vectors(date, airport_orig, airport_dest)
        integrate_nm_vectors.adrr_integrate_flight_vectors(date)
        # trajectory_metrics.calculate_metrics_trajectories(date, 'raw')

        # integrate_taf.taf_current_report(month, set(airport_orig + airport_dest))

        # L3
        # process_trajectories(date)
        # trajectory_metrics.calculate_metrics_trajectories(date, 'clean')
        # integrate_taf.taf_integrate_vectors(date)
        pass

    # Sort trajectory
    if False:
        # AT02603204
        tray = Trajectory('AT02603928', '2023-07-03', 'raw')
        print(tray.get_attr_list())
        # res = process_trajectory(tray, 'complete', params.SORT_ALG, False, {}, True, False)

    # Time benchmark
    if False:
        # t0 = time.time()
        # integrate_nm_vectors.nm_merge_fp_fd(date)
        # t1 = time.time()
        # integrate_nm_vectors.nm_integrate_flight_vectors(date, airport_orig, airport_dest)
        # t2 = time.time()
        # trajectory_metrics.calculate_metrics_trajectories(date, 'raw')
        # t3 = time.time()
        # print()
        # print(t1-t0)
        # print(t2-t1)
        # print(t3-t2)
        pass
