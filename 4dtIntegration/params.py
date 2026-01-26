# SCHEMA -------------------------------------------------------------------------------------------

# L0 - Name mappings

# OpenSky vectors

mapping_opensky = {
    'hexid'               :'icao24',
    'time_stamp'          :'time_position',
    'time_stamp_velocity' :'last_contact',
    'track'               :'true_track',
    'altitude'            :'geo_altitude',
    'ground_speed'        :'velocity',
}

# Network Manager
mapping_flightPlan = {
    'ifplId'                    :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.ifplId',
    'timestamp'                 :'ps:FlightPlanMessage.timestamp',
    'callsign'                  :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.aircraftId',
    'icao24'                    :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.aircraftAddress',
    'aerodromeOfDeparture'      :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aerodromeOfDeparture.icaoId',
    'aerodromeOfDestination'    :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aerodromesOfDestination.aerodromeOfDestination.icaoId',
    'estimatedOffBlockTime'     :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.estimatedOffBlockTime',
    'operator'                  :'ps:FlightPlanMessage.flightPlanData.structured.aircraftOperator',
    'operatingOperator'         :'ps:FlightPlanMessage.flightPlanData.structured.operatingAircraftOperator',
    'registrationMark'          :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.registrationMark',
    'ssr'                       :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftId.ssrInfo.code',
    'flightRules'               :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.flightRules',
    'flightType'                :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.flightType',
    'aircraftType'              :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.aircraftType.icaoId',
    'totalEstimatedElapsedTime' :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.totalEstimatedElapsedTime',
    'wakeTurbulenceCategory'    :'ps:FlightPlanMessage.flightPlanData.structured.flightPlan.wakeTurbulenceCategory',
    'uuid'                      :'ps:FlightPlanMessage.uuid',
}

mapping_flightData = {
    'ifplId'                  :'ps:FlightDataMessage.flightData.flightId.id',
    'timestamp'               :'ps:FlightDataMessage.timestamp',
    'callsign'                :'ps:FlightDataMessage.flightData.flightId.keys.aircraftId',
    'icao24'                  :'ps:FlightDataMessage.flightData.aircraftAddress',
    'aerodromeOfDeparture'    :'ps:FlightDataMessage.flightData.flightId.keys.aerodromeOfDeparture',
    'aerodromeOfDestination'  :'ps:FlightDataMessage.flightData.flightId.keys.aerodromeOfDestination',
    'estimatedOffBlockTime'   :'ps:FlightDataMessage.flightData.flightId.keys.estimatedOffBlockTime',
    'operator'                :'ps:FlightDataMessage.flightData.aircraftOperator',
    'operatingOperator'       :'ps:FlightDataMessage.flightData.operatingAircraftOperator',
    'estimatedTakeOffTime'    :'ps:FlightDataMessage.flightData.estimatedTakeOffTime',
    'estimatedTimeOfArrival'  :'ps:FlightDataMessage.flightData.estimatedTimeOfArrival',
    'actualOffBlockTime'      :'ps:FlightDataMessage.flightData.actualOffBlockTime',
    'actualTakeOffTime'       :'ps:FlightDataMessage.flightData.actualTakeOffTime',
    'actualTimeOfArrival'     :'ps:FlightDataMessage.flightData.actualTimeOfArrival',
    'calculatedTakeOffTime'   :'ps:FlightDataMessage.flightData.calculatedTakeOffTime',
    'calculatedTimeOfArrival' :'ps:FlightDataMessage.flightData.calculatedTimeOfArrival',
    'flightState'             :'ps:FlightDataMessage.flightData.flightState',
    'flightDataVersionNr'     :'ps:FlightDataMessage.flightData.flightDataVersionNr',
    'aircraftType'            :'ps:FlightDataMessage.flightData.aircraftType',
    'routeLength'             :'ps:FlightDataMessage.flightData.routeLength',
    'uuid'                    :'ps:FlightDataMessage.uuid',
}

# L1 - Column order
vector_attribute_names = [
    'timestamp',
    'icao24',
    'callsign',
    'time_position',
    'last_contact',
    'latitude',
    'longitude',
    'altitude',
    'baro_altitude',
    'geo_altitude',
    'velocity',
    'vertical_rate',
    'true_track',
    'on_ground',
    'squawk'
]
# Removed attributes: 'spi','sensors','position_source','origin_country'

flight_attribute_names = [
    'ifplId', 'icao24', 'callsign',
    'estimatedOffBlockTime', 'aerodromeOfDeparture',
    'aerodromeOfDestination', 'operator', 'operatingOperator',
    'flightState',
    'estimatedTakeOffTime', 'estimatedTimeOfArrival', 'actualTakeOffTime',
    'actualTimeOfArrival',
    'calculatedTakeOffTime',
    'calculatedTimeOfArrival',
    'flightType', 'registrationMark', 'ssr',
    'totalEstimatedElapsedTime', 'wakeTurbulenceCategory',
    'aircraftType', 'routeLength', ]

# DATA PROCESSING ----------------------------------------------------------------------------------

from .trajectory_processing.sorting_algorithms import (
    nearest_neighbours,
    opt2,
    opt2_progressive,
    opt2_restricted) 

# L1 - FLIGHT PLANS TIMEZONE ADJUSTMENT

TIMEZONE_DISPL = 0

# L2 - INTEGRATION PARAMETERS

# Integration parameters
TIME_SLACK = 10*60 # Seconds
VECTOR_NUMBER_MIN = 200

# L2/L3 - TRAJECTORY PARAMETERS

# Trajectory metrics parameters
THRESHOLD_DISTANCE_TO_AIRPORT = 50
THRESHOLD_GAP_TIME = 300
THRESHOLD_CONTINUITY = 30

# Trajectory sorting parameters
TMA_AREA_MAX = 100
TMA_AREA_MIN = 30
AIRPORT_AREA = 15

HOLDING_ROTATION = 365
LOOP_ROTATION = 180
MIN_OSCILLATION = 10

HOW_SORT = 'complete' # 'segmented'
PRESORT = True
PRESORT_ALG = {
    'complete': {
        'algorithm': nearest_neighbours,
        'options': {}
    }
}
SORT_ALG = {
    'complete': {
        'algorithm': opt2_progressive,
        'options': { 
            'n_closest' : 10,
            'window_size' : 100,
            'overlap' : 20,
            'distance_function' : 'haversine',
        },
    },
    'out': {
        'algorithm': opt2,
        'options': { 
            'distance_function' : 'haversine',
        },
    },
    'cruise': {
        'algorithm': nearest_neighbours,
        'options': { 
            'distance_function' : 'haversine',
        },
    },
    'in': {
        'algorithm': opt2,
        'options': { 
            'distance_function' : 'haversine',
        },
    },
}
# Trajectory outliers parameters
DIFF_SPEED_THRESHOLD = 0.5 # Km per second
DIFF_ALTITUDE_THRESHOLD = 125  # Feet per second
ALTITUDE_CHECK_WINDOW_SIZE = 11