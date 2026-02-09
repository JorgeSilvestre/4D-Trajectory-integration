# OpenSky Network

## Data source description

OpenSky Network is an open platform that collects and provides real-time and historical air traffic surveillance data. The data is primarily obtained from a worldwide network of ADS-B (Automatic Dependent Surveillance–Broadcast) receivers operated by volunteers and institutional partners. These receivers capture broadcasts emitted by aircraft, which include positional and kinematic information.

The OpenSky Network provides access to both raw and processed surveillance data through different APIs. In this project, OpenSky constitutes the main source of surveillance information, enabling the reconstruction of 4D aircraft trajectories based on time-stamped state vectors. Additionally, the Flights API is used to retrieve flight-level metadata to support trajectory identification and integration with other data sources, although it would be desestimated due to its data limitations.

The data is provided in structured formats (mainly JSON) and represents aircraft states sampled at irregular time intervals, depending on coverage and reception conditions.

---

## State Vectors

### Access

State vectors are accessed through the OpenSky Network API. Access is publicly available with rate limitations, while authenticated users are granted higher request quotas and extended access to historical data. Queries can be spatially and temporally filtered.

### Data structure

Each state vector corresponds to a single aircraft observation. The main attributes used in this project are summarized below.

| Attribute name  | Data type | Example value | Description                                      |
| --------------- | --------- | ------------- | ------------------------------------------------ |
| `icao24`        | string    | `"3451A2"`    | Unique ICAO 24-bit aircraft address.             |
| `callsign`      | string    |               | Aircraft callsign, if available                  |
| `time_position` | integer   | `1672531200`  | UNIX timestamp of the last known position.       |
| `last_contact`  | integer   |               | Timestamp of the last received ADS-B message     |
| `latitude`      | float     | `40.4719`     | Aircraft latitude in decimal degrees.            |
| `longitude`     | float     | `-3.5626`     | Aircraft longitude in decimal degrees.           |
| `baro_altitude` | float     | `9144.0`      | Barometric altitude in meters.                   |
| `geo_altitude`  | float     |               | Geometric altitude (meters)                      |
| `velocity`      | float     | `230.5`       | Ground speed in meters per second.               |
| `true_track`    | float     | `275.3`       | True track angle in degrees.                     |
| `vertical_rate` | float     | `-7.6`        | Vertical speed in meters per second.             |
| `on_ground`     | boolean   | `false`       | Indicates whether the aircraft is on the ground. |
| `squawk`        | string    |               | Transponder squawk code                          |


### Known data issues and limitations

State vector data is affected by several quality issues inherent to ADS-B-based surveillance systems:

- Irregular sampling rates, caused by heterogeneous receiver coverage and message loss.
- Callsigns are not guaranteed to be present or consistent across the flight.
- Temporal gaps, particularly in low-coverage areas or at low altitudes.
- Missing or null values for certain attributes (e.g., altitude or velocity).
- Out-of-order timestamps, due to delayed message reception or aggregation artifacts.
- Spurious or noisy measurements, especially during takeoff, landing, or maneuvering phases.

These issues motivate the need for trajectory reconstruction, reordering, filtering, and quality assessment stages in the processing pipeline.

Additional considerations derived from the used data source:

- The surveillance data is partitioned based on the local timezone of capture: Europe/Madrid. That is, for each partition the data ranges from 22:00:00 to 21:59:59 UTC. Since this fact does not interfere with the processing of the trajectories, repartitioning the data according to the UTC time is not necessary.

---

## Flights API

### Access

The Flights API is provided by OpenSky Network and allows querying flight-level information over a specified time interval. Access conditions are similar to those of the state vectors API.

### Data structure

Each record corresponds to a detected flight and aggregates information derived from surveillance data.

| Attribute name        | Data type | Example value | Description                                   |
| --------------------- | --------- | ------------- | --------------------------------------------- |
| `icao24`              | string    | `"3451A2"`    | Unique ICAO 24-bit aircraft address.          |
| `callsign`            | string    | `"IBE3152"`   | Aircraft callsign, if available.              |
| `firstSeen`           | integer   | `1672526400`  | Timestamp of the first detected state vector. |
| `lastSeen`            | integer   | `1672535400`  | Timestamp of the last detected state vector.  |
| `estDepartureAirport` | string    | `"LEBL"`      | Estimated departure airport (ICAO code).      |
| `estArrivalAirport`   | string    | `"LEMD"`      | Estimated arrival airport (ICAO code).        |

Some derived attributes relative to the estimated departure and arrival airports are also available, but they are not used in this project.

### Known data issues and limitations

- Estimated airports may be missing or incorrect, as they are inferred from surveillance data.
- Callsigns are not guaranteed to be present or consistent across the flight.
- Flights with sparse surveillance coverage may be partially detected or fragmented.

---

## References

- OpenSky Network API documentation:
  https://openskynetwork.github.io/opensky-api/
- Schäfer et al. Bringing Up OpenSky: A Large-scale ADS-B Sensor Network for Research. IPSN 2014.