# OpenSky Network

## Data source description

OpenSky Network is an open surveillance platform that provides real-time and historical air traffic data. The data is collected from a distributed network of ADS-B (Automatic Dependent Surveillance–Broadcast) receivers operated by volunteers and institutional partners.

In this project, OpenSky is the primary surveillance source used to reconstruct 4D trajectories from timestamped state vectors. The Flights API was evaluated as a complementary flight-level source, but it is not part of the core integration flow due to coverage and consistency limitations.

Data is ingested as structured records (historically JSON, currently parquet in this repository) sampled at irregular intervals due to heterogeneous receiver coverage and message loss.

---

## State Vectors

### Access

State vectors are available through the OpenSky API. Anonymous access is rate-limited; authenticated access provides higher quotas and broader historical coverage. Requests can be filtered by spatial and temporal bounds.

### Data structure

Each state vector represents one aircraft observation. The main attributes used by this pipeline are:

| Attribute name  | Data type | Example value | Description                                      |
| --------------- | --------- | ------------- | ------------------------------------------------ |
| `icao24`        | string    | `"3451A2"`    | ICAO 24-bit aircraft address.                    |
| `callsign`      | string    |               | Aircraft callsign, when available.               |
| `time_position` | integer   | `1672531200`  | UNIX timestamp of the latest known position.     |
| `last_contact`  | integer   |               | UNIX timestamp of the latest received message.   |
| `latitude`      | float     | `40.4719`     | Latitude in decimal degrees.                     |
| `longitude`     | float     | `-3.5626`     | Longitude in decimal degrees.                    |
| `baro_altitude` | float     | `9144.0`      | Barometric altitude (meters).                    |
| `geo_altitude`  | float     |               | Geometric altitude (meters).                     |
| `velocity`      | float     | `230.5`       | Ground speed (m/s).                              |
| `true_track`    | float     | `275.3`       | True track angle (degrees).                      |
| `vertical_rate` | float     | `-7.6`        | Vertical rate (m/s).                             |
| `on_ground`     | boolean   | `false`       | Ground status flag.                              |
| `squawk`        | string    |               | Transponder squawk code.                         |

### Known data issues and limitations

OpenSky state vectors inherit typical ADS-B quality constraints:

- Irregular sampling intervals.
- Missing or inconsistent callsigns.
- Temporal gaps in low-coverage areas.
- Null values in kinematic fields.
- Out-of-order timestamps due to delayed reception or aggregation.
- Noisy observations during high-dynamics phases (e.g., takeoff/landing).

These constraints motivate source-local cleaning before cross-source integration.

Additional repository-specific note:

- Surveillance partitions are aligned to `Europe/Madrid` local-day boundaries (`22:00:00` to `21:59:59` UTC in many periods). Repartitioning to UTC day boundaries is currently not required by downstream processing.

---

## Flights API

### Access

The Flights API provides aggregated flight-level records over time intervals. Access restrictions are equivalent to the state vectors API.

### Data structure

Each record corresponds to one detected flight:

| Attribute name        | Data type | Example value | Description                                   |
| --------------------- | --------- | ------------- | --------------------------------------------- |
| `icao24`              | string    | `"3451A2"`    | ICAO 24-bit aircraft address.                 |
| `callsign`            | string    | `"IBE3152"`   | Aircraft callsign, when available.            |
| `firstSeen`           | integer   | `1672526400`  | Timestamp of first detected state vector.     |
| `lastSeen`            | integer   | `1672535400`  | Timestamp of last detected state vector.      |
| `estDepartureAirport` | string    | `"LEBL"`      | Estimated departure airport ICAO code.        |
| `estArrivalAirport`   | string    | `"LEMD"`      | Estimated arrival airport ICAO code.          |

Some additional airport-derived attributes are available but are not used in this project.

### Known data issues and limitations

- Estimated airports may be missing or incorrect.
- Callsigns are not guaranteed to be present or stable.
- Sparse surveillance can lead to fragmented/partial flights.

---

## References

- OpenSky Network API documentation: <https://openskynetwork.github.io/opensky-api/>
- Schäfer et al. *Bringing Up OpenSky: A Large-scale ADS-B Sensor Network for Research*. IPSN 2014.
