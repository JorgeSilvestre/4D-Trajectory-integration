from .data_cleaning import surveillance, flight_plans, weather
from .data_cleaning import additional as clean_additional
from .data_extraction import additional as extract_additional
from .quality_metrics import individual_metrics, trajectory_metrics
from .data_integration import integrate_nm_vectors
import time
from .trajectory import Trajectory
from .trajectory_processing.sort_trajectory import process_trajectory, process_trajectories
from . import params

def run():
    # date_start, date_end = '2023-07-01','2023-07-16'
    # dates = utils.get_dates_between(date_start, date_end)
    # dates = [x.strftime('%Y-%m-%d') for x in dates]
    # for date in dates:
    #     print(date)

    date = '2023-07-03'
    month = '2023-07'




    # Integration process
    if True:
        # L1
        # extract_additional.extract_airports_ourAirports()
        # clean_additional.ourairports_airports_process()

        # individual_metrics.calculate_metrics_openskyVectors(date, state='raw')
        # surveillance.opensky_vectors_process(date)
        # individual_metrics.calculate_metrics_openskyVectors(date, state='clean')

        # individual_metrics.calculate_metrics_taf(month, 'raw')
        # weather.taf_clean_parquet(month)
        # individual_metrics.calculate_metrics_taf(month, 'clean')

        # individual_metrics.calculate_metrics_fplan(date, 'raw')
        # flight_plans.nm_fplan_process(date)
        # individual_metrics.calculate_metrics_fplan(date, 'clean')
        # individual_metrics.calculate_metrics_fdata(date, 'raw')
        # flight_plans.nm_fdata_process(date)
        # individual_metrics.calculate_metrics_fdata(date, 'clean')

        # L2
        airport_orig = ['EHAM', 'EDDF', 'LIRF', 'LFPG', 'LGAV', 'EKCH', 'EGLL', 'LEMD']
        airport_dest = ['EHAM', 'EDDF', 'LIRF', 'LFPG', 'LGAV', 'EKCH', 'EGLL', 'LEMD']

        # integrate_nm_vectors.nm_merge_fp_fd(date)
        integrate_nm_vectors.nm_integrate_flight_vectors(date, airport_orig, airport_dest)
        # trajectory_metrics.calculate_metrics_trajectories(date, 'raw')

        # L3
        # process_trajectories(date)
        # trajectory_metrics.calculate_metrics_trajectories(date, 'clean')
        pass

    # Sort trajectory
    if False:
        # AT02603204
        tray = Trajectory('AT02603928', '2023-07-03', 'raw')
        res = process_trajectory(tray, 'complete', params.SORT_ALG, False, {}, False, False)
        pass

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
