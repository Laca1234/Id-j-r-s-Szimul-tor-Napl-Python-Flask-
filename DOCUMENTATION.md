# Weather Journal — Technical Documentation

## Overview

The application is a stateless Flask weather lookup with a browser-local journal. A request is routed to historical reanalysis, an operational forecast, or a climate outlook according to the selected date. The server returns report JSON and does not read or save a shared history or favorites file.

## Architecture

| File | Responsibility |
|---|---|
| `app.py` | Flask page, geocoding, and weather JSON endpoints |
| `engine.py` | Open-Meteo requests, report calculations, and bounded in-memory provider-response cache |
| `templates/index.html` | EN/HU interface, browser storage, report rendering, import/export |
| `public/style.css` | Responsive stylesheet served locally by Flask and through Vercel's public asset support |
| `requirements.txt` | Flask runtime dependency |

### Routes

| Route | Method | Description |
|---|---|---|
| `/` | GET | Empty dashboard shell; no server-side report history is loaded |
| `/style.css` | GET | Stylesheet route for local development; Vercel serves `public/style.css` as a static asset |
| `/locations?q=...&lang=en\|hu` | GET | Search approximate cities and administrative areas |
| `/generate` | POST JSON | Retrieve one day or a date range, optionally with a second comparison area; returns reports as JSON and does not persist them |

### Browser-local data

Reports and saved areas are stored in IndexedDB, scoped to the current browser profile and site origin. A localStorage fallback is used if IndexedDB is unavailable. The interface has JSON export/import and a clear-data action. The selected language is stored separately in localStorage.

Browser storage is isolated by browser profile and origin. Clearing site data removes it, so users should export a backup before changing browsers or deleting browser data. Requests to `/generate` include the date and approximate coordinates because the server needs them to request weather data; the server does not turn those requests into a shared journal.

The engine holds up to 128 public provider responses in process memory to reduce duplicate requests. This cache is temporary, may disappear when a serverless instance is recycled, and contains no report history or favorites.

## Date and data handling

### Historical dates

Dates before today use Open-Meteo's Historical Weather API with ERA5. The report identifies the values as historical reanalysis because they are reconstructed gridded data, not station-verified observations. Archive data can be delayed by several days; for recent dates the engine can use the Forecast API's past-days endpoint. Supported dates start in 1940.

### Near-term dates

Today through 15 days ahead use the Forecast API. Reports include daily temperature range, apparent-temperature range, precipitation probability and total, maximum wind speed, and WMO condition code where available.

The lead-time guide is higher for days 0–2, moderate for days 3–6, and lower from day 7 onward. These are descriptive labels, not provider-issued probability scores. Forecast temperature is also compared with a 10-year sample near the same time of year.

### Far-future dates

Dates beyond the forecast window use ERA5 samples from the previous ten complete calendar years, within a ±7-day calendar window around the selected month and day. The report shows median temperature, a 10th–90th percentile band, typical lows/highs, the most common condition, precipitation likelihood, wind, and sample count. It is a climate outlook, not a day-specific forecast.

### Date ranges and comparisons

The UI accepts up to 31 consecutive days. The engine batches past, forecast, and climate requests by data source. A same-day comparison requests each selected area's report and returns both in one response. Group identifiers are added by the browser when saving the response locally; they are not stored server-side.

## Approximate area handling

Location search returns city or administrative-area names with representative coordinates. The app does not ask for street addresses. These coordinates are sent to Open-Meteo for weather lookup; the selected approximate point is shown on an OpenStreetMap preview.

## Local run

Python 3.10+ is required:

```bash
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. New weather and geocoding requests require network access.

## Vercel deployment

The root-level `app.py` exports the Flask instance named `app`. Vercel detects Flask and installs dependencies from `requirements.txt`; static files belong in `public/`. There is no server-side journal storage, so separate visitors do not receive the same report history. Browser-local data does not automatically transfer between origins or browser profiles.

## Data attribution and terms

The interface credits Open-Meteo, GeoNames, and OpenStreetMap. Weather data is provided under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Review [Open-Meteo's terms](https://open-meteo.com/en/terms) before commercial deployment.
