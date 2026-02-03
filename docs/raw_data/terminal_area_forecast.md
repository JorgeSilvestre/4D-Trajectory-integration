# Terminal Area Forecast (TAF)

## Data source description

Terminal Area Forecasts (TAF) are standardized aviation weather forecasts describing expected meteorological conditions at an airport for a given validity period, typically up to 30 hours. TAFs are issued by meteorological authorities and encoded according to ICAO standards.

In this project, TAF data is used to provide **forecasted meteorological context at airports**, supporting the analysis of flight operations and trajectory quality. The data is obtained in decoded form and processed into a structured tabular representation.

The project operates on locally stored parquet files containing decoded TAF reports.

---

## TAF forecast data

### Access

TAF data is publicly available through aviation weather providers. No authentication is required.

---

### Data structure

Each record represents a forecast segment for a given airport and validity interval.

| Attribute name | Data type | Example value | Description |
|---------------|-----------|---------------|-------------|
| `station_id` | string | `"LEMD"` | ICAO airport code. |
| `issue_time` | datetime | `2023-01-01T05:00:00Z` | TAF issuance time. |
| `valid_time_from` | datetime | `2023-01-01T06:00:00Z` | Start of forecast validity period. |
| `valid_time_to` | datetime | `2023-01-02T12:00:00Z` | End of forecast validity period. |
| `change_indicator` | string | `"BECMG"` | Forecast change indicator (e.g. BECMG, TEMPO, AMD). |
| `probability` | integer | `30` | Probability associated with the forecast change. |
| `wind_dir_degrees` | float | `270` | Forecast wind direction (degrees). |
| `wind_speed_kt` | integer | `12` | Forecast wind speed (knots). |
| `wing_gust_kt` | integer | `20` | Forecast wind gust speed (knots). |
| `wind_shear_hgt_ft_agl` | integer | `2000` | Wind shear height above ground level (feet). |
| `wind_shear_dir_degrees` | integer | `250` | Wind shear direction (degrees). |
| `wind_shear_speed_kt` | integer | `30` | Wind shear speed (knots). |
| `visibility_statute_mi` | float | `6.0` | Forecast horizontal visibility (statute miles). |
| `altim_in_hg` | float | `29.92` | Altimeter setting (inches of mercury). |
| `vert_vis_ft` | integer | `1500` | Vertical visibility (feet). |
| `wx_string` | string | `"RA"` | Weather phenomena description. |
| `sky_cover` | string | `"BKN"` | Sky cover code. |
| `cloud_base_ft_agl` | integer | `3000` | Cloud base height above ground level (feet). |
| `cloud_type` | string | `"CB"` | Cloud type. |
| `max_temp` | integer | `25` | Forecast maximum temperature (°C). |
| `max_temp_timestamp` | datetime | `2023-01-01T14:00:00Z` | Time of maximum temperature. |
| `min_temp` | integer | `12` | Forecast minimum temperature (°C). |
| `min_temp_timestamp` | datetime | `2023-01-02T06:00:00Z` | Time of minimum temperature. |

---

### Known data issues and limitations

- **Forecast-based nature**, representing expected rather than observed conditions.
- **Complex temporal structure**, including base conditions and conditional changes (BECMG, TEMPO).
- **Sparse population of some fields**, such as icing and turbulence conditions.

These characteristics require temporal alignment and consolidation of forecast segments.

---

## References

- ICAO. *Annex 3 – Meteorological Service for International Air Navigation*.  
- World Meteorological Organization. *Manual on Codes (WMO-No. 306)*.
