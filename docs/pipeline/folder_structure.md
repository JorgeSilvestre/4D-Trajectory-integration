# Folder Structure and Data Maturity Levels

This repository follows a structured data layout based on **data maturity levels**,
from raw source data (L0) to fully cleaned and enriched trajectories (L3). Within each directory, data is organized per source (L0 and L1) or represented entity (L2 and L3), and partitioned by date unless stated otherwise.


Each level is reflected consistently in both the filesystem layout and the codebase (see `trajectoryIntegration/paths.py`).

---

## Project-level directories

```bash
project_root/
├── trajectoryIntegration/ # Core processing pipelines
├── data/                  # All datasets, organized by maturity level (L0–L3)
├── reports/               # Quality metrics and logs
└── docs/                  # Project documentation
```
---

## Package directory (`trajectoryIntegration/`)

```bash
project_root/
├── data_cleaning/         # Data cleaning modules (L0 → L1)
├── data_extraction/       # Data extraction modules (sources → L0)
├── data_integration/      # Data cleaning modules (L1 → L2)
├── quality_metrics/       # Data quality metrics calculation modules
├── trajectory_processing/ # Trajectory cleaning modules (L2 → L3)
├── params.py       # Parameter definitions 
├── paths.py        # Files and folders path definitions 
├── trajectory.py   # Trajectory class 
└── utils.py        # Common utilities for all modules 
```

---

## Data directory (`data/`)

All datasets are stored under `data/`, organized by **data maturity level**.

### L0 — Raw data (`data/L0/`)

L0 contains **raw, unmodified data** as obtained from external sources.
No cleaning, normalization or semantic consolidation is applied at this stage.

```bash
data/L0/
├── nmFPlan/            # Network Manager Flight Plan messages (JSON)
├── nmFData/            # Network Manager Flight Data messages (JSON)
├── nmADRR/             # Eurocontrol ADRR Flights (CSV)
├── openskyFlights/     # OpenSky aggregated flight events (JSON)
├── openskyVectorsJson/ # OpenSky raw state vectors (JSON)
├── openskyVectors/     # OpenSky raw state vectors (parquet)
├── taf/                # Terminal Aerodrome Forecasts (parquet)
├── airports/           # Airport reference data (CSV)
├── runways/            # Runway reference data (CSV)
└── airlines/           # Airline reference data (CSV)
```

### L1 — Cleaned individual sources (`data/L1/`)

L1 corresponds to **source-level cleaned data** in parquet file format.
At this level, each dataset is processed independently: schema normalization, basic filtering and validation, and semantic consolidation within a single source.

```bash
data/L1/
├── nmFPlan/        # Cleaned NM Flight Plans
├── nmFData/        # Cleaned NM Flight Data
├── nmADRR/         # Cleaned Eurocontrol ADRR Flights
├── openskyFlights/ # Cleaned OpenSky flights
├── openskyVectors/ # Cleaned OpenSky state vectors
├── taf/            # Processed TAF data (monthly)
└── airports/       # Normalized airport reference dataset
```

### L2 — Integrated data (`data/L2/`)

L2 contains **integrated datasets**, where information from multiple sources is combined.

```bash
data/L2/
├── nmFlights/      # Consolidated NM flights
├── nmTrajectories/ # Integrated NM trajectories
└── taf/            # Consolidated weather forecasts at the airport
```

### L3 — Clean and enrich trajectories (`data/L3/`)

L3 represents the **final trajectory products**, ready for analysis, visualization and evaluation. At this level, the main issues affecting data quality in trahectories have been tackled (incorrect timestamps, outliers, etc.), and the weather forecast information has been integrated with the trajectory.

```bash
data/L3/
└── nmTrajectories/ # Final cleaned NM trajectories
```

---

## Reports directory (`reports/`)

The `reports/` directory contains **quality metrics and diagnostic outputs** generated during processing. Metrics are also organized by maturity level.

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

---

## Relationship with the codebase

All filesystem paths are centrally defined in `trajectoryIntegration/paths.py`.
Processing modules rely exclusively on these definitions to ensure consistency
between code and directory structure.

The naming convention used throughout the repository explicitly reflects:
- data source (e.g. NM, OpenSky)
- entity type (flights, vectors, trajectories)
- maturity level (L0–L3)