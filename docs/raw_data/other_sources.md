

# Airports dataset from OurAirports

## Data source description

OurAirports is an open, community-maintained dataset that provides structured information about airports worldwide. The data is curated from public sources and user contributions and distributed under an open license.

In this project, the OurAirports dataset is used as a static reference dataset to enrich trajectories and flights with airport metadata, such as geographic location and identifiers. It provides a lightweight and reliable way to map airport codes to spatial information.

The dataset is distributed as CSV files and is periodically updated.

## Access

The dataset is publicly available and can be downloaded directly from the OurAirports website. No authentication or access restrictions apply.

The project uses a local snapshot of the dataset.

## Data structure

Each record represents an airport or aerodrome.

| Attribute name  | Data type | Example value                            | Description                               |
| --------------- | --------- | ---------------------------------------- | ----------------------------------------- |
| `ident`         | string    | `"LEMD"`                                 | Airport identifier (ICAO code).           |
| `type`          | string    | `"large_airport"`                        | Airport type classification.              |
| `name`          | string    | `"Adolfo Suárez Madrid-Barajas Airport"` | Official airport name.                    |
| `latitude_deg`  | float     | `40.4719`                                | Airport latitude in decimal degrees.      |
| `longitude_deg` | float     | `-3.5626`                                | Airport longitude in decimal degrees.     |
| `elevation_ft`  | integer   | `1998`                                   | Airport elevation above sea level (feet). |
| `iso_country`   | string    | `"ES"`                                   | ISO country code.                         |

## Known data issues and limitations

- Heterogeneous data quality, as the dataset is community-maintained.
- Missing identifiers for small or private aerodromes.
- Occasional inconsistencies between ICAO/IATA codes and airport names.

## References

- OurAirports. OurAirports – Open airport and aviation data. https://ourairports.com