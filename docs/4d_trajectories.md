# Enriched 4D trajectory

A traditional 4D trajectory represents the time-ordered sequence of aircraft positions during a flight, where each spatial state is associated with a timestamp. In this project, an Enriched 4D Trajectory is defined as a structured data container that integrates all available information related to a real flight into a unified and processable representation.

It combines:

- Surveillance-derived state vectors
- Flight planning information
- Operational metadata
- Derived descriptive attributes
- (Optionally) contextual data such as weather

## Role of enriched 4D trajectories in this project

The Enriched 4D Trajectory is produced after the integration stage of the pipeline:

```
L0  Raw sources (Surveillance, Flight Plan, Weather)
        |
        | L0 → L1 Standardization and cleaning
        ↓
L1 Clean data (Surveillance, Flight Plan, Weather)
        |
        | L1 → L2 Data integration
        ↓
L2  Trajectory (state: raw)
        |
        | L2 → L3 Trajectory cleaning
        ↓
L3  Trajectory (state: clean)
```

Each trajectory may exist in different processing states (e.g., raw, cleaned), reflecting its maturity level within the pipeline.

## Data Model

The enriched trajectory is structured at two levels:

- Static attributes
- Time-dependent attributes

### Static Attributes

Static attributes contain flight-level information that remains constant throughout the flight.

#### Identification

- NM flight identifier (IFPL ID)
- Aircraft ICAO24 / hex identifier
- Callsign
- Flight date

#### Planning Information

- Airline
- Origin and destination airports
- Scheduled and actual timestamps for:
    - Off-block
    - Takeoff
    - Landing

#### Derived Flight Descriptors

- Attributes computed during integration and quality assessment:
- Flight state (typically `TERMINATED`)
- Number of state vectors
- Total flown distance
- Flags indicating:
    - Missing initial segment
    - Missing final segment
    - Presence of loops or holdings
- Maximum rotation in destination TMA (used for loop detection)
- Trajectory temporal span (first and last state vector timestamps)

#### Data Provenance and Processing Metadata

- Surveillance data source
- Flight plan data source
- Trajectory maturity level
- Processing state

### Time-Dependent Attributes

Time-dependent attributes are represented as one or more time series. Each data point is associated with a timestamp, but different time series may follow different temporal domains.

#### State Vectors (Surveillance Temporal Domain)

Currently, all time-dependent flight state information originates from OpenSky and shares a common temporal axis. Each state vector contains:

- 3D Position:
    - Latitude
    - Longitude
    - Geometric altitude
    - Barometric altitude
- Instantaneous Aircraft State:
    - Ground speed
    - Vertical rate
    - True track / heading
    - On-ground flag

#### Additional Temporal Domains

Additional time-dependent data may follow independent temporal evolution, such as:

- Flight plan version updates
- Evolution of flight state (flightState)
- Estimated Time of Arrival (estimatedTimeOfArrival)
- Significant flight plan waypoints

#### Meteorological Data

Currently, meteorological information corresponds to forecast conditions at the destination airport. Its temporal evolution follows:

- Forecast validity periods
- Publication/update times


## The Trajectory class

The Trajectory class abstracts access to all data associated with a given flight and provides a unified interface across pipeline stages.

```python
class Trajectory():
    def __init__(self, trajectory_id: str, date: str | Date, trajectory_state: str):
        ...
```

Example:

```python
tray = Trajectory('AT02603204', '2023-07-03', 'raw')
```

This instantiates trajectory `AT02603204` for `2023-07-03` in its `raw` state, meaning after integration but before quality resolution.

Attributes are accessible via dot notation:

```python
tray.ifplId
# "AT02603204"
tray.loop
# True
tray.state_vectors
# <pd.DataFrame columns=["ifplId", "flightDate", ...]>
```

Thus, the class acts as:

- A data loader
- A structured container
- A state-aware abstraction layer
- A bridge between data engineering and machine learning workflow.