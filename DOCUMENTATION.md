# Weather Journal — Technical Documentation

## Overview

The application is a Flask weather lookup and journal. It uses external weather data rather than generating random seasonal values. A requested day is classified as historical, within forecast range, or beyond the forecast horizon and routed to an appropriate data source.

## Architecture

| File | Responsibility |
|---|---|
| `app.py` | Flask routes, request validation, messages, page rendering |
| `engine.py` | Open-Meteo geocoding and weather retrieval; forecast and climate report calculations |
| `service.py` | Read and atomically save reports in the local JSON log |
| `templates/index.html` | Date and area selection, latest report, history table |
| `static/style.css` | Responsive interface styling |

### Routes

| Route | Method | Description |
|---|---|---|
| `/` | GET | Dashboard, latest report, and saved history |
| `/locations?q=...` | GET | Search approximate city/administrative-area matches via Open-Meteo geocoding |
| `/generate` | POST | Retrieve the appropriate data for the selected date and location, save it, and return to the dashboard |

## Date and data handling

### Historical dates

For dates before today, the app requests daily data from Open-Meteo's Historical Weather API, using ERA5. Available fields include daily mean/minimum/maximum temperature, apparent temperature, precipitation total, maximum wind speed, and a WMO weather code. The report identifies these as historical weather reanalysis, since reanalysis is reconstructed gridded weather data rather than a station observation. ERA5 archive data can be delayed by several days; if a date in the last five days is not yet in the archive, the app tries the Forecast API's recent past-days data and labels it separately. The supported date range starts in 1940.

### Near-term dates

Today through 15 days ahead use the Forecast API with a 16-day response. The report uses the daily forecast's temperature range, apparent-temperature range, precipitation probability and total, maximum wind speed, and WMO weather code.

### Far-future dates

Dates beyond the forecast window use historical ERA5 data from the previous ten complete calendar years. The sample contains observations within ±7 calendar days of the selected month/day. The report presents:

- Median daily mean temperature.
- 10th–90th percentile range for daily mean temperature.
- Median daily low and high temperatures.
- The most frequent WMO condition code.
- The share of sampled days with at least 0.1 mm precipitation.
- Median precipitation and peak wind speed.

The sample size and calculation window are shown with each report. This is a climate outlook, not a specific forecast for the selected day. A climate outlook is used when an operational forecast is unavailable so the app does not invent extreme values.

### Approximate areas

Users search for a city or administrative area and select a geocoding result. The app stores its representative latitude/longitude, region, and country. It does not ask for an address. The same approximate coordinate is used for both archive and forecast lookups.

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
  "precipitation_probability": 0,
  "precipitation_sum": 0.0,
  "wind_speed": 0.0,
  "condition": "Partly cloudy",
  "data_basis": "Weather data basis",
  "data_note": "How this report should be interpreted"
}
```

The reader tolerates older simulator records so existing JSON history remains visible. New JSON writes use a temporary file and atomic replace.

## Run locally

Requires Python 3.10+ and Flask:

```bash
python -m pip install Flask
python app.py
```

Open <http://127.0.0.1:5000>. A network connection is required for geocoding and weather data. The local Flask development server is intended for development, not public deployment. Set `FLASK_SECRET_KEY` to a private value before using the app beyond local development.

## Data attribution and terms

The interface credits [Open-Meteo](https://open-meteo.com/) and GeoNames. Open-Meteo weather data is provided under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Its free API is for non-commercial use; check [Open-Meteo's terms](https://open-meteo.com/en/terms) before commercial deployment.
