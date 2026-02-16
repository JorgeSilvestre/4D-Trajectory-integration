# Network Manager (EUROCONTROL)

## Data source description

EUROCONTROL Network Manager (NM) provides operational flight information for European airspace. In this project, NM is the authoritative flight-level source used to complement surveillance trajectories with identifiers, aerodromes, and operational timestamps.

The raw feed is delivered as deeply nested JSON messages and is processed into two logical datasets:

- **FPLAN (Flight Plan)**: intent-oriented flight-plan messages.
- **FDATA (Flight Data)**: execution/status updates with versioned state.

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

## Relationship between FPLAN and FDATA

FPLAN and FDATA are linked by `ifplId`, but they represent different semantics:

- **FPLAN**: intended operation.
- **FDATA**: observed operational evolution.

Consistency between both datasets is not guaranteed and is resolved in later integration stages.

---

## References

- EUROCONTROL Network Manager: <https://www.eurocontrol.int/network-manager>
