# Network Manager (EUROCONTROL)

## Data source description

The Network Manager (NM), operated by EUROCONTROL, is the central system responsible for air traffic flow and capacity management in the European airspace. It aggregates operational data provided by airspace users and air navigation service providers, covering both **planned** and **executed** flights.

In contrast to surveillance-based sources, Network Manager data represents the **operational intent and status of flights**, as defined and updated through flight plan submissions and operational messages. Within this project, NM data is used to provide authoritative flight-level metadata that complements surveillance-derived trajectories, enabling flight identification, temporal alignment, and consistency checks.

The original data is delivered as highly nested JSON messages.

---

## Flight Plan data (FPLAN)

### Access

Flight Plan data is provided through restricted Network Manager services. Access requires authorization and is subject to EUROCONTROL data usage policies.

---

### Data structure

Flight Plan messages describe the **intended characteristics of a flight**, and may be updated multiple times prior to departure.

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

---

### Known data issues and limitations

- **Multiple messages per flight plan**, reflecting updates and amendments over time.
- **Partial information in early messages**, with some attributes only appearing in later updates.
- **Differences between planned and executed flights**, as the data represents intent rather than actual behavior.
- **Highly nested original structure**, requiring explicit flattening and schema normalization.

---

## Flight Data (FDATA)

### Access

Flight Data messages are provided by the Network Manager as post-operational or near-real-time updates describing the **actual execution and state of flights**. Access is restricted and subject to authorization.

---

### Data structure

Each Flight Data message describes the operational status of a flight and may be updated multiple times. Table 2 lists the attributes used after normalization and consolidation.

**Table 2 – Network Manager Flight Data attributes used in the project**

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

---

### Known data issues and limitations

- **Multiple versions per flight**, requiring consolidation based on version number.
- **Missing or delayed actual times**, especially for ongoing or partially reported flights.
- **Inconsistencies with surveillance data**, due to different data generation mechanisms and update cycles.

---

## References

- EUROCONTROL. *Network Manager*. https://www.eurocontrol.int/network-manager



# Network Manager (EUROCONTROL)

This document describes the data obtained from the **Network Manager (NM)** operated
by EUROCONTROL, which provides authoritative operational air traffic management data
for the European airspace.

Within this project, Network Manager data is used as a high-quality reference source for flight planning and flight execution information.

Two distinct datasets are extracted from Network Manager:

- **Flight Plans (FPLAN)**: structured flight plan messages.
- **Flight Data (FDATA)**: operational flight updates and execution-related messages.

Although both datasets are linked through a common flight identifier, they differ in
structure, temporal behavior and semantic meaning, and are documented separately.

## Source characterization

Network Manager data originates from the operational systems used by EUROCONTROL to
manage air traffic flows within the European Civil Aviation Conference (ECAC) area.

Unlike surveillance-based sources, Network Manager data is:

- Authoritative and operational in nature.
- Highly structured and schema-driven.
- Event-based rather than observation-based.

The data reflects planned and executed flight information as exchanged between
airspace users and air traffic management systems.


## Flight plans

FPLAN

### Source and access

Flight Plan data consists of structured flight plan messages submitted to Network
Manager prior to flight execution.

Each message represents either the creation or update of a flight plan and contains
detailed information about the planned flight, including aircraft, routing and timing
information.

Messages are provided as JSON records with a deeply nested structure.

### Data structure

The main attributes extracted from Flight Plan messages are summarized below.

| Attribute | Type | Description |
|----------|------|-------------|
| `ifplId` | string | Unique flight plan identifier |
| `timestamp` | integer | Message timestamp (UNIX time, seconds) |
| `icao24` | string | Aircraft ICAO 24-bit address |
| `callsign` | string | Aircraft callsign |
| `registrationMark` | string | Aircraft registration |
| `aerodromeOfDeparture` | string | Departure aerodrome (ICAO) |
| `aerodromeOfDestination` | string | Destination aerodrome (ICAO) |
| `estimatedOffBlockTime` | integer | Estimated off-block time |
| `operator` | string | Aircraft operator |
| `operatingOperator` | string | Operating airline |
| `flightType` | string | Flight type |
| `aircraftType` | string | Aircraft ICAO type designator |
| `wakeTurbulenceCategory` | string | Wake turbulence category |
| `totalEstimatedElapsedTime` | integer | Planned flight duration (minutes) |
| `uuid` | string | Unique message identifier |

### Known data issues and limitations

- Multiple flight plan messages may exist for the same flight.
- Attributes may be missing in early messages and only appear in later updates.
- Aircraft identifiers (e.g. ICAO24, registration) may be absent in some messages.
- Flight duration is encoded as a string and requires parsing.
- The deeply nested JSON structure complicates direct analysis.



## Flight data

FDATA

## Flight Data (FDATA)

### Source and access

Flight Data messages describe the operational evolution of a flight after planning.
They include estimated, calculated and actual timestamps related to flight execution.

Messages are versioned and may be updated multiple times throughout the flight.

### Data structure

The main attributes extracted from Flight Data messages are summarized below.

| Attribute | Type | Description |
|----------|------|-------------|
| `ifplId` | string | Flight identifier |
| `timestamp` | integer | Message timestamp |
| `flightDataVersionNr` | integer | Version number of flight data |
| `icao24` | string | Aircraft ICAO 24-bit address |
| `callsign` | string | Aircraft callsign |
| `aerodromeOfDeparture` | string | Departure aerodrome |
| `aerodromeOfDestination` | string | Destination aerodrome |
| `estimatedOffBlockTime` | integer | Estimated off-block time |
| `estimatedTakeOffTime` | integer | Estimated take-off time |
| `actualOffBlockTime` | integer | Actual off-block time |
| `actualTakeOffTime` | integer | Actual take-off time |
| `estimatedTimeOfArrival` | integer | Estimated arrival time |
| `actualTimeOfArrival` | integer | Actual arrival time |
| `calculatedTakeOffTime` | integer | Calculated take-off time |
| `calculatedTimeOfArrival` | integer | Calculated arrival time |
| `flightState` | string | Operational flight state |
| `routeLength` | integer | Route length |
| `uuid` | string | Unique message identifier |

### Known data issues and limitations

- Multiple versions of flight data may exist for the same flight.
- Aircraft identifiers may be missing in early versions.
- Some operational timestamps may be missing or inconsistent.
- Message order is not guaranteed in the raw data.
- Timestamps are localized at Europe/Madrid timezone.
- Data are partitioned based on the estimatedOffBlockTime of the flight (localized at localized at Europe/Madrid timezone).
    - That is, for each partition the data ranges from 22:00:00 to 21:59:59 UTC.

## Relationship between FPLAN and FDATA

Flight Plan and Flight Data messages are linked through the `ifplId` identifier.

While Flight Plans describe intended operations, Flight Data reflects the actual
execution of the flight. Consistency between both datasets is not guaranteed and
must be assessed during integration.

## References

- EUROCONTROL Network Manager documentation
