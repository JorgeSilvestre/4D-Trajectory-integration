from pathlib import Path

# Package directory
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
# Base directories
DATA_DIR = PROJECT_ROOT / 'data'
REPORTS_DIR = PROJECT_ROOT / 'reports'

# DATA ---------------------------------------------------------------------------------------------

# L0 - RAW
NM_JSON_FPLAN_PATH = DATA_DIR / 'L0/nmFPlan'
NM_JSON_FDATA_PATH = DATA_DIR / 'L0/nmFData'
NM_RAW_ADRR_PATH = DATA_DIR / 'L0/nmADRR'
OPENSKY_RAW_FLIGHTS_PATH = DATA_DIR / 'L0/openskyFlights'
OPENSKY_RAW_VECTORS_JSON_PATH = DATA_DIR / 'L0/openskyVectorsJson'
OPENSKY_RAW_VECTORS_PATH = DATA_DIR / 'L0/openskyVectors'
TAF_RAW_PATH = DATA_DIR / 'L0/taf'
AIRPORTS_RAW_PATH = DATA_DIR / 'L0/airports'
RUNWAYS_RAW_PATH = DATA_DIR / 'L0/runways'
AIRLINES_RAW_PATH = DATA_DIR / 'L0/airlines'

# L1 - INDIVIDUAL
NM_PARQUET_FPLAN_PATH = DATA_DIR / 'L1/nmFPlan'
NM_PARQUET_FDATA_PATH = DATA_DIR / 'L1/nmFData'
NM_PARQUET_ADRR_PATH = DATA_DIR / 'L1/nmADRR'
OPENSKY_PARQUET_FLIGHTS_PATH = DATA_DIR / 'L1/openskyFlights'
OPENSKY_PARQUET_VECTORS_PATH = DATA_DIR / 'L1/openskyVectors'
TAF_PARQUET_PATH = DATA_DIR / 'L1/taf'
AIRPORTS_PATH = DATA_DIR / 'L1/airports'

# L2 - INTEGRATED
NM_PARQUET_FLIGHTS_PATH = DATA_DIR / 'L2/nmFlights'
NM_TRAJECTORIES_RAW_PATH = DATA_DIR / 'L2/nmTrajectories'
TAF_INTEGRATED_PATH = DATA_DIR / 'L2/taf'
# No se usan: se guardan directamente las trayectorias
OPENSKY_JOINED_VECTORS_PATH = DATA_DIR / 'L2/openskyVectorsJoined'
OPENSKY_JOINED_FLIGHTS_PATH = DATA_DIR / 'L2/openskyFlightsJoined'
NM_JOINED_VECTORS_PATH = DATA_DIR / 'L2/nmVectorsJoined'
NM_JOINED_FLIGHTS_PATH = DATA_DIR / 'L2/nmFlightsJoined'

# L3 - CLEAN TRAJECTORIES
NM_TRAJECTORIES_PATH = DATA_DIR / 'L3/nmTrajectories'

# METRICS ------------------------------------------------------------------------------------------

NM_FPLAN_METRICS_L0_PATH = REPORTS_DIR / 'L0_fplan'
NM_FDATA_METRICS_L0_PATH = REPORTS_DIR / 'L0_fdata'
OPENSKY_VECTORS_METRICS_L0_PATH = REPORTS_DIR / 'L0_vectors'
TAF_METRICS_L0_PATH = REPORTS_DIR / 'L0_taf'

NM_FPLAN_METRICS_L1_PATH = REPORTS_DIR / 'L1_fplan'
NM_FDATA_METRICS_L1_PATH = REPORTS_DIR / 'L1_fdata'
OPENSKY_VECTORS_METRICS_L1_PATH = REPORTS_DIR / 'L1_vectors'
TAF_METRICS_L1_PATH = REPORTS_DIR / 'L1_taf'

NM_TRAYS_METRICS_L2_PATH = REPORTS_DIR / 'L2_trajectories'
NM_TRAYS_METRICS_L3_PATH = REPORTS_DIR / 'L3_trajectories'
INTEGRATION_METRICS_PATH = REPORTS_DIR / 'L2_integration_metrics'
SORT_TRAJECTORIES_METRICS_PATH = REPORTS_DIR / 'L3_sort_metrics'

def ensure_dir_exists(dir: Path) -> None:
    """Check the existence of a folder, and create it otherwise. 
    
    Args:
        dir (pathlib.Path): The complete path to the directory. """
    
    if not dir.exists():
        dir.mkdir(parents=True)