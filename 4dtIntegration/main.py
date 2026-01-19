from .data_cleaning import surveillance, flight_plans, weather, additional
from .quality_metrics import individual_metrics, trajectory_metrics
from .data_integration import integrate_nm_vectors
from .trajectory_processing.sort_trajectory import sort_trajectories

def run():
    # date_start, date_end = '2023-07-01','2023-07-16'
    # dates = utils.get_dates_between(date_start, date_end)
    # dates = [x.strftime('%Y-%m-%d') for x in dates]
    # for date in dates:
    #     print(date)

    date = '2023-07-01'
    month = '2023-07'

    if False:
        # L1
        additional.airports_json_to_parquet()

        individual_metrics.calculate_metrics_openskyVectors(date, state='raw')
        surveillance.vectors_clean_parquet(date)
        individual_metrics.calculate_metrics_openskyVectors(date, state='clean')

        individual_metrics.calculate_metrics_taf(month, 'raw')
        weather.taf_clean_parquet(month)
        individual_metrics.calculate_metrics_taf(month, 'clean')

        individual_metrics.calculate_metrics_fplan(date, 'raw')
        flight_plans.nm_fplan_json_to_parquet(date)
        individual_metrics.calculate_metrics_fplan(date, 'clean')
        individual_metrics.calculate_metrics_fdata(date, 'raw')
        flight_plans.nm_fdata_json_to_parquet(date)
        individual_metrics.calculate_metrics_fdata(date, 'clean')

        # L2
        airport_orig = ['EHAM', 'EDDF', 'LIRF', 'LFPG', 'LGAV', 'EKCH', 'EGLL', 'LEMD']
        airport_dest = ['EHAM', 'EDDF', 'LIRF', 'LFPG', 'LGAV', 'EKCH', 'EGLL', 'LEMD']

        integrate_nm_vectors.nm_merge_fp_fd(date)
        integrate_nm_vectors.nm_integrate_flight_vectors(date)
        trajectory_metrics.calculate_metrics_trajectories(date, 'raw')

    # L3
    sort_trajectories(date)
    trajectory_metrics.calculate_metrics_trajectories(date, 'clean')
    