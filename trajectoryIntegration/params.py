from .trajectory_processing.sorting_algorithms import (
    nearest_neighbours,
    opt2,
    opt2_progressive,
    opt2_restricted,
)

# THRESHOLDS AND CONSTANTS -------------------------------------------------------------------------

# L1 - FLIGHT PLANS TIMEZONE ADJUSTMENT

TIMEZONE_DISPLACEMENT_SECONDS = 0

# L2 - INTEGRATION PARAMETERS

# Integration parameters
TIME_EXPANSION = 10*60 # Seconds
MIN_VECTOR_NUMBER = 200

# L2/L3 - TRAJECTORY PARAMETERS

# Trajectory metrics parameters
THRESHOLD_DISTANCE_TO_AIRPORT = 50
THRESHOLD_GAP_TIME = 300
THRESHOLD_CONTINUITY = 30

# Trajectory sorting thresholds
TMA_AREA_MAX = 100
TMA_AREA_MIN = 30
AIRPORT_AREA = 15

HOLDING_ROTATION = 365
LOOP_ROTATION = 180
MIN_OSCILLATION = 10

# Trajectory outliers thresholds
DIFF_SPEED_THRESHOLD = 0.5 # Km per second
DIFF_VSPEED_THRESHOLD = 125  # Feet per second
DIFF_ALTITUDE_THRESHOLD = 250  # Feet
ALTITUDE_CHECK_WINDOW_SIZE = 7

# SORTING CONFIGURATION ----------------------------------------------------------------------------

# Trajectory sorting configurations
HOW_SORT = 'complete' # 'segmented'
DETECT_LOOP = True
SORT_ALG = {
    'complete': {
        'algorithm': opt2_restricted,
        'options': {
            'n_closest': 10,
            'window_size': 100,
            'overlap': 20,
            'distance_function': 'haversine',
        },
    },
    'out': {
        'algorithm': opt2,
        'options': {
            'distance_function': 'haversine',
        },
    },
    'cruise': {
        'algorithm': nearest_neighbours,
        'options': {
            'distance_function': 'haversine',
        },
    },
    'in': {
        'algorithm': opt2,
        'options': {
            'distance_function': 'haversine',
        },
    },
    'loop': {
        'algorithm': opt2_progressive,
        'options': {
            'distance_function': 'haversine',
            'window_size': 30,
            'overlap': 10,
        },
    },
}
PRESORT = True
PRESORT_ALG = {
    'complete': {
        'algorithm': nearest_neighbours,
        'options': {
            'distance_function': 'haversine',
        },
    },
    'out': {
        'algorithm': opt2_progressive,
        'options': {
            'n_closest': 10,
            'window_size': 100,
            'overlap': 20,
            'distance_function': 'haversine',
        },
    },
    'cruise': {
        'algorithm': nearest_neighbours,
        'options': {
            'distance_function': 'haversine',
        },
    },
    'in': {},
}
_all_options = {
    'n_closest': 10,
    'window_size': 100,
    'overlap': 20,
    'distance_function': 'haversine',
}

