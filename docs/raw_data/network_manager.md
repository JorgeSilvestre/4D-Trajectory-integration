# Network Manager (EUROCONTROL)

This document describes the data obtained from the **Network Manager (NM)** operated
by EUROCONTROL, which provides authoritative operational air traffic management data
for the European airspace.

Within this project, Network Manager data is used as a high-quality reference source
for flight planning and flight execution information.

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

## Relationship between FPLAN and FDATA

Flight Plan and Flight Data messages are linked through the `ifplId` identifier.

While Flight Plans describe intended operations, Flight Data reflects the actual
execution of the flight. Consistency between both datasets is not guaranteed and
must be assessed during integration.

## References

- EUROCONTROL Network Manager documentation
