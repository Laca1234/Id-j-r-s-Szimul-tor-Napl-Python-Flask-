

# Időjárás Szimulátor & Napló — Technical Documentation

## 1. Project Overview

The Weather Simulator & Journal is an educational web application built with Python and Flask.

It demonstrates a layered, MVC-style architecture by separating HTTP request handling, weather generation logic, and persistent data storage.

The application does not use an external weather API. Instead, it generates simulated weather records using randomized, season-based rules and stores the generated data in a local JSON file.

The user can generate new weather reports and review previously generated records through a browser interface.

## 2. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application logic |
| Flask | Web framework and routing |
| HTML5 | Page structure |
| CSS3 | Interface styling |
| Jinja2 | Dynamic HTML rendering |
| JSON | Persistent local data storage |

## 3. Architecture

The application separates its responsibilities into three main layers.

### Controller — `app.py`

The Flask application handles incoming HTTP requests and connects the presentation layer with the application logic.

Available routes:

| Route | Method | Function |
|---|---|---|
| `/` | GET | Displays the dashboard and weather history. |
| `/generate` | POST | Generates and saves a new weather record. |

The homepage retrieves stored records, calculates the average temperature, and identifies the latest generated report.

### Engine — `engine.py`

The `WeatherEngine` class is responsible for generating simulated weather data.

Its main method is:

```python
WeatherEngine.generate_weather_data()
```

The method generates the following information:

- Timestamp.
- Season.
- Temperature.
- Feels-like temperature.
- Weather condition.
- Humidity.
- Wind speed.

### Service — `service.py`

The `WeatherService` class handles persistent data storage.

Its main methods are:

```python
WeatherService.save_record(record)
WeatherService.get_all_records()
```

The service reads and writes weather records to a local JSON file named `weather_log.json`.

If the file does not exist, the application starts with an empty history.

If the stored JSON is invalid, the service falls back to an empty dataset.

### Presentation — `templates/` and `static/`

The presentation layer contains:

- `templates/index.html` — dynamic dashboard template.
- `static/style.css` — visual styling.

The HTML template uses Jinja2 to display the latest weather report, statistics, and historical records.

## 4. Weather Generation Logic

Weather data is generated locally using Python's `random` module.

The application randomly selects one of four seasons.

| Season | Temperature Range |
|---|---|
| Spring (`Tavasz`) | 10–22 °C |
| Summer (`Nyár`) | 22–38 °C |
| Autumn (`Ősz`) | 5–18 °C |
| Winter (`Tél`) | -10–5 °C |

The selected season determines the available weather conditions.

Humidity is generated between 30% and 95%.

Wind speed is generated between 0 and 45 km/h.

## 5. Feels-Like Temperature Calculation

The application calculates a simplified comfort temperature using the generated temperature, humidity, and wind speed.

The implemented rules are:

**Hot and humid conditions:**

If temperature is above 25 °C and humidity is above 60%:

```python
feels_like = round(temp + (humidity / 10), 1)
```

**Cold and windy conditions:**

If temperature is below 10 °C and wind speed is above 10 km/h:

```python
feels_like = round(temp - (wind_speed / 5), 1)
```

**Other conditions:**

The feels-like temperature remains equal to the generated temperature.

These calculations are simplified educational rules, not a meteorological forecasting model.

## 6. Data Storage

Weather records are stored in:

```text
weather_log.json
```

Each record contains the generated weather information.

Example structure:

```json
{
    "timestamp": "2026-01-01 12:30:00",
    "season": "Tavasz",
    "temperature": 18.5,
    "feels_like": 18.5,
    "condition": "Napos",
    "humidity": 55,
    "wind_speed": 8.2
}
```

The example illustrates the data structure; actual values are generated randomly.

The JSON file is created automatically when the first record is saved.

## 7. Web Interface

The dashboard provides three main areas.

### Generate Weather

A button submits a POST request to `/generate`.

The application generates a new report, saves it, and redirects the user to the homepage.

### Current Report

Displays the latest available weather record, including:

- Date and time.
- Season.
- Weather condition.
- Temperature.
- Feels-like temperature.
- Humidity.
- Wind speed.

### Statistics and History

The dashboard displays:

- Total number of generated records.
- Average temperature across stored records.
- Historical weather reports in a table.

The history is displayed in reverse order so that the newest records appear first.

## 8. Installation

### Requirements

- Python 3.10 or newer.
- pip.

Clone the repository:

```bash
git clone https://github.com/Laca1234/Id-j-r-s-Szimul-tor-Napl-Python-Flask-.git
cd Id-j-r-s-Szimul-tor-Napl-Python-Flask-
```

Install Flask:

```bash
pip install Flask
```

## 9. Running the Application

Start the Flask server:

```bash
python app.py
```

Open the application in a browser:

```text
http://127.0.0.1:5000
```

The application currently starts Flask with debug mode enabled, which is suitable for local development but should be disabled in a production deployment.

## 10. Project Structure

```text
weather-simulator/
├── app.py
├── engine.py
├── service.py
├── weather_log.json
├── templates/
│   └── index.html
└── static/
    └── style.css
```

`weather_log.json` is generated at runtime and may not exist in a fresh checkout.

## 11. Limitations

- Weather data is simulated rather than retrieved from real measurements.
- No external weather API is used.
- The generation logic is randomized.
- The feels-like calculation is simplified.
- JSON storage is intended for a small local application rather than concurrent production workloads.
- The development server is not intended for public production deployment.

## 12. Project Scope

The project demonstrates separation of concerns in a small Flask application, including routing, business logic, local persistence, and dynamic server-rendered HTML.

