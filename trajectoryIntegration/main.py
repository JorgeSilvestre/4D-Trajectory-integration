from .data_cleaning import surveillance, flight_plans, weather, additional
from .quality_metrics import individual_metrics, trajectory_metrics
from .data_integration import integrate_nm_vectors
from .trajectory_processing.sort_trajectory import sort_trajectories
import time
from .trajectory import Trajectory
from .trajectory_processing.sort_trajectory import process_trajectory
from . import params

def run():
    # date_start, date_end = '2023-07-01','2023-07-16'
    # dates = utils.get_dates_between(date_start, date_end)
    # dates = [x.strftime('%Y-%m-%d') for x in dates]
    # for date in dates:
    #     print(date)

    date = '2023-07-03'
    month = '2023-07'

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
    
    if False:
        pass
        # L1
        # additional.airports_json_to_parquet()

        # individual_metrics.calculate_metrics_openskyVectors(date, state='raw')
        # surveillance.vectors_clean_parquet(date)
        # individual_metrics.calculate_metrics_openskyVectors(date, state='clean')

        # individual_metrics.calculate_metrics_taf(month, 'raw')
        # weather.taf_clean_parquet(month)
        # individual_metrics.calculate_metrics_taf(month, 'clean')

        # individual_metrics.calculate_metrics_fplan(date, 'raw')
        # flight_plans.nm_fplan_json_to_parquet(date)
        # individual_metrics.calculate_metrics_fplan(date, 'clean')
        # individual_metrics.calculate_metrics_fdata(date, 'raw')
        # flight_plans.nm_fdata_json_to_parquet(date)
        # individual_metrics.calculate_metrics_fdata(date, 'clean')

        # L2
        # airport_orig = ['EHAM', 'EDDF', 'LIRF', 'LFPG', 'LGAV', 'EKCH', 'EGLL', 'LEMD']
        # airport_dest = ['EHAM', 'EDDF', 'LIRF', 'LFPG', 'LGAV', 'EKCH', 'EGLL', 'LEMD']

        # integrate_nm_vectors.nm_merge_fp_fd(date)
        # integrate_nm_vectors.nm_integrate_flight_vectors(date)
        # trajectory_metrics.calculate_metrics_trajectories(date, 'raw')

        # L3
        # sort_trajectories(date)
        # trajectory_metrics.calculate_metrics_trajectories(date, 'clean')
    
    if True:
        # AT02603204
        tray = Trajectory('AT02603928', '2023-07-03', 'raw')
        res = process_trajectory(tray, 'segmented', params.SORT_ALG)
        pass
