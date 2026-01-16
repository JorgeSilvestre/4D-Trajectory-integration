from pathlib import Path

# DATA -------------------------------------------------------------------

# L0 - RAW
NM_JSON_FPLAN_PATH = Path('./data/L0/nmFPlan')
NM_JSON_FDATA_PATH = Path('./data/L0/nmFData')
OPENSKY_RAW_FLIGHTS_PATH = Path('./data/L0/openskyFlights')
OPENSKY_RAW_VECTORS_JSON_PATH = Path('./data/L0/openskyVectorsJson')
OPENSKY_RAW_VECTORS_PATH = Path('./data/L0/openskyVectors')
TAF_RAW_PATH = Path('./data/L0/taf')
AIRPORTS_RAW_PATH = Path('./data/L0/airports/airports.json')

# L1 - INDIVIDUAL
NM_PARQUET_FPLAN_PATH = Path('./data/L1/nmFPlan')
NM_PARQUET_FDATA_PATH = Path('./data/L1/nmFData')
NM_PARQUET_FLIGHTS_PATH = Path('./data/L1/nmFlights')
OPENSKY_PARQUET_FLIGHTS_PATH = Path('./data/L1/openskyFlights')
OPENSKY_PARQUET_VECTORS_PATH = Path('./data/L1/openskyVectors')
TAF_PARQUET_PATH = Path('./data/L1/taf')
AIRPORTS_PATH = Path('./data/L1/airports/airports.parquet')

# L2 - FILTERED
NM_TRAJECTORIES_RAW_PATH = Path('./data/L2/nmTrajectories')
# No se usan: se guardan directamente las trayectorias
OPENSKY_JOINED_VECTORS_PATH = Path('./data/L2/openskyVectorsJoined')
OPENSKY_JOINED_FLIGHTS_PATH = Path('./data/L2/openskyFlightsJoined')
NM_JOINED_VECTORS_PATH = Path('./data/L2/nmVectorsJoined')
NM_JOINED_FLIGHTS_PATH = Path('./data/L2/nmFlightsJoined')

# L3 - CLEAN TRAJECTORIES
NM_TRAJECTORIES_PATH = Path('./data/L3/nmTrajectories')

# METRICS ----------------------------------------------------------------

NM_FPLAN_METRICS_L0_PATH = Path('./reports/L0_fplan')
NM_FDATA_METRICS_L0_PATH = Path('./reports/L0_fdata')
OPENSKY_VECTORS_METRICS_L0_PATH = Path('./reports/L0_vectors')
TAF_METRICS_L0_PATH = Path('./reports/L0_taf')

NM_FPLAN_METRICS_L1_PATH = Path('./reports/L1_fplan')
NM_FDATA_METRICS_L1_PATH = Path('./reports/L1_fdata')
OPENSKY_VECTORS_METRICS_L1_PATH = Path('./reports/L1_vectors')
TAF_METRICS_L1_PATH = Path('./reports/L1_taf')

NM_TRAYS_METRICS_L2_PATH = Path('./reports/L2_trajectories')
NM_TRAYS_METRICS_L3_PATH = Path('./reports/L3_trajectories')

INTEGRATION_METRICS_PATH = Path('./reports/integration_metrics')
SORT_TRAJECTORIES_METRICS_PATH = Path('./reports/sort_metrics')