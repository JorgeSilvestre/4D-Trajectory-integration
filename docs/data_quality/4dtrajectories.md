# Data Quality Metrics for 4D Trajectories

This document describes the quality metrics computed for integrated 4D trajectories at L2 (raw trajectories) and L3 (cleaned trajectories) maturity levels.

Trajectory quality metrics are automatically generated per trajectory and stored as JSON files in the `reports/` directory:

```
reports/
├── L2_trajectories/       # Raw integrated trajectories
│   └── tray.{date}.{ifplId}.json
└── L3_trajectories/       # Cleaned and sorted trajectories
    └── tray.{date}.{ifplId}.json
```

---

## Overview

Unlike individual source metrics, trajectory metrics assess the quality of **integrated and processed** flight trajectories that combine:

- Network Manager flight plan and flight data (metadata)
- OpenSky state vectors (4D position observations)
- Trajectory processing operations (sorting, outlier removal, interpolation)

These metrics evaluate:

- **Completeness**: Presence of required attributes in state vectors
- **Semantic validity**: Alignment with expected flight behavior
- **Coverage**: Temporal and spatial extent of observations
- **Continuity**: Temporal gaps and segmentation
- **Processing quality** (L3 only): Impact of sorting and cleaning operations

---

## Metric Categories

| Category | L2 (Raw) | L3 (Cleaned) | Description |
|----------|----------|--------------|-------------|
| **Generic** | ✓ | ✓ | Basic trajectory characteristics |
| **Completeness** | ✓ | ✓ | Attribute presence in state vectors |
| **Semantic** | ✓ | ✓ | Alignment with flight metadata |
| **Coverage** | ✓ | ✓ | Temporal and spatial extent |
| **Continuity** | ✓ | ✓ | Gap analysis and segmentation |
| **Processing** | - | ✓ | Sorting and timestamp adjustments |

---

## Generic Metrics

Generic metrics characterize the basic properties of the trajectory.

| Metric | Type | Description |
|--------|------|-------------|
| `ifplId` | string | Network Manager flight plan identifier |
| `num_vectors` | integer | Total number of state vectors in the trajectory |
| `duration` | integer | Time span from first to last vector (seconds) |
| `distance` | float | Total path length computed using haversine distance (miles) |

**Purpose:** These metrics provide a high-level summary of trajectory scale and extent.

**Expected behavior:**
- `num_vectors`: Typically ranges from hundreds to several thousand depending on flight duration and surveillance coverage
- `duration`: Should align approximately with the difference between `actualTakeOffTime` and `actualTimeOfArrival` from flight metadata
- `distance`: Should be comparable to the great circle distance between origin and destination airports, typically higher due to routing and airspace constraints

**Interpretation:**
- Very low `num_vectors` (< 200) may indicate incomplete surveillance coverage
- `distance` significantly lower than airport separation suggests missing flight segments
- `duration` much larger than expected flight time may indicate data from multiple flights incorrectly merged

---

## Completeness Metrics

Completeness metrics quantify the presence of attributes in state vectors.

| Metric | Type | Description |
|--------|------|-------------|
| `completitude.<attribute>` | float (0-1) | Fraction of state vectors with non-null values for each attribute |

**Purpose:** Assess the availability of kinematic and metadata attributes required for trajectory analysis.

**Monitored attributes:**
- `timestamp`: Position timestamp (should be 1.0)
- `latitude`, `longitude`: Geographic coordinates (should be 1.0)
- `baro_altitude`, `geo_altitude`: Altitude measurements
- `altitude`: Derived altitude field (should be 1.0 after processing)
- `callsign`: Aircraft callsign
- `vertical_rate`: Vertical speed
- `velocity`: Ground speed
- `true_track`: True track angle

**Expected behavior:**
- Position fields (`timestamp`, `latitude`, `longitude`) should have completeness = 1.0 after L2 integration
- Kinematic fields (`velocity`, `vertical_rate`, `true_track`) typically show 0.7-0.95 completeness
- `callsign` completeness varies (0.5-0.9) depending on aircraft broadcasting behavior

**Interpretation:**
- Low completeness for altitude or velocity may limit certain trajectory analyses
- Completeness should remain stable or improve from L2 to L3

---

## Semantic Metrics

Semantic metrics validate the trajectory against expected flight behavior and metadata.

### Airport Proximity

| Metric | Type | Description |
|--------|------|-------------|
| `distance_to_origin` | float | Distance from first trajectory point to departure airport (miles) |
| `distance_to_destination` | float | Distance from last trajectory point to destination airport (miles) |
| `missing_start` | boolean | True if `distance_to_origin` exceeds threshold |
| `missing_end` | boolean | True if `distance_to_destination` exceeds threshold |

**Purpose:** Detect missing departure or arrival segments.

**Threshold:** `THRESHOLD_DISTANCE_TO_AIRPORT` = 50 miles

**Expected behavior:**
- Trajectories should ideally start and end near their respective airports
- `missing_start` or `missing_end` = true indicates incomplete surveillance coverage near airports

**Interpretation:**
- Missing start: Surveillance began after takeoff or departure segment lost
- Missing end: Surveillance ended before landing or arrival segment lost
- Both common for flights at the edge of surveillance coverage area

### Flight Duration Consistency

| Metric | Type | Description |
|--------|------|-------------|
| `airports_distance` | float | Great circle distance between origin and destination airports (miles) |
| `effective_flight_time` | integer | Duration between `actualTakeOffTime` and `actualTimeOfArrival` from flight metadata (seconds) |

**Purpose:** Provide reference values for trajectory validation.

**Interpretation:**
- `airports_distance` represents minimum possible flight distance
- Actual trajectory `distance` should be greater than `airports_distance` due to routing
- `duration` should align closely with `effective_flight_time` (±10-20%)

### Last Altitude Before Ground

| Metric | Type | Description |
|--------|------|-------------|
| `last_altitude_before_ground` | float | Altitude of the last airborne state vector (feet) |

**Purpose:** Assess completeness of the landing segment.

**Expected behavior:**
- Should be close to destination airport elevation for complete trajectories
- High values indicate missing final descent segment
- Null value indicates no airborne vectors or all vectors marked as on_ground

---

## Coverage and Density Metrics

Coverage metrics characterize the temporal and spatial sampling of the trajectory.

### Temporal Coverage

| Metric | Type | Description |
|--------|------|-------------|
| `mean_granularity` | float | Mean time interval between consecutive state vectors (seconds) |
| `std_granularity` | float | Standard deviation of time intervals (seconds) |

**Purpose:** Assess temporal sampling regularity and identify irregular coverage patterns.

**Expected behavior:**
- `mean_granularity`: Typically 5-15 seconds for ADS-B surveillance
- `std_granularity`: Should be relatively low (< 20 seconds) for consistent coverage
- High standard deviation indicates heterogeneous sampling rates

**Interpretation:**
- Very high mean granularity (> 30 seconds) suggests sparse coverage
- High variability suggests changing surveillance quality during flight

### Spatial Coverage

| Metric | Type | Description |
|--------|------|-------------|
| `mean_granularity_distance` | float | Mean distance between consecutive state vectors (miles) |
| `std_granularity_distance` | float | Standard deviation of distances (miles) |
| `density` | float | State vectors per mile (`num_vectors / distance`) |

**Purpose:** Assess spatial sampling density and uniformity.

**Expected behavior:**
- `mean_granularity_distance`: Typically 0.5-3 miles depending on aircraft speed and sampling rate
- `density`: Typically 10-100 vectors per mile for well-covered flights
- Higher density indicates better spatial resolution

**Interpretation:**
- Very low density (< 5 vectors/mile) may indicate significant gaps
- High variability in granularity_distance suggests non-uniform coverage

---

## Continuity Metrics

Continuity metrics identify and characterize temporal gaps in the trajectory.

### Gap Identification

| Metric | Type | Description |
|--------|------|-------------|
| `gaps` | list[dict] | List of temporal gaps exceeding `THRESHOLD_GAP_TIME` |
| `num_gaps` | integer | Number of identified gaps |

**Gap object structure:**
```json
{
  "index": 245,      // Index of the vector after the gap
  "size": 420        // Gap duration in seconds
}
```

**Threshold:** `THRESHOLD_GAP_TIME` = 300 seconds (5 minutes)

**Purpose:** Identify loss of surveillance coverage during the flight.

**Expected behavior:**
- Flights within dense surveillance coverage: 0-2 gaps
- Flights crossing coverage boundaries: 3-10 gaps
- Each gap represents a period where no state vectors were observed

### Segmentation

| Metric | Type | Description |
|--------|------|-------------|
| `segments` | list[dict] | Continuous trajectory segments between gaps |
| `num_segments` | integer | Number of continuous segments |

**Segment object structure:**
```json
{
  "start": 0,        // Index of first vector in segment
  "end": 244         // Index of last vector in segment
}
```

**Purpose:** Partition the trajectory into continuous observation periods.

**Expected behavior:**
- `num_segments = num_gaps + 1`
- Single-segment trajectories indicate continuous surveillance
- Multi-segment trajectories may require segment-by-segment analysis

### Temporal Classification

| Metric | Type | Description |
|--------|------|-------------|
| `gap_time` | integer | Total time in gaps > `THRESHOLD_GAP_TIME` (seconds) |
| `gap_ratio` | float | Fraction of flight duration in gaps (`gap_time / duration`) |
| `continuity_time` | integer | Total time with intervals ≤ `THRESHOLD_CONTINUITY` (seconds) |
| `continuity_ratio` | float | Fraction of flight with high continuity (`continuity_time / duration`) |
| `discontinuity_time` | integer | Total time with intervals between continuity and gap thresholds (seconds) |
| `discontinuity_ratio` | float | Fraction in discontinuous regime (`discontinuity_time / duration`) |

**Thresholds:**
- `THRESHOLD_CONTINUITY` = 30 seconds (high-quality continuous coverage)
- `THRESHOLD_GAP_TIME` = 300 seconds (significant gap)

**Purpose:** Quantify the temporal quality of surveillance coverage.

**Expected behavior:**
- High `continuity_ratio` (> 0.7) indicates good sustained coverage
- Low `gap_ratio` (< 0.2) indicates few major coverage losses
- The three ratios should sum to approximately 1.0:
  - `continuity_ratio + discontinuity_ratio + gap_ratio ≈ 1.0`

**Interpretation:**
- `continuity_ratio > 0.8`: Excellent coverage quality
- `gap_ratio > 0.3`: Significant coverage gaps, may affect analysis
- High `discontinuity_ratio`: Variable coverage quality

---

## Processing Metrics (L3 Only)

Processing metrics quantify the impact of trajectory cleaning and sorting operations applied at L3.

| Metric | Type | Description |
|--------|------|-------------|
| `sorted_vectors` | integer | Number of state vectors reordered during sorting |
| `timestamp_variation` | timedelta | Mean timestamp adjustment for reordered vectors |

**Purpose:** Assess the extent of reordering operations performed during L3 processing.

**Expected behavior:**
- `sorted_vectors`: Should be a small fraction of total vectors (< 10%)
- `timestamp_variation`: Should be small (typically < 30 seconds)

**Interpretation:**
- High `sorted_vectors` count indicates significant temporal disorder in L2 data
- Large `timestamp_variation` suggests aggressive timestamp interpolation
- These metrics help validate the sorting algorithm's behavior

---

## Threshold Reference

The following thresholds are used in trajectory metric calculations:

| Threshold | Value | Purpose |
|-----------|-------|---------|
| `THRESHOLD_DISTANCE_TO_AIRPORT` | 50 miles | Define proximity to airports for start/end detection |
| `THRESHOLD_GAP_TIME` | 300 seconds | Minimum duration to classify as a significant gap |
| `THRESHOLD_CONTINUITY` | 30 seconds | Maximum interval for high-quality continuous coverage |

These thresholds are defined in `trajectoryIntegration/params.py` and are included in the metrics output for reference:

```json
{
  "thresholds": {
    "THRESHOLD_DISTANCE_TO_AIRPORT": 50,
    "THRESHOLD_GAP_TIME": 300,
    "THRESHOLD_CONTINUITY": 30
  }
}
```

---

## Usage Patterns

### Accessing Trajectory Metrics

Metrics are stored per trajectory with the naming convention:

```
tray.{date}.{ifplId}.json
```

Example: `tray.2023-07-03.AT02603928.json`

### Typical Analysis Workflows

#### 1. Identify Incomplete Trajectories

```python
import json
from pathlib import Path

def load_trajectory_metrics(date, ifplId, level='L2'):
    """Load trajectory quality metrics."""
    base_path = Path(f'reports/{level}_trajectories')
    filepath = base_path / f'tray.{date}.{ifplId}.json'
    with open(filepath, 'r') as f:
        return json.load(f)

# Find trajectories with missing segments
metrics = load_trajectory_metrics('2023-07-03', 'AT02603928', 'L2')

if metrics['missing_start'] or metrics['missing_end']:
    print(f"Incomplete trajectory: {metrics['ifplId']}")
    print(f"  Missing start: {metrics['missing_start']}")
    print(f"  Missing end: {metrics['missing_end']}")
```

#### 2. Assess Coverage Quality

```python
# Identify poorly covered trajectories
if metrics['continuity_ratio'] < 0.5:
    print(f"Poor coverage quality: {metrics['ifplId']}")
    print(f"  Continuity ratio: {metrics['continuity_ratio']:.2%}")
    print(f"  Number of gaps: {metrics['num_gaps']}")
    print(f"  Number of segments: {metrics['num_segments']}")
```

#### 3. Validate Processing Impact (L3)

```python
# Compare L2 and L3 metrics
l2_metrics = load_trajectory_metrics('2023-07-03', 'AT02603928', 'L2')
l3_metrics = load_trajectory_metrics('2023-07-03', 'AT02603928', 'L3')

print(f"Reordered vectors: {l3_metrics['sorted_vectors']}")
print(f"Reorder percentage: {l3_metrics['sorted_vectors'] / l3_metrics['num_vectors']:.2%}")
print(f"Distance change: {l2_metrics['distance']} → {l3_metrics['distance']} miles")
```

---

## Interpretation Guidelines

### Quality Assessment Framework

Trajectory quality can be assessed using the following criteria:

| Criterion | Excellent | Good | Fair | Poor |
|-----------|-----------|------|------|------|
| **Completeness** | > 0.95 | 0.85 - 0.95 | 0.70 - 0.85 | < 0.70 |
| **Continuity ratio** | > 0.80 | 0.60 - 0.80 | 0.40 - 0.60 | < 0.40 |
| **Gap ratio** | < 0.10 | 0.10 - 0.25 | 0.25 - 0.40 | > 0.40 |
| **Density** (vectors/mile) | > 50 | 20 - 50 | 10 - 20 | < 10 |
| **Missing endpoints** | None | Start OR end | Both | - |

### Common Quality Patterns

**Pattern 1: Complete, well-covered trajectory**
- `missing_start` = false, `missing_end` = false
- `continuity_ratio` > 0.7
- `num_gaps` ≤ 2
- `density` > 30 vectors/mile

**Pattern 2: Partial coverage (missing segments)**
- `missing_start` or `missing_end` = true
- High `gap_ratio` (> 0.3)
- Multiple segments (`num_segments` > 3)
- Usable but requires careful segment selection

**Pattern 3: Sparse surveillance**
- Low `density` (< 15 vectors/mile)
- High `mean_granularity` (> 30 seconds)
- High `std_granularity` (irregular sampling)
- May limit trajectory analysis accuracy

**Pattern 4: Fragmented trajectory**
- Many gaps (`num_gaps` > 5)
- Low `continuity_ratio` (< 0.5)
- Many segments (`num_segments` > 6)
- Difficult to analyze as a coherent trajectory

### L2 vs L3 Comparison

When comparing raw (L2) and cleaned (L3) trajectories, expect:

**Improvements:**
- `distance` should decrease (outlier removal, better sorting)
- `completitude.altitude` may increase (interpolation)
- Temporal ordering should improve

**Stable metrics:**
- `num_vectors` should be similar (±5%)
- `duration` should remain similar
- `missing_start` and `missing_end` should be unchanged

**Red flags:**
- Significant decrease in `num_vectors` (> 20%)
- Large increase in `distance` after sorting
- Decrease in completeness

### Context-Dependent Interpretation

Metric interpretation depends on:

**Flight characteristics:**
- Long-haul flights naturally have more gaps (crossing coverage boundaries)
- Short flights may have higher density but less total vectors

**Geographic context:**
- Flights over dense surveillance areas (Western Europe) show better coverage
- Oceanic or remote segments show increased gaps

**Analysis purpose:**
- High-precision trajectory analysis requires high continuity and density
- Aggregate statistical analysis may tolerate lower quality

---

## Metrics File Format

Trajectory metrics are stored as JSON files with the following structure:

```json
{
  "ifplId": "AT02603928",
  "num_vectors": 1234,
  "duration": 4567,
  "distance": 523.45,

  "completitude": {
    "timestamp": 1.0,
    "latitude": 1.0,
    "longitude": 1.0,
    "altitude": 0.95,
    "velocity": 0.89
  },

  "distance_to_origin": 12.3,
  "distance_to_destination": 8.7,
  "missing_start": false,
  "missing_end": false,
  "airports_distance": 489.2,
  "effective_flight_time": 4320,
  "last_altitude_before_ground": 2156.0,

  "density": 2.36,
  "mean_granularity": 12.5,
  "std_granularity": 8.3,
  "mean_granularity_distance": 0.42,
  "std_granularity_distance": 0.28,

  "gaps": [
    {"index": 245, "size": 420},
    {"index": 789, "size": 315}
  ],
  "num_gaps": 2,
  "segments": [
    {"start": 0, "end": 244},
    {"start": 245, "end": 788},
    {"start": 789, "end": 1233}
  ],
  "num_segments": 3,
  "gap_time": 735,
  "gap_ratio": 0.161,
  "continuity_time": 3456,
  "continuity_ratio": 0.757,
  "discontinuity_time": 376,
  "discontinuity_ratio": 0.082,

  "thresholds": {
    "THRESHOLD_DISTANCE_TO_AIRPORT": 50,
    "THRESHOLD_GAP_TIME": 300,
    "THRESHOLD_CONTINUITY": 30,
    "AIRPORT_AREA": 15
  }
}
```

**L3-specific additions:**
```json
{
  "sorted_vectors": 87,
  "timestamp_variation": "0:00:18.5"
}
```

---

## Relationship with Pipeline Stages

Trajectory metrics are computed at two key stages:

**L2 (Raw Trajectories):**
- After integration of NM metadata and OpenSky vectors
- Before sorting and outlier removal
- Metrics reflect raw surveillance quality

**L3 (Cleaned Trajectories):**
- After trajectory sorting and processing
- After altitude correction and timestamp interpolation
- Metrics reflect processed trajectory quality
- Additional processing metrics available

Comparing L2 and L3 metrics allows validation of the cleaning pipeline and assessment of its impact on trajectory characteristics.
