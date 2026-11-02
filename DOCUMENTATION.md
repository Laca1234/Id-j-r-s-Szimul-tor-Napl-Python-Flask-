# Weather Journal — Technical Documentation

## Overview

The application is a Flask weather lookup and journal. It uses external weather data rather than generating random seasonal values. A requested day is classified as historical, within forecast range, or beyond the forecast horizon and routed to an appropriate data source.

## Architecture

| File | Responsibility |
|---|---|
| `app.py` | Flask routes, request validation, messages, page rendering |
| `engine.py` | Open-Meteo geocoding and weather retrieval; forecast and climate calculations; response cache |
| `service.py` | Atomic JSON persistence for reports and favorite areas |
| `templates/index.html` | Date range and area selection, map preview, comparisons, timelines, and history |
| `static/style.css` | Responsive interface styling |

### Routes

| Route | Method | Description |
|---|---|---|
| `/` | GET | Dashboard, latest report, and saved history |
| `/locations?q=...` | GET | Search approximate city/administrative-area matches via Open-Meteo geocoding |
| `/generate` | POST | Retrieve the appropriate data for the selected date and location, save it, and return to the dashboard |
| `/favorites` | GET, POST | List saved areas or add the selected area to favorites |
| `/favorites/<id>` | DELETE | Remove one saved area |

## Date and data handling

### Historical dates

For dates before today, the app requests daily data from Open-Meteo's Historical Weather API, using ERA5. Available fields include daily mean/minimum/maximum temperature, apparent temperature, precipitation total, maximum wind speed, and a WMO weather code. The report identifies these as historical weather reanalysis, since reanalysis is reconstructed gridded weather data rather than a station observation. ERA5 archive data can be delayed by several days; if a date in the last five days is not yet in the archive, the app tries the Forecast API's recent past-days data and labels it separately. The supported date range starts in 1940.

### Near-term dates

Today through 15 days ahead use the Forecast API with a 16-day response. The report uses the daily forecast's temperature range, apparent-temperature range, precipitation probability and total, maximum wind speed, and WMO weather code.

Each forecast also gets a lead-time guide: higher for days 0–2, moderate for days 3–6, and lower from day 7 onward. These are descriptive guidance labels, not provider-issued probability scores. Forecast mean temperature is compared with a 10-year same-season sample; the report shows the temperature difference, typical range, and historical precipitation likelihood when that comparison data is available.

### Far-future dates

Dates beyond the forecast window use historical ERA5 data from the previous ten complete calendar years. The sample contains observations within ±7 calendar days of the selected month/day. The report presents:

- Median daily mean temperature.
- 10th–90th percentile range for daily mean temperature.
- Median daily low and high temperatures.
- The most frequent WMO condition code.
- The share of sampled days with at least 0.1 mm precipitation.
- Median precipitation and peak wind speed.

The sample size and calculation window are shown with each report. This is a climate outlook, not a specific forecast for the selected day. A climate outlook is used when an operational forecast is unavailable so the app does not invent extreme values.

### Date ranges

Users can request up to 31 consecutive days. Historical dates are fetched as one archive range, near-term dates use one forecast request, and long-range dates use batched historical windows. Each daily report is saved with a range-group identifier. The dashboard renders the saved group as a temperature-range timeline.

### Approximate areas

Users search for a city or administrative area and select a geocoding result. The app stores its representative latitude/longitude, region, and country. It does not ask for an address. The same approximate coordinate is used for both archive and forecast lookups.

The selected place can be saved as a favorite. Saved areas live in `.saved_locations.json`, which is excluded from Git. For a single-day lookup, a second saved area can be selected for side-by-side comparison. An OpenStreetMap preview shows the representative point and an approximate surrounding area.

### Cache and offline fallback

Provider JSON responses are cached in `.weather_cache.json`, excluded from Git. Geocoding results are cached for 30 days, forecasts for 15 minutes, and archive responses for one day. If a live request fails, the engine serves matching cached data and adds a visible note with its approximate age. Cache writes use an atomic replace.

## Stored report shape

`weather_log.json` contains a JSON array. New reports include:

```json
{
  "date": "YYYY-MM-DD",
  "generated_at": "ISO-8601 timestamp",
  "location": "Place, Region, Country",
  "latitude": 0.0,
  "longitude": 0.0,
  "scenario_type": "historical | forecast | climate_outlook",
  "source": "Open-Meteo",
  "source_url": "provider documentation link",
  "temperature": 0.0,
  "temperature_min": 0.0,
  "temperature_max": 0.0,
  "normal_temperature": 0.0,
  "temperature_vs_normal": 0.0,
  "confidence_label": "Higher | Moderate | Lower",
  "precipitation_probability": 0,
  "precipitation_sum": 0.0,
  "wind_speed": 0.0,
  "condition": "Partly cloudy",
  "data_basis": "Weather data basis",
  "data_note": "How this report should be interpreted"
}
```

The reader tolerates older simulator records so existing JSON history remains visible. New JSON writes use a temporary file and atomic replace.

Reports created by a date-range request also carry a shared `range_group`; reports created by a same-day area comparison carry a shared `comparison_group`. These identifiers let the dashboard reconstruct the latest timeline or comparison from the report log.

## Run locally

Requires Python 3.10+ and Flask:

```bash
python -m pip install Flask
python app.py
```

Open <http://127.0.0.1:5000>. A network connection is required for new geocoding and weather data; cached results can be used during outages. The local Flask development server is intended for development, not public deployment. Set `FLASK_SECRET_KEY` to a private value before using the app beyond local development.

## Data attribution and terms

The interface credits [Open-Meteo](https://open-meteo.com/) and GeoNames. Open-Meteo weather data is provided under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Its free API is for non-commercial use; check [Open-Meteo's terms](https://open-meteo.com/en/terms) before commercial deployment.
