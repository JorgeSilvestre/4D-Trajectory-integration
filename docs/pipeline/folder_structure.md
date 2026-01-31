# Folder Structure and Data Maturity Levels

This repository follows a structured data layout based on **data maturity levels**,
from raw source data (L0) to fully cleaned and integrated trajectories (L3).

Each level corresponds to a specific processing stage in the trajectory construction
pipeline and is reflected consistently in both the filesystem layout and the codebase
(see `trajectoryIntegration/paths.py`).

---

## Project-level directories

```bash
project_root/
├── data/                  # All datasets, organized by maturity level (L0–L3)
├── reports/               # Quality metrics and logs
├── docs/                  # Project documentation
└── trajectoryIntegration/ # Core processing pipelines
```


## Data directory (`data/`)

All datasets are stored under `data/`, organized by **data maturity level**.

### L0 — Raw data (`data/L0/`)

L0 contains **raw, unmodified data** as obtained from external sources.
No cleaning, normalization or semantic consolidation is applied at this stage.

```bash
data/L0/
├── nmFPlan/            # Network Manager Flight Plan messages (JSON)
├── nmFData/            # Network Manager Flight Data messages (JSON)
├── openskyFlights/     # OpenSky aggregated flight events (JSON)
├── openskyVectorsJson/ # OpenSky raw state vectors (JSON)
├── openskyVectors/     # OpenSky raw state vectors (parquet)
├── taf/                # Terminal Aerodrome Forecasts
├── airports/           # Airport reference data
├── runways/            # Runway reference data
└── airlines/           # Airline reference data
```

L0 data is assumed to be **source-dependent**, potentially incomplete, and not suitable
for direct integration.

---

### L1 — Cleaned individual sources (`data/L1/`)

L1 corresponds to **source-level cleaned data**.
At this level, each dataset is processed independently:

- schema normalization
- basic filtering and validation
- semantic consolidation within a single source
- conversion to efficient parquet format

```bash
data/L1/
├── nmFPlan/        # Cleaned NM Flight Plans (parquet)
├── nmFData/        # Cleaned NM Flight Data (parquet)
├── nmFlights/      # Consolidated NM flights
├── openskyFlights/ # Cleaned OpenSky flight events
├── openskyVectors/ # Cleaned OpenSky state vectors
├── taf/            # Processed TAF data
└── airports/
    └── airports.parquet # Normalized airport reference dataset
```

No cross-source integration occurs at this stage.

---

### L2 — Integrated data (`data/L2/`)

L2 contains **integrated datasets**, where information from multiple sources is combined.

Typical operations include:
- joining flight-level and vector-level data
- aligning trajectories across sources
- resolving inconsistencies between NM and OpenSky data

```bash
data/L2/
├── nmTrajectories/       # Intermediate NM trajectories
├── openskyVectorsJoined/ # Joined OpenSky vectors
├── openskyFlightsJoined/ # Joined OpenSky flights
├── nmVectorsJoined/      # Joined NM vectors
└── nmFlightsJoined/      # Joined NM flights
```

Some intermediate artifacts may not be persisted if trajectories are directly generated.

---

### L3 — Clean trajectories (`data/L3/`)

L3 represents the **final trajectory products**, ready for analysis, visualization and
evaluation.

At this level:
- trajectories are temporally consistent
- sorting and interpolation have been applied
- outliers and artifacts have been removed

```bash
data/L3/
└── nmTrajectories/ # Final cleaned NM trajectories
```

These datasets are considered stable inputs for downstream tasks.

---

## Reports directory (`reports/`)

The `reports/` directory contains **quality metrics and diagnostic outputs** generated
during processing.

Metrics are also organized by maturity level.

```bash
reports/
├── L0_fplan/
├── L0_fdata/
├── L0_vectors/
├── L0_taf/
├── L1_fplan/
├── L1_fdata/
├── L1_vectors/
├── L1_taf/
├── L2_trajectories/
├── L3_trajectories/
├── L2_integration_metrics/
└── L3_sort_metrics/
```

These reports support:
- data quality assessment
- pipeline validation
- comparison across processing stages

---

## Relationship with the codebase

All filesystem paths are centrally defined in `trajectoryIntegration/paths.py`.
Processing modules rely exclusively on these definitions to ensure consistency
between code and directory structure.

The naming convention used throughout the repository explicitly reflects:
- data source (e.g. NM, OpenSky)
- entity type (flights, vectors, trajectories)
- maturity level (L0–L3)