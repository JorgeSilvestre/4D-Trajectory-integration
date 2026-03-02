# Auxiliary reference sources

## Airport reference datasets

The cleaning layer includes utilities to generate an airport reference parquet from two possible raw sources:

- **FlightRadar24 airports JSON** (`fr24_airports_process`).
- **OurAirports CSV snapshot** (`ourairports_airports_process`).

Both are source-local L0→L1 transformations used to provide static airport metadata for enrichment stages.

## OurAirports

OurAirports is a community-maintained open dataset with worldwide airport metadata.

### Access

Public download: <https://ourairports.com>.

### Data structure (raw snapshot)

| Attribute name | Type | Example value | Description |
|---|---|:-|---|
| `ident` | string | `"LEMD"` | Airport identifier. |
| `type` | string | `"large_airport"` | Airport category used for filtering. |
| `icao_code` | string | `"LEMD"` | ICAO airport code. |
| `iata_code` | string | `"MAD"` | IATA airport code. |
| `name` | string | `"Adolfo Suárez Madrid-Barajas Airport"` | Airport name. |
| `latitude_deg` | float | `40.4719` | Latitude in decimal degrees. |
| `longitude_deg` | float | `-3.5626` | Longitude in decimal degrees. |
| `elevation_ft` | integer | `1998` | Elevation in feet. |
| `continent` | string | `"EU"` | Continent code. |
| `iso_country` | string | `"ES"` | ISO country code. |
| `iso_region` | string | `"ES-M"` | ISO region code. |

### Transformation in this repository

- Keep only `large_airport` rows.
- Project selected identifier/geospatial columns.
- Rename to canonical names:
  - `latitude_deg` → `latitude`
  - `longitude_deg` → `longitude`
  - `elevation_ft` → `elevation`
- Persist parquet with typed numeric columns.

### Known limitations

- Community curation implies heterogeneous data quality.
- Identifier completeness varies by region/airport class.

## FlightRadar24 airports snapshot

FR24 airport data is stored as JSON rows and normalized to parquet as an alternative static source.

### Data structure (raw snapshot)

| Attribute name | Type | Example value | Description |
|---|---|---|---|
| `name` | string | `"Adolfo Suárez Madrid-Barajas Airport"` | Airport name. |
| `iata` | string | `"MAD"` | IATA code. |
| `icao` | string | `"LEMD"` | ICAO code. |
| `lat` | float | `40.4719` | Latitude in decimal degrees. |
| `lon` | float | `-3.5626` | Longitude in decimal degrees. |
| `alt` | integer | `1998` | Elevation/altitude in feet. |

### Transformation in this repository

- Parse `rows` from `airports.json`.
- Rename fields to canonical geospatial names:
  - `lat` → `latitude`
  - `lon` → `longitude`
  - `alt` → `altitude`
- Persist parquet for downstream enrichment.

### Known limitations

- Snapshot freshness depends on manual/local data refresh cadence.
- Field semantics are source-dependent and should be validated when mixed with other airport catalogs.

---

## Airline reference datasets
