# Data Cleaning (L1)

This document specifies the **L1 cleaning stage** of the pipeline. At this stage, each source is processed **independently** to transform raw inputs (L0) into standardized and validated datasets, without cross-source joins.

Raw-source structure and semantics are documented under `docs/raw_data/`.

<figure><p align="center">
<img src="../assets/cleaning_pipeline.png" width="700"  alt=""></p>
<figcaption><p align="center">Overview of the cleaning pipeline.</p></figcaption>
</figure>

---

## Scope of L1 cleaning

L1 cleaning produces source-local datasets with stable schema and consistent semantics:

- stable and normalized column names,
- validated identifiers and temporal fields,
- removal of obvious invalid records and duplicates,
- parquet output for efficient downstream processing.

Typical operations include:

### Schema normalization

- Flattening/extraction of relevant attributes.
- Source-to-canonical renaming.
- Explicit nullable typing (pandas/pyarrow where applicable).
- Removal of unused attributes.

### Time normalization

- Standardization of timestamp representation.
- Explicit UTC localization when required.
- Removal or filtering of invalid temporal values.

### String normalization

- Trimming and case standardization.
- Conversion of empty strings to nulls.

### Duplicate handling

- Source-specific duplicate definitions.
- Deterministic retention policy (e.g., first occurrence).

### Ordering and propagation

- Deterministic ordering using source timestamps/version fields.
- Forward propagation of selected attributes within entity groups when required.

---

## OpenSky Network – State Vectors

This section documents the operations implemented in `trajectoryIntegration/data_cleaning/surveillance.py`.

### Schema normalization

- Drop unused OpenSky attributes: `sensors`, `spi`, `position_source`, `origin_country`.
- Rename OpenSky fields to canonical names (e.g., `hexid` → `icao24`, `track` → `true_track`).
- Localize `time_position` and `last_contact` to UTC and truncate to second resolution.
- Enforce selected dtypes (e.g., `squawk` as `string[pyarrow]`).

### Invalid observation filtering

Discard records when any of the following holds:

- Missing `icao24`.
- Missing `latitude` or `longitude`.
- `latitude ∉ [-90, 90]`.
- `longitude ∉ [-180, 180]`.

### Duplicate detection

Remove duplicates using key:

- `icao24`,
- `time_position`,
- `latitude`,
- `longitude`.

### Text normalization

- Trim trailing blanks from `callsign`.
- Discard callsigns containing embedded blanks.
- Uppercase `icao24` and `callsign`.
- Replace empty callsigns with null values.

### Ordering

Sort state vectors by:

1. `icao24`,
2. `time_position`.

### Derived attributes

- `timestamp := time_position`
- `altitude := geo_altitude`

### Output contract

L1 OpenSky vectors are emitted with fixed column ordering:

`timestamp`, `icao24`, `callsign`, `time_position`, `last_contact`, `latitude`, `longitude`, `altitude`, `baro_altitude`, `geo_altitude`, `velocity`, `vertical_rate`, `true_track`, `on_ground`, `squawk`.

---

## Network Manager – Flight Plans (FPLAN)

### Schema extraction and flattening

Raw Flight Plan JSON messages are flattened using explicit attribute paths.

### Type normalization

- Timestamps are normalized to UTC-aware UNIX-time semantics.
- Duration-like fields are converted to integer minutes.

### Ordering and deduplication

- Sort by flight identifier and message timestamp.
- Remove duplicates excluding the unique message identifier.

### Attribute propagation

Within each flight, selected attributes are forward-filled across message versions.

---

## Network Manager – Flight Data (FDATA)

### Schema extraction and concatenation

Flight Data records are extracted from multiple JSON files and concatenated into one daily table.

### Attribute propagation

Aircraft identifiers and selected operational timestamps are propagated across versions of the same flight.

---

## Relationship with later stages

- **L2 (Integration)** combines L1 datasets across sources.
- **L3 (Trajectories)** builds temporally coherent trajectories with additional trajectory-level cleaning.

Keeping L1 strictly source-local improves traceability, validation, and robustness of integration.
