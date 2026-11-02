# Weather Journal

A small Flask application for looking up weather by date and approximate area. Reports come from weather data and climate statistics instead of randomized conditions.

## What it does

- **Past date:** loads daily historical weather reanalysis from Open-Meteo's archive. It is gridded, model-reconstructed data, not a station-verified observation. If one of the last five days is not in the archive yet, the app falls back to the provider's recent past-days data.
- **Today through 15 days ahead:** loads the daily multi-model forecast.
- **More than 15 days ahead:** builds a climate outlook from the previous ten years of ERA5 data, using dates within seven calendar days of the selected day. The typical temperature is the median; the temperature band is the 10th–90th percentile range; precipitation likelihood is the share of sampled days with measurable precipitation. This is not a day-specific forecast.
- **Area selection:** searches city and administrative-area names. The chosen coordinates represent an approximate area, not an address.
- **Report history:** saves reports to `weather_log.json`.

All temperatures are Celsius, precipitation is millimetres, and wind speed is kilometres per hour.

## Run locally

Requirements: Python 3.10+ and Flask.

```bash
python -m pip install Flask
python app.py
```

Open <http://127.0.0.1:5000> in a browser. Location search and weather lookups require an internet connection. The app itself does not need an API key for personal or educational non-commercial use.

## Data providers and attribution

Weather and location search use [Open-Meteo](https://open-meteo.com/) and its GeoNames-based geocoding results. Weather data is provided under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); the interface includes attribution. Review [Open-Meteo's current terms](https://open-meteo.com/en/terms) before deploying or using the free API commercially.

## Project structure

```text
app.py                 Flask routes and page rendering
engine.py              Geocoding, forecast, historical data, climate statistics
service.py              Local JSON report storage
templates/index.html   Date/location form, report, and history
static/style.css        Responsive dashboard styling
weather_log.json        Saved reports
```
