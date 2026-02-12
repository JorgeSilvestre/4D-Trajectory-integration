# Data Quality Metrics for Individual Sources

This document describes the quality metrics computed for each data source at both L0 (raw) and L1 (cleaned) maturity levels.

Quality metrics are automatically generated for each processing date and stored as JSON files in the `reports/` directory, following the structure:

```
reports/
├── L0_fplan/          # Raw Network Manager Flight Plans
├── L0_fdata/          # Raw Network Manager Flight Data
├── L0_vectors/        # Raw OpenSky state vectors
├── L0_taf/            # Raw Terminal Area Forecasts
├── L1_fplan/          # Cleaned Flight Plans
├── L1_fdata/          # Cleaned Flight Data
├── L1_vectors/        # Cleaned state vectors
└── L1_taf/            # Cleaned TAF forecasts
```

---

## Metric Categories by Source

| Metric Category | OpenSky Vectors | NM FPlan | NM FData | TAF |
|-----------------|-----------------|----------|----------|-----|
| **Volume** | ✓ | ✓ | ✓ | ✓ |
| **Completeness** | ✓ | ✓ | ✓ | ✓ |
| **Uniqueness** | ✓ | ✓ | ✓ | ✓ |
| **Duplicates** | ✓ | ✓ | ✓ | - |
| **Position Duplicates** | ✓ | - | - | - |
| **Temporal Ranges** | - | ✓ | ✓ | ✓ |
| **Geographic Distribution** | - | ✓ | - | - |
| **Update Patterns** | - | ✓ | ✓ | - |
| **Weather Phenomena** | - | - | - | ✓ |

---

## OpenSky Network State Vectors

State vector metrics assess the quality and coverage of ADS-B surveillance data. Metrics are computed per processing date.

### Volume Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `num_vectors` | integer | Total number of state vectors in the dataset |
| `unique_aircraft` | integer | Number of unique ICAO24 addresses (from `uniqueness.icao24`) |

**Purpose:** Volume metrics establish the scale of the dataset and help identify anomalies such as missing data or unexpected spikes in message volume.

**Expected behavior:**
- L1 `num_vectors` should be lower than L0 due to removal of invalid positions and duplicates
- `unique_aircraft` typically ranges from thousands to tens of thousands depending on geographic coverage

### Completeness Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `completitude.<attribute>` | float (0-1) | Fraction of non-null values for each attribute |

**Purpose:** Completeness metrics quantify the presence of required and optional attributes. Missing values in critical fields (e.g., `latitude`, `longitude`, `icao24`) indicate data quality issues that must be addressed during cleaning.

**Key attributes monitored:**
- `icao24`: Aircraft identifier (should be 1.0 at L1)
- `callsign`: Aircraft callsign (expected to have gaps, often 0.6-0.9)
- `latitude`, `longitude`: Position coordinates (should be 1.0 at L1)
- `altitude`: Altitude information (varies, often 0.8-0.95)
- `velocity`: Ground speed (varies, often 0.85-0.95)
- `vertical_rate`: Vertical speed (highly variable, often 0.6-0.8)

**Expected behavior:**
- L1 should show higher completeness for position-related fields after filtering
- Some attributes (e.g., `callsign`, `vertical_rate`) remain incomplete due to source limitations

### Data Quality Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `duplicate_records` | integer | Number of exactly duplicated rows |
| `reused_position` | integer | Vectors with identical (icao24, time_position, lat, lon) |
| `nulls.latitude` | integer | Count of missing latitude values |
| `nulls.longitude` | integer | Count of missing longitude values |
| `nulls.latlon` | integer | Count of vectors missing either coordinate |

**Purpose:** These metrics identify data anomalies caused by message retransmission, aggregation artifacts, or receiver errors.

**Expected behavior:**
- L0: Duplicates are common due to multiple receivers capturing the same transmission
- L1: `duplicate_records` and `reused_position` should be zero after cleaning
- L1: All `nulls.*` metrics should be zero (invalid positions are removed)

### Identifier Uniqueness

| Metric | Type | Description |
|--------|------|-------------|
| `uniqueness.icao24` | integer | Number of unique aircraft addresses |
| `uniqueness.callsign` | integer | Number of unique callsigns |

**Purpose:** Uniqueness metrics characterize the diversity of aircraft observed and help validate identifier consistency.

**Expected behavior:**
- `uniqueness.callsign` is typically lower than `uniqueness.icao24` because:
  - Callsigns may be reused across different days
  - Some aircraft do not broadcast callsigns
  - Same callsign may be used by different aircraft (though rare)

---

## Network Manager Flight Plans (FPLAN)

Flight plan metrics assess the quality and update patterns of pre-flight operational data.

### Volume and Update Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `num_messages` | integer | Total number of flight plan messages |
| `num_flights` | integer | Number of unique flight plans (`ifplId`) |
| `avg_messages_per_flight` | float | Mean number of messages per flight plan |

**Purpose:** These metrics characterize the message volume and update frequency. High `avg_messages_per_flight` indicates frequent flight plan amendments.

**Expected behavior:**
- L0: Multiple messages per flight are normal (amendments, updates)
- L1: Should retain only the last version of each flight plan, reducing message count
- `avg_messages_per_flight` typically ranges from 1.5 to 3.0 at L0

### Completeness Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `completitude.<attribute>` | float (0-1) | Fraction of non-null values for each attribute |

**Purpose:** Quantify attribute presence across all flight plan messages.

**Key attributes monitored:**
- `ifplId`: Flight plan identifier (always 1.0)
- `icao24`: Aircraft address (often incomplete in early messages, ~0.6-0.8)
- `callsign`: Aircraft callsign (typically high, ~0.95-1.0)
- `aerodromeOfDeparture`, `aerodromeOfDestination`: Airport codes (always 1.0)
- `operator`, `operatingOperator`: Airline codes (often 0.8-0.9)
- `aircraftType`: ICAO aircraft type (typically ~0.95)

**Expected behavior:**
- L1 completeness should improve due to attribute propagation across message versions
- Some attributes (`icao24`, `registrationMark`) may remain incomplete if never provided

### Uniqueness Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `uniqueness.<attribute>` | integer | Number of unique values per attribute |

**Purpose:** Assess identifier diversity and detect potential data anomalies.

**Note:** Excludes timestamp and duration fields which are inherently variable.

### Duplicate Detection

| Metric | Type | Description |
|--------|------|-------------|
| `duplicate_records` | integer | Exact duplicate messages (excluding `uuid`) |

**Purpose:** Identify message retransmission or processing errors.

**Expected behavior:**
- L0: Some duplicates may exist due to message republication
- L1: Should be zero after deduplication

### Temporal Coverage

| Metric | Type | Description |
|--------|------|-------------|
| `ranges.timestamp_min` | datetime | Earliest message timestamp |
| `ranges.timestamp_max` | datetime | Latest message timestamp |
| `ranges.offblockTime_min` | datetime | Earliest planned off-block time |
| `ranges.offblockTime_max` | datetime | Latest planned off-block time |

**Purpose:** Verify that temporal coverage aligns with the expected processing date and detect data partitioning issues.

**Expected behavior:**
- `timestamp` range spans the processing date ±several hours (messages may arrive early/late)
- `offblockTime` should primarily fall within the processing date ±1 day

### Geographic Distribution

| Metric | Type | Description |
|--------|------|-------------|
| `flights_airport_dep` | dict | Count of flights per departure airport (ICAO code) |
| `flights_airport_dest` | dict | Count of flights per destination airport (ICAO code) |
| `flights_airport_route` | dict | Count of flights per origin-destination pair |

**Purpose:** Characterize the geographic scope of the dataset and validate airport filtering.

**Expected behavior:**
- Distribution depends on configured airport filters
- Helps identify dominant routes and traffic patterns

---

## Network Manager Flight Data (FDATA)

Flight data metrics assess the quality of operational flight execution information.

### Volume and Update Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `num_messages` | integer | Total number of flight data messages |
| `num_flights` | integer | Number of unique flights (`ifplId`) |
| `avg_messages_per_flight` | float | Mean number of messages per flight |

**Purpose:** Similar to flight plans, these metrics characterize message volume and update patterns. Flight data messages are versioned and updated throughout flight execution.

**Expected behavior:**
- Higher `avg_messages_per_flight` than FPLAN (more frequent updates during flight)
- L1 should retain only the last version per flight

### Completeness Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `completitude.<attribute>` | float (0-1) | Fraction of non-null values for each attribute |

**Purpose:** Quantify the presence of operational timestamps and identifiers.

**Key attributes monitored:**
- `icao24`: Aircraft address (improves across message versions)
- `actualTakeOffTime`, `actualTimeOfArrival`: Actual operational times
- `estimatedTakeOffTime`, `estimatedTimeOfArrival`: Estimated times
- `calculatedTakeOffTime`, `calculatedTimeOfArrival`: System-calculated times
- `flightState`: Operational state (always present)

**Expected behavior:**
- Actual times (`actualTakeOffTime`, `actualTimeOfArrival`) are only present for flights that have reached those milestones
- Completeness increases across message versions as flight progresses
- L1 should show higher completeness for `icao24` after propagation

### Uniqueness Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `uniqueness.<attribute>` | integer | Number of unique values per attribute |

**Purpose:** Assess identifier and state diversity.

**Note:** Excludes timestamp and numeric fields which vary across messages.

### Duplicate Detection

| Metric | Type | Description |
|--------|------|-------------|
| `duplicate_records` | integer | Exact duplicate messages (excluding `uuid`) |

**Purpose:** Identify message retransmission or processing errors.

**Expected behavior:**
- L0: Some duplicates may exist
- L1: Should be zero after deduplication

### Temporal Coverage

| Metric | Type | Description |
|--------|------|-------------|
| `ranges.offblockTime_min` | datetime | Earliest estimated off-block time |
| `ranges.offblockTime_max` | datetime | Latest estimated off-block time |
| `ranges.actualTakeOffTime_min` | datetime | Earliest actual takeoff time |
| `ranges.actualTakeOffTime_max` | datetime | Latest actual takeoff time |
| `ranges.actualTimeOfArrival_min` | datetime | Earliest actual arrival time |
| `ranges.actualTimeOfArrival_max` | datetime | Latest actual arrival time |
| `ranges.estimatedTakeOffTime_min` | datetime | Earliest estimated takeoff |
| `ranges.estimatedTakeOffTime_max` | datetime | Latest estimated takeoff |
| `ranges.estimatedTimeOfArrival_min` | datetime | Earliest estimated arrival |
| `ranges.estimatedTimeOfArrival_max` | datetime | Latest estimated arrival |

**Purpose:** Verify temporal consistency and detect data partitioning issues.

**Expected behavior:**
- Actual times should span a wider range than the processing date (flights may start/end on adjacent days)
- Estimated times align more closely with the processing date

---

## Terminal Area Forecasts (TAF)

TAF metrics assess the quality and coverage of aviation weather forecasts.

### Volume and Coverage Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `num_reports` | integer | Total number of TAF forecast segments |
| `num_stations` | integer | Number of unique weather stations (airports) |

**Purpose:** Characterize the scale and geographic coverage of weather forecast data.

**Expected behavior:**
- `num_reports` includes base forecasts and all change segments (BECMG, TEMPO, AMD, COR)
- `num_stations` reflects the number of airports with TAF coverage

### Completeness Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `completitude.<attribute>` | float (0-1) | Fraction of non-null values for each attribute |

**Purpose:** Assess the presence of meteorological parameters.

**Key attributes monitored:**
- `station_id`: Airport code (always 1.0)
- `issue_time`, `valid_time_from`, `valid_time_to`: Temporal validity
- `wind_dir_degrees`, `wind_speed_kt`: Wind information
- `visibility_statute_mi`: Visibility
- `sky_cover`, `cloud_base_ft_agl`: Cloud information
- `wx_string`: Weather phenomena (varies, often sparse)
- `max_temp`, `min_temp`: Temperature forecasts (sparse, only in some reports)

**Expected behavior:**
- Base meteorological parameters (wind, visibility, clouds) have high completeness
- Optional parameters (temperature extremes, icing, turbulence) are sparse

### Uniqueness Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `uniqueness.<attribute>` | integer | Number of unique values per attribute |

**Purpose:** Characterize the diversity of forecast conditions and change types.

**Note:** Excludes nested list fields (`sky_condition`, `turbulence_condition`, `icing_condition`, `temperature`).

### Temporal Coverage

| Metric | Type | Description |
|--------|------|-------------|
| `ranges.min_temp` | integer | Minimum forecast temperature (°C) |
| `ranges.max_temp` | integer | Maximum forecast temperature (°C) |

**Purpose:** Provide a quick overview of temperature range across all forecasts in the period.

**Note:** These represent extremes across all forecasts, not a single forecast's min/max.

### Forecast Type Distribution

| Metric | Type | Description |
|--------|------|-------------|
| `reports_per_type` | dict | Count of reports by `change_indicator` |

**Purpose:** Characterize the distribution of forecast types.

**Forecast types:**
- `null`: Base forecast conditions
- `BECMG`: Permanent changes becoming established
- `TEMPO`: Temporary fluctuations
- `AMD`: Amendments to previous forecasts
- `COR`: Corrections to previous forecasts
- `PROB`: Probability forecasts (with `probability` field)

**Expected behavior:**
- Base forecasts (null) should be the most common
- TEMPO and BECMG are moderately common
- AMD and COR should be less frequent (issued only when needed)

---

## Interpretation Guidelines

### Comparing L0 vs L1 Metrics

Quality improvements should be observable when comparing L0 (raw) and L1 (cleaned) metrics:

**Expected improvements at L1:**
- **Completeness:** Higher for critical fields after cleaning and propagation
- **Duplicates:** Reduced to zero or near-zero
- **Volume:** Lower due to removal of invalid or redundant records
- **Uniqueness:** Should remain stable or increase slightly (no data loss)

**Anomalies requiring investigation:**
- Significant decrease in volume without corresponding quality improvement
- Decrease in uniqueness (indicates data loss)
- Persistence of duplicates at L1
- Decrease in completeness (indicates cleaning error)

### Metric Stability

Metrics should exhibit relative stability across consecutive processing dates for the same data source and geographic scope. Significant deviations may indicate:

- Changes in data extraction parameters
- Source system issues
- Processing pipeline errors
- Changes in aircraft/flight patterns (less likely to cause abrupt changes)

### Source-Specific Considerations

**OpenSky Vectors:**
- Completeness depends heavily on receiver coverage and aircraft equipment
- Volume varies with geographic filtering and time of day
- Callsign completeness inherently limited by aircraft broadcasting behavior

**Network Manager Flight Plans/Data:**
- Message volume depends on operational activity and amendment patterns
- ICAO24 completeness improves across message versions (early messages often missing)
- Geographic distribution reflects configured airport filters

**TAF:**
- Completeness of optional fields (temperature, icing, turbulence) is inherently low
- Report volume depends on forecast update frequency and amendment activity
- Weather phenomena (`wx_string`) presence varies with actual weather conditions

---

## Metrics File Format

Metrics are stored as JSON files with the following naming convention:

```
<source>.<level>.<date>.json
```

Examples:
- `vectors.L0.2023-07-03.json`
- `fPlan.L1.2023-07-03.json`
- `taf.L1.2023-07.json` (monthly aggregation)

Each file contains a JSON object with the metrics described above, along with metadata fields:

```json
{
  "date": "2023-07-03",
  "state": "clean",
  "level": "L1",
  "num_vectors": 3245678,
  "completitude": { ... },
  "uniqueness": { ... },
  ...
}
```
