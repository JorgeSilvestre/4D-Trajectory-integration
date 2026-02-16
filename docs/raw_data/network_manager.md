# Network Manager (EUROCONTROL)

## Data source description

The Network Manager (NM), operated by EUROCONTROL, is the central system responsible for air traffic flow and capacity management in the European airspace. It aggregates operational data provided by airspace users and air navigation service providers, covering both **planned** and **executed** flights.

Two distinct datasets are extracted from Network Manager:
- **Flight Plans (FPLAN)**: structured flight plan messages.
- **Flight Data (FDATA)**: operational flight updates and execution-related messages.

In contrast to surveillance-based sources, Network Manager data represents the **operational intent and status of flights**, as defined and updated through flight plan submissions and operational messages. Within this project, NM data is used to provide authoritative flight-level metadata that complements surveillance-derived trajectories, enabling flight identification, temporal alignment, and consistency checks.

The original data is delivered as highly nested JSON messages.

---

## Flight Plan data (FPLAN)

### Access

Flight Plan data is provided through restricted Network Manager services. Access requires authorization and is subject to EUROCONTROL data usage policies.

### Data structure

Flight Plan messages describe the intended characteristics of a flight, and may be updated multiple times prior to departure.

| Attribute name | Data type | Example value | Description |
|---------------|-----------|---------------|-------------|
| `ifplId` | string | `"IFPL123456"` | Unique flight plan identifier assigned by Network Manager. |
| `timestamp` | integer | `1672562400` | Message timestamp (Unix epoch, seconds). |
| `callsign` | string | `"IBE3152"` | Aircraft callsign. |
| `icao24` | string | `"3451A2"` | ICAO 24-bit aircraft address. |
| `aerodromeOfDeparture` | string | `"LEBL"` | ICAO code of the departure airport. |
| `aerodromeOfDestination` | string | `"LEMD"` | ICAO code of the destination airport. |
| `estimatedOffBlockTime` | integer | `1672564200` | Estimated off-block time (Unix epoch, seconds). |
| `operator` | string | `"IBE"` | Aircraft operator. |
| `operatingOperator` | string | `"IBE"` | Operating aircraft operator. |
| `registrationMark` | string | `"EC-MXY"` | Aircraft registration mark. |
| `ssr` | string | `"1234"` | Secondary surveillance radar code. |
| `flightType` | string | `"S"` | Flight type (e.g. scheduled, non-scheduled). |
| `aircraftType` | string | `"A320"` | ICAO aircraft type designator. |
| `totalEstimatedElapsedTime` | integer | `75` | Estimated flight duration (minutes). |
| `wakeTurbulenceCategory` | string | `"M"` | Wake turbulence category. |
| `uuid` | string | `"550e8400-e29b..."` | Unique message identifier. |

### Known data issues and limitations

- Multiple messages per flight plan, reflecting updates and amendments over time.
- Partial information in early messages, with some attributes only appearing in later updates.
- Aircraft identifiers (e.g. ICAO24, registration) may be absent in some messages.
- Flight duration is encoded as a string and requires parsing.
- Highly nested original structure, requiring explicit flattening and schema normalization.

---

## Flight Data (FDATA)

### Access

Flight Data messages are provided by the Network Manager as post-operational or near-real-time updates describing the **actual execution and state of flights**. Access is restricted and subject to authorization.

### Data structure

Each Flight Data message describes the operational status of a flight and may be updated multiple times. The following table lists the attributes used after normalization and consolidation.

| Attribute name | Data type | Example value | Description |
|---------------|-----------|---------------|-------------|
| `ifplId` | string | `"IFPL123456"` | Unique flight plan identifier. |
| `timestamp` | integer | `1672566000` | Message timestamp (Unix epoch, seconds). |
| `callsign` | string | `"IBE3152"` | Aircraft callsign. |
| `icao24` | string | `"3451A2"` | ICAO 24-bit aircraft address. |
| `aerodromeOfDeparture` | string | `"LEBL"` | ICAO code of the departure airport. |
| `aerodromeOfDestination` | string | `"LEMD"` | ICAO code of the destination airport. |
| `estimatedOffBlockTime` | integer | `1672564200` | Estimated off-block time. |
| `estimatedTakeOffTime` | integer | `1672565100` | Estimated take-off time. |
| `actualOffBlockTime` | integer | `1672564500` | Actual off-block time. |
| `actualTakeOffTime` | integer | `1672565400` | Actual take-off time. |
| `estimatedTimeOfArrival` | integer | `1672570200` | Estimated arrival time. |
| `actualTimeOfArrival` | integer | `1672570800` | Actual arrival time. |
| `calculatedTakeOffTime` | integer | `1672565250` | System-calculated take-off time. |
| `calculatedTimeOfArrival` | integer | `1672570500` | System-calculated arrival time. |
| `flightState` | string | `"ARRIVED"` | Flight operational state. |
| `flightDataVersionNr` | integer | `5` | Version number of the flight data message. |
| `aircraftType` | string | `"A320"` | ICAO aircraft type designator. |
| `routeLength` | integer | `482` | Planned route length (nautical miles). |
| `operator` | string | `"IBE"` | Aircraft operator. |
| `operatingOperator` | string | `"IBE"` | Operating aircraft operator. |
| `uuid` | string | `"a12b34c5-d..."` | Unique message identifier. |

### Known data issues and limitations

- Multiple versions of flight data may exist for the same flight.
- Aircraft identifiers may be missing in early versions.
- Some operational timestamps may be missing or inconsistent.
- Message order is not guaranteed in the raw data.
- Timestamps are localized at Europe/Madrid timezone.
- Data are partitioned based on the estimatedOffBlockTime of the flight (localized at localized at Europe/Madrid timezone).
    - That is, for each partition the data ranges from 22:00:00 to 21:59:59 UTC.


---

## Relationship between FPLAN and FDATA

Flight Plan and Flight Data messages are linked through the `ifplId` identifier.

While Flight Plans describe intended operations, Flight Data reflects the actual
execution of the flight. Consistency between both datasets is not guaranteed and
must be assessed during integration.

## References

- EUROCONTROL. *Network Manager*. https://www.eurocontrol.int/network-manager