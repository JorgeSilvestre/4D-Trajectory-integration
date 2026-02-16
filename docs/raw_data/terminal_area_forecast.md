# Terminal Area Forecast (TAF)

## Data source description

TAF reports are standardized aerodrome weather forecasts. In this project, decoded TAF records are used as airport-level forecast context for trajectory analysis.

Input data is ingested from local parquet snapshots of decoded TAF messages.

---

## Forecast dataset

### Access

TAF products are generally public through aviation weather providers.

### Data structure

Each row represents one forecast segment for one airport and validity interval.

| Attribute name | Type | Example value | Description |
|---|---|---|---|
| `station_id` | string | `"LEMD"` | ICAO aerodrome identifier. |
| `issue_time` | datetime (UTC) | `2023-01-01T05:00:00Z` | TAF issuance timestamp. |
| `valid_time_from` | datetime (UTC) | `2023-01-01T06:00:00Z` | Segment validity start. |
| `valid_time_to` | datetime (UTC) | `2023-01-02T12:00:00Z` | Segment validity end. |
| `change_indicator` | string | `"BECMG"` | Forecast change category (`BECMG`, `TEMPO`, etc.). |
| `probability` | integer | `30` | Probability qualifier when present. |
| `wind_dir_degrees` | numeric | `270` | Wind direction (normalized modulo 360). |
| `wind_speed_kt` | integer | `12` | Wind speed in knots. |
| `wing_gust_kt` | integer | `20` | Wind gust in knots (column name matches raw schema). |
| `wind_shear_hgt_ft_agl` | integer | `2000` | Wind shear height above ground level (ft). |
| `wind_shear_dir_degrees` | integer | `250` | Wind shear direction (degrees). |
| `wind_shear_speed_kt` | integer | `30` | Wind shear speed in knots. |
| `visibility_statute_mi` | float | `6.0` | Horizontal visibility (statute miles). |
| `altim_in_hg` | float | `29.92` | Altimeter setting (inHg). |
| `vert_vis_ft` | integer | `1500` | Vertical visibility (ft). |
| `wx_string` | string | `"RA"` | Weather descriptor string. |
| `sky_cover` | string | `"BKN"` | First extracted sky-layer cover code. |
| `cloud_base_ft_agl` | integer | `3000` | First extracted sky-layer cloud base (ft AGL). |
| `cloud_type` | string | `"CB"` | First extracted sky-layer cloud type. |
| `max_temp` | integer | `25` | Extracted maximum temperature (°C). |
| `max_temp_timestamp` | datetime (UTC) | `2023-01-01T14:00:00Z` | Timestamp of extracted maximum temperature. |
| `min_temp` | integer | `12` | Extracted minimum temperature (°C). |
| `min_temp_timestamp` | datetime (UTC) | `2023-01-02T06:00:00Z` | Timestamp of extracted minimum temperature. |
| `date` | string | `"2023-01-01"` | Derived date from `issue_time` for partition-friendly analysis. |

### Known data issues and limitations

- Forecasts are predictive, not observed meteorology.
- Complex segment structure leads to sparse optional fields.
- Some validity timestamps can be missing and are imputed during cleaning.
- Nested list fields (e.g., temperatures, sky layers) are partially flattened to first-order scalar features.

---

## References

- ICAO Annex 3 — Meteorological Service for International Air Navigation.
- WMO-No. 306 — Manual on Codes.
