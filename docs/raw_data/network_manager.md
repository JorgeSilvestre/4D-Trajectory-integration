# Network Manager (EUROCONTROL)

## Data source description

EUROCONTROL Network Manager (NM) provides operational flight information for European airspace. In this project, NM is the authoritative flight-level source used to complement surveillance trajectories with identifiers, aerodromes, and operational timestamps.

The raw feed is delivered as deeply nested JSON messages and is processed into two logical datasets:

- **FPLAN (Flight Plan)**: intent-oriented flight-plan messages.
- **FDATA (Flight Data)**: execution/status updates with versioned state.

FPLAN and FDATA are linked by `ifplId`,

---

## Flight Plan data (FPLAN)

### Access

Access to NM FPLAN messages is restricted and subject to EUROCONTROL authorization and usage policies.

### Data structure

Each record corresponds to one FPLAN message version for a flight (`ifplId`).

| Attribute name | Type | Example value | Description |
|---|---|---|---|
| `ifplId` | string | `"IFPL123456"` | NM flight plan identifier. |
| `timestamp` | datetime (UTC) | `2023-01-01T10:00:00Z` | Message timestamp. |
| `callsign` | string | `"IBE3152"` | Aircraft callsign. |
| `icao24` | string | `"3451A2"` | ICAO 24-bit address. |
| `aerodromeOfDeparture` | string | `"LEBL"` | Departure ICAO code. |
| `aerodromeOfDestination` | string | `"LEMD"` | Destination ICAO code. |
| `estimatedOffBlockTime` | datetime (UTC) | `2023-01-01T10:30:00Z` | EOBT. |
| `operator` | string | `"IBE"` | Aircraft operator. |
| `operatingOperator` | string | `"IBE"` | Operating aircraft operator. |
| `registrationMark` | string | `"EC-MXY"` | Aircraft registration. |
| `ssr` | string | `"1234"` | SSR code. |
| `flightRules` | string | `"I"` | Flight rules metadata. |
| `flightType` | string | `"S"` | Flight type metadata. |
| `aircraftType` | string | `"A320"` | ICAO aircraft type. |
| `totalEstimatedElapsedTime` | integer | `75` | EET converted to minutes from NM HHMM format. |
| `wakeTurbulenceCategory` | string | `"M"` | Wake category. |
| `uuid` | string | `"550e8400-e29b-41d4-a716-446655440000"` | Source message unique identifier. |

### Known data issues and limitations

- Multiple message versions per `ifplId`.
- Important fields can be null in early versions and appear later.
- Raw JSON structure requires explicit flattening.
- EET arrives as HHMM string and must be parsed before analysis.

---

## Flight Data (FDATA)

### Access

Access to NM FDATA messages is restricted under EUROCONTROL policies.

### Data structure

Each record corresponds to one versioned operational update (`flightDataVersionNr`) for a flight.

| Attribute name | Type | Example value | Description |
|---|---|---|---|
| `ifplId` | string | `"IFPL123456"` | NM flight plan identifier. |
| `timestamp` | datetime (UTC) | `2023-01-01T10:45:00Z` | Message timestamp. |
| `callsign` | string | `"IBE3152"` | Aircraft callsign. |
| `icao24` | string | `"3451A2"` | ICAO 24-bit address. |
| `aerodromeOfDeparture` | string | `"LEBL"` | Departure ICAO identifier. |
| `aerodromeOfDestination` | string | `"LEMD"` | Destination ICAO identifier. |
| `estimatedOffBlockTime` | datetime (UTC) | `2023-01-01T10:30:00Z` | EOBT. |
| `estimatedTakeOffTime` | datetime (UTC) | `2023-01-01T10:50:00Z` | Estimated takeoff time. |
| `actualOffBlockTime` | datetime (UTC) | `2023-01-01T10:36:00Z` | Actual off-block time. |
| `actualTakeOffTime` | datetime (UTC) | `2023-01-01T10:54:00Z` | Actual takeoff time. |
| `estimatedTimeOfArrival` | datetime (UTC) | `2023-01-01T12:05:00Z` | Estimated arrival time. |
| `actualTimeOfArrival` | datetime (UTC) | `2023-01-01T12:10:00Z` | Actual arrival time. |
| `calculatedTakeOffTime` | datetime (UTC) | `2023-01-01T10:52:00Z` | NM-calculated takeoff milestone. |
| `calculatedTimeOfArrival` | datetime (UTC) | `2023-01-01T12:08:00Z` | NM-calculated arrival milestone. |
| `flightState` | string | `"ARRIVED"` | Operational state. |
| `flightDataVersionNr` | integer | `5` | Version number within `ifplId`. |
| `aircraftType` | string | `"A320"` | ICAO aircraft type. |
| `routeLength` | integer | `482` | Route length metadata. |
| `operator` | string | `"IBE"` | Aircraft operator. |
| `operatingOperator` | string | `"IBE"` | Operating aircraft operator. |
| `uuid` | string | `"a12b34c5-d678-4ee0-a111-22bb33cc44dd"` | Source message unique identifier. |

### Known data issues and limitations

- Version ordering is not guaranteed in raw files and must be enforced.
- Some identifiers/timestamps are missing in early versions.
- Daily partitions are aligned to local Europe/Madrid boundaries rather than strict UTC-day boundaries.

---

## ADRR Flight Data

Eurocontrol makes accesible a repository where researchers can access detailed datasets on aircraft trajectories and related airspace information. Datasets in this repository contain:
- detailed flight information,
- flight trajectories (planned and actual),
- airspace structure, and
- route network information.

### Access

The access to these datasets requires the availability of an OneSky Online account, which is subject to approval after requiring the registration.

### Data structure

We only leverage flight data at the moment in this project. Flight data is provided as monthly CSV, containing one line per flight with the following columns:

| Attribute name | Type | Example value | Description |
|---|---|---|---|
| ECTL_ID | string | `"261882769"` | Unique numeric identifier for each flight in Eurocontrol PRISME DWH.  |
| ADEP | string | `"KATL"` | Departure ICAO identifier.  |
| ADEP Latitude | float64 | `33.63333` | Latitude of departure airport in decimal degrees.  |
| ADEP Longitude | float64 | `-84.43333` | Longitude of departure airport in decimal degrees.  |
| ADES | string | `"EIDW"` | Destination ICAO identifier.  |
| ADES Latitude | float64 | `53.42139` | Latitude of destination airport in decimal degrees.  |
| ADES Longitude | float64 | `-6.27` | Longitude of destination airport in decimal degrees.  |
| Filed Off-Block Time | datetime (UTC) | `01-06-2023 00:00:00` | Off-Block Time (UTC) based on the last filed flight plan. |
| Filed Arrival Time | datetime (UTC) | `01-06-2023 07:35:32` | Time of arrival (UTC) based on the last filed flight plan. |
| Actual Off-Block Time | datetime (UTC) | `01-06-2023 00:17:00` | Off-Block Time (UTC) based on the ATFM-updated flight plan. The time that an aircraft departs from its parking position. |
| Actual Arrival Time | datetime (UTC) | `01-06-2023 07:57:13` | Time of arrival (UTC) based on the ATFM-updated flight plan. It is the time at which the aircraft lands at the aerodrome. |
| AC Type | string | `"A359"` | ICAO aircraft type designator.  |
| AC Operator | string | `"DAL"` | Three-letter ICAO operator code. If the operator is unknown, not provided in the flight plan the value is "ZZZ".  |
| AC Registration | string | `"N576DZ"` | Aircraft registration. |
| ICAO Flight Type | string | `"S"` | ICAO Flight Type: S – Scheduled, N - Non-scheduled commercial operation |
| Requested FL | float64 | `370.0` | Requested cruising flight level from the flight plan.  |
| Actual Distance Flown (nm) | int64 | `3508` | Distance flown in nautical miles. |

### Known data issues and limitations

- The data correspond with consolidated flight plans after the flight has ended, so it only contains the last snapshot of the flight plan (without any notion of the changes in the data across the flight) of terminated flights.
- The data is not exhaustive from a time perspective: only one month out of three is available per year (March, June, September, December).
- New updates are published with a 2-year delay (e.g. the latest update in 2025 introduced data from 2023).
- Flight data from this source can only be integrated with surveillance data using the callsign of the flight (which is not always available in OpenSky data), since they do not contain ICAO24 identifiers.

---

## References

- EUROCONTROL Network Manager: <https://www.eurocontrol.int/network-manager>
- EUROCONTROL B2B Reference Manuals FlightServices
- EUROCONTROL B2B Reference Manuals PublishSubscribeServices
- ADRR: https://www.eurocontrol.int/dashboard/aviation-data-research
