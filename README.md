# Weather Journal

A Flask weather lookup for historical dates, current forecasts, and climate-based future outlooks. The interface supports English and Hungarian and stores each visitor's report history and saved places in that browser profile.

## What it does

- **Past dates:** historical weather reanalysis from Open-Meteo. Recent archive data can be delayed; the app uses the provider's recent-data endpoint when appropriate.
- **Today through 15 days ahead:** a current multi-model forecast with a lead-time confidence guide and local climate context.
- **Further future dates:** a 10-year climate outlook built from historical weather samples. This is not a day-specific forecast.
- **Areas:** search by city or administrative region, see an approximate map, save areas locally, and compare two areas for one day.
- **Date ranges:** request up to 31 days and see a temperature timeline.
- **Personal journal:** reports, favorites, and language preference stay in the browser's IndexedDB/local storage. Use Export data and Import backup to move the journal between browsers. Clearing browser/site data clears the journal.

The Flask server does not save report history or saved areas. It processes each lookup and returns weather results; the browser saves them locally. Weather requests are sent to this app and its weather provider to produce a report.

All temperatures are Celsius, precipitation is millimetres, and wind speed is kilometres per hour.

## Run locally

Requirements: Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. New location and weather lookups need an internet connection.

## Data providers and attribution

Weather and location search use [Open-Meteo](https://open-meteo.com/) and its GeoNames-based geocoding results; the approximate map uses [OpenStreetMap](https://www.openstreetmap.org/copyright). Weather data is provided under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Review [Open-Meteo's current terms](https://open-meteo.com/en/terms) before commercial use.

## Project structure

```text
app.py                 Stateless Flask routes for weather and geocoding
engine.py              Geocoding, historical data, forecasts, climate statistics
templates/index.html   Weather journal, browser storage, and EN/HU interface
public/style.css       Responsive interface stylesheet
requirements.txt       Python runtime dependency for local and Vercel deployment
```
