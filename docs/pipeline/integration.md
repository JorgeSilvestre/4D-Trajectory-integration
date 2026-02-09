# Data Integration Pipeline (L1 → L2)

This document describes the data integration stage that combines cleaned individual sources (L1) into integrated datasets (L2). The primary output of this stage is the construction of raw 4D trajectories by matching flight metadata with surveillance observations.

---

## Overview

The integration pipeline operates on L1 cleaned data and produces L2 integrated datasets. The process consists of two main stages:

1. **Flight Record Consolidation**: Merging Network Manager flight plans and flight data
2. **Trajectory Construction**: Matching flight records with OpenSky state vectors

---

## Stage 1: Flight Record Consolidation

### Purpose

Network Manager provides flight information through two complementary data streams:
- **Flight Plans (FPLAN)**: Pre-flight planned information  
- **Flight Data (FDATA)**: Operational execution information

These must be merged to create a complete view of each flight containing both planned and actual operational data.

### Consolidation Process

#### Version Selection

Both FPLAN and FDATA messages are versioned and may be updated multiple times per flight.

**Flight Plan:** Select the last message per flight (by timestamp)
- Rationale: Latest version contains most complete and up-to-date planning information

**Flight Data:** For TERMINATED flights with multiple updates, select first TERMINATED message; otherwise select latest version
- Rationale: Avoid using late updates that modify arrival times after landing

#### Attribute Consolidation

When attributes appear in both sources, conflicts are resolved by:
- **Preferring FDATA values** over FPLAN values (actual over planned)
- Using `combine_first()` to fill missing values from either source

Consolidated attributes include: `icao24`, `callsign`, `estimatedOffBlockTime`, `aerodromeOfDeparture`, `aerodromeOfDestination`, `operator`, `operatingOperator`, `aircraftType` (all FDATA preferred).

#### Temporal Consistency Validation

After merging, flights are filtered to ensure FPLAN and FDATA refer to the same flight:

```python
valid_flights = flights[
    (actualTakeOffTime > estimatedOffBlockTime - 1 day) &
    (actualTimeOfArrival < estimatedOffBlockTime + 2 days)
]
```

**Purpose:** Detect ifplId reuse where FPLAN and FDATA refer to different flights.

### Output

**Location:** `data/L1/nmFlights/nm.flights.{date}.parquet`

**Schema:** 22 attributes combining FPLAN and FDATA information (see FLIGHT_ATTRIBUTE_NAMES in code)

---

## Stage 2: Trajectory Construction

### Purpose

Match consolidated flight records with OpenSky state vectors to construct 4D trajectories. Each trajectory consists of:
- Flight metadata (origin, destination, times, identifiers)
- Sequence of state vectors (position, velocity, altitude observations)

### Matching Strategy

#### Identifier Matching

State vectors are matched to flights by **ICAO24 aircraft address**.

**Rationale:**
- ICAO24 is globally unique aircraft identifier
- More reliable than callsign (which can be missing or reused)
- Directly comparable between NM and OpenSky data

**Optimization:** Vectors are pre-filtered to only include ICAO24 values present in the flight list before joining.

#### Temporal Filtering

After identifier matching, vectors are filtered by temporal overlap with flight execution:

```python
matched_vectors = vectors[
    (timestamp >= actualTakeOffTime - TIME_EXPANSION) &
    (timestamp <= actualTimeOfArrival + TIME_EXPANSION)
]
```

**TIME_EXPANSION:** 600 seconds (10 minutes)

**Purpose:** Account for uncertainty in actual times and capture vectors near airports.

### Processing Flow

1. Load flights with optional airport filtering
2. Remove return flights (same origin and destination)
3. For each state vector file:
   - Load vectors
   - Pre-filter by ICAO24
   - Join with flights
   - Filter by temporal overlap
   - Accumulate matched vectors
4. Consolidate all matched vectors
5. Filter trajectories with < MIN_VECTOR_NUMBER (200) vectors
6. Write outputs

### Overnight Flight Handling

Flights crossing midnight require loading vectors from both the current date and the next day, as OpenSky vectors are partitioned by date.

### Output Structure

#### Trajectory Vectors (Parquet)

**Location:** `data/L2/nmTrajectories/tray.{date}.parquet`

All state vectors for all trajectories in a single file, with `ifplId` added to link to flight metadata.

#### Trajectory Metadata (JSON)

**Location:** `data/L2/nmTrajectories/flightDate={date}/tray.{ifplId}.json`

One JSON file per trajectory containing:
- Flight identifiers and airports
- Temporal information (estimated, actual, observation times)
- Vector count and data sources
- Processing status marker

#### Integration Metrics (JSON)

**Location:** `reports/L2_integration_metrics/integration.{date}.json`

Tracks integration success rates and data volume:

| Metric | Description |
|--------|-------------|
| `num_flights_initial` | Flights after airport filtering |
| `num_flights` | Flights after removing return flights |
| `returned_flights` | Removed return flights |
| `num_vectors` | Total state vectors processed |
| `num_joined_vectors` | Vectors matched to flights |
| `num_joined_flights` | Flights with matched vectors |
| `num_joined_vectors_final` | Vectors after trajectory filtering |
| `num_joined_flights_final` | Final trajectory count |
| `removed_short_trajectories` | Trajectories below minimum threshold |

---

## Integration Parameters

Defined in `trajectoryIntegration/params.py`:

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `TIME_EXPANSION` | 600 seconds | Temporal tolerance for vector matching |
| `MIN_VECTOR_NUMBER` | 200 | Minimum vectors required per trajectory |

---

## Relationship with Pipeline Stages

```
L0 (Raw)          L1 (Cleaned)        L2 (Integrated)     L3 (Trajectories)
────────          ────────────        ───────────────     ─────────────────
NM FPLAN    →     NM FPLAN     ──┐
                                 ├──→  NM Flights ──┐
NM FDATA    →     NM FDATA     ──┘                  │
                                                    ├──→  Raw         →  Clean
OpenSky     →     OpenSky      ─────────────────────┘     Trajectories   Trajectories
Vectors           Vectors                                 (L2)           (L3)
```

**Input from L1:** Cleaned, deduplicated, normalized individual sources with schema standardization complete.

**Output to L3:** Integrated trajectories with matched surveillance and metadata, ready for trajectory-specific processing (sorting, outlier removal).
