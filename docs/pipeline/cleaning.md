# Data Cleaning (L1)

This document describes the **data cleaning stage (L1)** of the pipeline. At this level, each data source is processed **independently**, transforming raw inputs (L0) into standardized, validated and analysis-ready datasets, without performing cross-source integration.

Details about the structure, semantics and known issues of each raw data source are documented separately under `docs/raw_data/`.

<figure><p align="center">
<img src="../assets/cleaning_pipeline.png" width="700"  alt=""></p>
<figcaption><p align="center">Overview of the cleaning pipeline.</p></figcaption>
</figure>

---

## Scope of L1 Cleaning

The goal of L1 is to produce **clean, consistent datasets per source**, ensuring that:

- schemas are normalized and stable
- timestamps and identifiers are consistent
- obvious inconsistencies and duplicates are removed
- data is stored in an efficient columnar format (parquet)

In particular, L1 cleaning typically includes the
following operations.

### Schema normalization

- Extraction of relevant attributes from nested structures
- Renaming columns using consistent naming conventions
- Explicit typing of columns using pandas nullable / pyarrow-backed dtypes
- Removal of unused attributes

### Time normalization

- Conversion of timestamps to UNIX epoch seconds
- Explicit handling of time zones and offsets
- Removal of invalid or missing time values

### String normalization

- Standardization of string attributes to their expected formats
- Trimming whitespace and enforcing uppercase where appropriate
- Identification of empty strings as null values

### Duplicate handling

- Removal of duplicate messages or records
- Definition of source-specific uniqueness criteria
- Preservation of the most informative or recent version when applicable

### Message ordering and propagation

- Records are ordered using source-specific versioning or timestamps
- Selected attributes are forward-filled within logical groups
  (e.g. flight-level identifiers)

---

## OpenSky Network – State Vectors

This section describes the cleaning operations applied to OpenSky state vector data. These operations are motivated by the known limitations and inconsistencies of ADS-B based surveillance data, as documented in the OpenSky Network description.

### Schema normalization

- Removal of unused attributes that are not used downstream (e.g. spi or position source) or empty (e.g. sensor metadata).
- Timestamps are added timezone information and interpreted as UNIX time in seconds.

### Removal of invalid observations

Individual state vectors are removed if they contain invalid or inconsistent values
that make them unusable for trajectory reconstruction. An observation is discarded if any of the following conditions hold:

- Missing aircraft identifier (`icao24`).
- Missing latitude or longitude.
- Latitude outside the valid range [-90°, 90°].
- Longitude outside the valid range [-180°, 180°].

These checks eliminate corrupted or incomplete observations that cannot be reliably
placed in space or whose source is unknown.

### Duplicate detection

Duplicate observations may occur in the raw data due to repeated aggregation or message reconstruction. Only the first instance of each duplicated observation is retained. Duplicates are identified and removed based on the combination of:

- Aircraft identifier (`icao24`)
- Position timestamp (`time_position`)
- Latitude
- Longitude

### Text normalization

- Callsign values that are set to empty strings are replaced by explicit missing values.

### Temporal ordering

State vectors are sorted by aircraft identifier and position timestamp.

This ordering ensures that all subsequent trajectory-level processing operates on temporally consistent sequences.

### Derived attributes

Two additional attributes are introduced to simplify downstream processing:

- `timestamp`: defined as the position timestamp (`time_position`), and used as the reference temporal coordinate for the state vector.
- `altitude`: defined as the geometric altitude (`geo_altitude`), used as the default altitude reference when available.



## Network Manager – Flight Plans (FPLAN)

This section describes the cleaning operations applied to Network Manager Flight Plan data to produce a consistent L1 dataset.

### Schema extraction and flattening

Raw Flight Plan messages are provided as deeply nested JSON records. Relevant attributes are extracted using explicit attribute paths and transformed into a flat tabular structure.

### Data type normalization

- All timestamps are converted to UNIX time in seconds and localized to UTC timezone.
- Duration fields are converted to integer minutes.

### Message ordering and deduplication

- Messages are sorted by flight identifier and message timestamp.
- Duplicate messages are removed based on all attributes except the unique message identifier.

### Attribute propagation

Some attributes may be missing in early Flight Plan messages and only appear in later updates. For each flight, missing values in selected attributes are forward-filled to ensure that the final flight plan contains the most complete information available.



## Network Manager – Flight Data (FDATA)

This section describes the cleaning operations applied to Network Manager Flight Data.

### Schema extraction and concatenation

Flight Data messages are extracted from multiple JSON files and combined into a single tabular dataset per day.

### Attribute propagation

Missing aircraft identifiers and key operational timestamps are propagated across
versions within the same flight.

---

## Relationship with Later Stages

- **L2 (Integration)** combines cleaned L1 datasets across sources
- **L3 (Trajectories)** produces fully cleaned and temporally consistent trajectories

Keeping L1 cleaning strictly source-local simplifies validation and makes later stages more robust.