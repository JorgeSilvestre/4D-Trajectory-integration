# Data Cleaning (L1)

This document describes the **data cleaning stage (L1)** of the pipeline.

At this level, each data source is processed **independently**, transforming raw inputs (L0) into standardized, validated and analysis-ready datasets, without performing cross-source integration.

Details about the structure, semantics and known issues of each raw data source are documented separately under `docs/raw_data/`.

---

## Scope of L1 Cleaning

The goal of L1 is to produce **clean, consistent datasets per source**, ensuring that:

- schemas are normalized and stable
- timestamps and identifiers are consistent
- obvious inconsistencies and duplicates are removed
- data is stored in an efficient columnar format (parquet)

L1 cleaning **does not attempt** to:
- merge data from different sources
- reconstruct trajectories
- resolve semantic conflicts between sources

These operations are deferred to L2 and L3.

---

## Common Cleaning Operations

Although each source requires specific handling, L1 cleaning typically includes the
following operations.

### Schema normalization

- Extraction of relevant attributes from nested structures
- Renaming columns using consistent naming conventions
- Explicit typing of columns using pandas nullable / pyarrow-backed dtypes

---

### Time normalization

- Conversion of timestamps to UNIX epoch seconds
- Explicit handling of time zones and offsets
- Removal or propagation of invalid or missing time values when applicable

---

### Identifier normalization

- Standardization of identifiers such as:
  - `icao24`
  - `callsign`
  - flight or message identifiers
- Trimming whitespace and enforcing uppercase where appropriate

---

### Duplicate handling

- Removal of duplicate messages or records
- Definition of source-specific uniqueness criteria
- Preservation of the most informative or recent version when applicable

---

### Message ordering and propagation

For sources that provide incremental updates (e.g. NM messages):

- Records are ordered using source-specific versioning or timestamps
- Selected attributes are forward-filled within logical groups
  (e.g. flight-level identifiers)

---

### Output format

All L1 datasets are written to disk using:

- Apache Parquet format
- Explicit schemas
- One dataset per source and per day (when applicable)

This ensures efficient downstream processing and reproducibility.

---

## Source-specific Cleaning Modules

Each source has a dedicated cleaning module under:
`trajectoryIntegration/data_cleaning/`

Typical responsibilities of these modules include:

- parsing raw input files
- applying source-specific schema changes
- performing L1-level cleaning operations
- writing cleaned outputs to the corresponding `data/L1/` directory

Refer to the source-specific documentation under `docs/raw_data/` for details on raw
formats and semantics.

## OpenSky Network – State Vectors

This section describes the cleaning operations applied to OpenSky state vector data.
These operations are motivated by the known limitations and inconsistencies of ADS-B
based surveillance data, as documented in the OpenSky Network description.

### Schema normalization

The raw OpenSky state vector data includes attributes that are not required for
trajectory reconstruction or are inconsistent across records.

The following operations are applied:

- Removal of unused attributes that are not used downstream (e.g. sensor metadata).
- Renaming of selected attributes to ensure a consistent naming convention across
  data sources.
- Explicit casting of all columns to well-defined data types.

Timestamps are converted to UNIX time in seconds and stored as integer values.
Geospatial and kinematic variables are stored using floating-point precision.

### Removal of invalid observations

Individual state vectors are removed if they contain invalid or inconsistent values
that make them unusable for trajectory reconstruction.

An observation is discarded if any of the following conditions hold:

- Missing aircraft identifier (`icao24`).
- Missing latitude or longitude.
- Latitude outside the valid range [-90°, 90°].
- Longitude outside the valid range [-180°, 180°].

These checks eliminate corrupted or incomplete observations that cannot be reliably
placed in space.

### Duplicate detection

Duplicate observations may occur in the raw data due to repeated aggregation or
message reconstruction.

Duplicates are identified and removed based on the combination of:

- Aircraft identifier (`icao24`)
- Position timestamp (`time_position`)
- Latitude
- Longitude

Only one instance of each duplicated observation is retained.

### Text normalization

Text-based attributes are normalized to ensure consistent formatting:

- Leading and trailing whitespace is removed.
- All string values are converted to uppercase.
- Empty strings are replaced by explicit missing values.

This normalization is applied in particular to aircraft identifiers and callsigns,
which are frequently affected by formatting inconsistencies.

### Temporal ordering

State vectors are sorted by aircraft identifier and position timestamp.

This ordering ensures that all subsequent trajectory-level processing operates on
temporally consistent sequences.

### Derived attributes

Two additional attributes are introduced to simplify downstream processing:

- `timestamp`: defined as the position timestamp (`time_position`), and used as the
  reference temporal coordinate for the state vector.
- `altitude`: defined as the geometric altitude (`geo_altitude`), used as the default
  altitude reference when available.

No interpolation or estimation is performed at this stage.

### Output guarantees

After cleaning, the OpenSky state vector dataset (L1) satisfies the following
conditions:

- All observations have valid spatial coordinates.
- Aircraft identifiers are consistently formatted.
- Duplicate observations are removed.
- Data types are explicitly defined.
- Observations are temporally ordered per aircraft.

Remaining issues related to irregular sampling, missing values in non-essential
attributes, or surveillance coverage limitations are intentionally preserved and
handled in later stages of the pipeline.

## Network Manager – Flight Plans (FPLAN)

This section describes the cleaning operations applied to Network Manager Flight Plan
data to produce a consistent L1 dataset.

### Schema extraction and flattening

Raw Flight Plan messages are provided as deeply nested JSON records.

Relevant attributes are extracted using explicit attribute paths and transformed into
a flat tabular structure. Only attributes required for downstream processing are
retained.

### Data type normalization

- All timestamps are converted to UNIX time in seconds.
- Duration fields are converted to integer minutes.
- Text-based attributes are stored as strings with explicit missing values.

### Message ordering and deduplication

- Messages are sorted by flight identifier and message timestamp.
- Duplicate messages are removed based on all attributes except the unique message
  identifier.

### Attribute propagation

Some attributes may be missing in early Flight Plan messages and only appear in later
updates.

For each flight, missing values in selected attributes are forward-filled to ensure
that the final flight plan contains the most complete information available.

### Output guarantees

After cleaning, the Flight Plan dataset satisfies the following conditions:

- One consolidated flight plan per flight.
- Explicit and consistent data types.
- Complete attribute set when available in the source data.

## Network Manager – Flight Data (FDATA)

This section describes the cleaning operations applied to Network Manager Flight Data.

### Schema extraction and concatenation

Flight Data messages are extracted from multiple JSON files and combined into a single
tabular dataset per day.

### Schema extraction and concatenation

Flight Data messages are extracted from multiple JSON files and combined into a single
tabular dataset per day.

### Attribute propagation

Missing aircraft identifiers and key operational timestamps are propagated across
versions within the same flight.

### Attribute propagation

Missing aircraft identifiers and key operational timestamps are propagated across
versions within the same flight.


---

## Relationship with Later Stages

- **L2 (Integration)** combines cleaned L1 datasets across sources
- **L3 (Trajectories)** produces fully cleaned and temporally consistent trajectories

Keeping L1 cleaning strictly source-local simplifies validation and makes later stages
more robust.