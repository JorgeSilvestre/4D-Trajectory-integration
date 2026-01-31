# OpenSky Network

This document describes the data obtained from the **OpenSky Network** and its role
within this project. The focus is on the origin, structure and known limitations of
the data, prior to any cleaning or integration steps.

OpenSky provides open air traffic surveillance data collected from a distributed
network of ADS-B receivers operated by both volunteers and institutional partners.

In this project, two distinct datasets are extracted from OpenSky:

- **State vectors**, representing aircraft positions over time.
- **Flights**, representing flight-level summaries inferred from surveillance data.

Although both datasets originate from the same source, they differ significantly in
granularity, semantics and intended usage, and are therefore documented separately.

---

## State Vectors

### Source and access

State vectors are derived from ADS-B messages broadcast by aircraft and collected by
the OpenSky Network receiver infrastructure. This preprocessing
is performed by OpenSky and includes basic decoding and aggregation of ADS-B data.

Each state vector represents an instantaneous estimate of the aircraft state at a
given time.

### Data structure

Each state vector corresponds to a single aircraft observation. The main attributes
used in this project are summarized below.

| Attribute            | Type        | Description |
|----------------------|-------------|-------------|
| `icao24`             | string      | Unique aircraft identifier (ICAO 24-bit address) |
| `callsign`           | string      | Aircraft callsign, if available |
| `time_position`      | integer     | Timestamp of the position estimate (UNIX time, seconds) |
| `last_contact`       | integer     | Timestamp of the last received ADS-B message |
| `latitude`           | float       | WGS84 latitude (degrees) |
| `longitude`          | float       | WGS84 longitude (degrees) |
| `baro_altitude`      | float       | Barometric altitude (meters) |
| `geo_altitude`       | float       | Geometric altitude (meters) |
| `velocity`           | float       | Ground speed (m/s) |
| `true_track`         | float       | Track angle relative to true north (degrees) |
| `vertical_rate`      | float       | Vertical rate (m/s) |
| `on_ground`          | boolean     | Indicates whether the aircraft is on the ground |
| `squawk`             | string      | Transponder squawk code |

### Temporal characteristics

- Observations are irregularly sampled.
- Update rates vary across aircraft, time and geographic coverage.
- Multiple observations may exist for the same aircraft within a short time window.
- Two different timestamps are provided:
  - `time_position`, associated with the latest ADS-B message indicating the aircraft's position.
  - `last_contact`, associated with the latest ADS-B message of any type.

### Known data issues and limitations

State vector data exhibits several known issues that must be considered before
trajectory reconstruction:

- **Missing values** are frequent, especially for altitude, velocity and callsign.
- **Invalid coordinates** may appear (e.g. latitude or longitude outside valid ranges).
- **Duplicate observations** can occur for the same aircraft, time and position.
- **Temporal inconsistencies** exist between `time_position` and `last_contact`.
- **Inconsistent callsigns**, including trailing spaces and mixed casing.
- **Uneven sampling density**, depending on receiver coverage and aircraft equipment.
- **Altitude ambiguity**, as both barometric and geometric altitude may be present,
  missing or inconsistent.

These issues motivate a dedicated cleaning stage prior to any trajectory-level
processing.



- Missing values are common, especially for altitude and velocity-related fields.
- Some observations may contain physically inconsistent values
  (e.g. invalid coordinates).
- Duplicate or near-duplicate observations can occur.
- Aircraft identifiers and callsigns may include trailing spaces or inconsistent casing.
- Data quality depends on receiver coverage and aircraft equipage.

---

## Flights API

### Source and access

The Flights dataset is obtained through the OpenSky Flights API. It provides
flight-level summaries inferred from state vector data using OpenSky internal
segmentation heuristics.

Each record represents a complete flight, from first to last detection.

### Data structure

Each flight record includes the following main attributes:

| Attribute          | Type    | Description |
|--------------------|---------|-------------|
| `icao24`           | string  | Aircraft identifier |
| `callsign`         | string  | Aircraft callsign |
| `firstSeen`        | integer | Timestamp of first detection (UNIX time, seconds) |
| `lastSeen`         | integer | Timestamp of last detection |
| `estDepartureAirport` | string | Estimated departure airport (ICAO) |
| `estArrivalAirport`   | string | Estimated arrival airport (ICAO) |


### Known data issues and limitations

- Departure and arrival airports are estimated and may be missing or incorrect.
- Flights may span multiple calendar days.
- Callsigns may be missing or inconsistent.
- Flight segmentation depends on internal OpenSky heuristics and may differ from
  operational definitions.
- Near-boundary flights may appear in multiple daily extracts.

Blabla

- Departure and arrival airports are estimated and may be missing or incorrect.
- Callsigns may be inconsistent or missing.
- Flights inferred near day boundaries may appear in multiple daily extracts.
- Flight segmentation depends on OpenSky internal heuristics and may differ from
  operational definitions.

---

## References

- OpenSky Network API documentation:
  https://openskynetwork.github.io/opensky-api/