"""Weather data retrieval and conservative, data-backed outlooks."""

import json
import statistics
from datetime import date, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FORECAST_DOCS = "https://open-meteo.com/en/docs"
HISTORICAL_DOCS = "https://open-meteo.com/en/docs/historical-weather-api"


class WeatherDataError(Exception):
    """Raised when the selected date or external weather data is unavailable."""


class WeatherEngine:
    FORECAST_DAYS = 16
    CLIMATE_YEARS = 10
    CLIMATE_WINDOW_DAYS = 7
    EARLIEST_DATE = date(1940, 1, 1)

    ARCHIVE_VARIABLES = (
        "weather_code,temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
        "apparent_temperature_max,apparent_temperature_min,precipitation_sum,"
        "wind_speed_10m_max"
    )
    FORECAST_VARIABLES = ARCHIVE_VARIABLES.replace(
        "precipitation_sum,", "precipitation_sum,precipitation_probability_max,"
    )

    WEATHER_CODES = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Freezing fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Dense drizzle",
        56: "Freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Light rain",
        63: "Rain",
        65: "Heavy rain",
        66: "Freezing rain",
        67: "Heavy freezing rain",
        71: "Light snow",
        73: "Snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Light rain showers",
        81: "Rain showers",
        82: "Heavy rain showers",
        85: "Light snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        97: "Heavy thunderstorm",
        99: "Thunderstorm with heavy hail",
    }

    @classmethod
    def generate_weather_data(cls, target_date, location, today=None):
        """Return an observed, forecast, or climate-based report for one date."""
        today = today or date.today()
        latitude = cls._number(location.get("latitude"), "latitude")
        longitude = cls._number(location.get("longitude"), "longitude")
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise WeatherDataError("Choose a valid location from the search results.")

        normalized_location = {
            "name": str(location.get("name", "Selected area"))[:100],
            "region": str(location.get("region", ""))[:100],
            "country": str(location.get("country", ""))[:100],
            "latitude": latitude,
            "longitude": longitude,
        }

        if target_date < cls.EARLIEST_DATE:
            raise WeatherDataError("Historical data is available from 1940 onward.")

        if target_date < today:
            return cls._historical_report(target_date, normalized_location, today)

        if (target_date - today).days < cls.FORECAST_DAYS:
            return cls._forecast_report(target_date, normalized_location)

        return cls._climate_report(target_date, normalized_location, today)

    @classmethod
    def search_locations(cls, query):
        query = query.strip()
        if len(query) < 2:
            return []
        url = "https://geocoding-api.open-meteo.com/v1/search?" + urlencode(
            {"name": query[:100], "count": 10, "language": "en", "format": "json"}
        )
        data = cls._get_json(url)
        results = []
        for item in data.get("results", []):
            results.append(
                {
                    "name": item.get("name", ""),
                    "region": item.get("admin1", ""),
                    "country": item.get("country", ""),
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                    "timezone": item.get("timezone", ""),
                }
            )
        return results

    @classmethod
    def _historical_report(cls, target_date, location, today):
        try:
            daily = cls._archive_daily(
                location,
                target_date.isoformat(),
                target_date.isoformat(),
            )
        except WeatherDataError:
            if 0 < (today - target_date).days <= 5:
                return cls._recent_report(target_date, location, today)
            raise
        index = cls._date_index(daily, target_date)
        if index is None or cls._value(daily, "temperature_2m_mean", index) is None:
            if 0 < (today - target_date).days <= 5:
                return cls._recent_report(target_date, location, today)
            raise WeatherDataError(
                "Historical data is not available for that day yet. Recent archive data can be delayed by several days."
            )

        code = cls._value(daily, "weather_code", index)
        record = cls._base_record(target_date, location, "historical", HISTORICAL_DOCS)
        record.update(
            {
                "temperature": cls._value(daily, "temperature_2m_mean", index),
                "temperature_min": cls._value(daily, "temperature_2m_min", index),
                "temperature_max": cls._value(daily, "temperature_2m_max", index),
                "feels_like_min": cls._value(daily, "apparent_temperature_min", index),
                "feels_like_max": cls._value(daily, "apparent_temperature_max", index),
                "precipitation_sum": cls._value(daily, "precipitation_sum", index),
                "precipitation_probability": None,
                "wind_speed": cls._value(daily, "wind_speed_10m_max", index),
                "condition": cls._weather_label(code),
                "data_basis": "Historical weather reanalysis",
                "data_note": "Reconstructed gridded weather data; not a station-verified observation.",
            }
        )
        return record

    @classmethod
    def _recent_report(cls, target_date, location, today):
        days_ago = (today - target_date).days
        params = cls._coordinates(location)
        params.update(
            {
                "daily": cls.FORECAST_VARIABLES,
                "past_days": days_ago,
                "forecast_days": 1,
                "timezone": "auto",
            }
        )
        data = cls._get_json("https://api.open-meteo.com/v1/forecast?" + urlencode(params))
        daily = data.get("daily", {})
        index = cls._date_index(daily, target_date)
        if index is None or cls._value(daily, "temperature_2m_mean", index) is None:
            raise WeatherDataError(
                "Historical data is not available for that day yet. Recent archive data can be delayed by several days."
            )

        record = cls._base_record(target_date, location, "historical", FORECAST_DOCS)
        record.update(
            {
                "temperature": cls._value(daily, "temperature_2m_mean", index),
                "temperature_min": cls._value(daily, "temperature_2m_min", index),
                "temperature_max": cls._value(daily, "temperature_2m_max", index),
                "feels_like_min": cls._value(daily, "apparent_temperature_min", index),
                "feels_like_max": cls._value(daily, "apparent_temperature_max", index),
                "precipitation_sum": cls._value(daily, "precipitation_sum", index),
                "precipitation_probability": None,
                "wind_speed": cls._value(daily, "wind_speed_10m_max", index),
                "condition": cls._weather_label(cls._value(daily, "weather_code", index)),
                "data_basis": "Recent weather data",
                "data_note": "Recent daily data from the forecast service's past-days endpoint; modelled and subject to revision.",
            }
        )
        return record

    @classmethod
    def _forecast_report(cls, target_date, location):
        params = cls._coordinates(location)
        params.update(
            {
                "daily": cls.FORECAST_VARIABLES,
                "forecast_days": cls.FORECAST_DAYS,
                "timezone": "auto",
            }
        )
        data = cls._get_json("https://api.open-meteo.com/v1/forecast?" + urlencode(params))
        daily = data.get("daily", {})
        index = cls._date_index(daily, target_date)
        if index is None or cls._value(daily, "temperature_2m_mean", index) is None:
            raise WeatherDataError("The forecast provider has no data for that day.")

        record = cls._base_record(target_date, location, "forecast", FORECAST_DOCS)
        record.update(
            {
                "temperature": cls._value(daily, "temperature_2m_mean", index),
                "temperature_min": cls._value(daily, "temperature_2m_min", index),
                "temperature_max": cls._value(daily, "temperature_2m_max", index),
                "feels_like_min": cls._value(daily, "apparent_temperature_min", index),
                "feels_like_max": cls._value(daily, "apparent_temperature_max", index),
                "precipitation_sum": cls._value(daily, "precipitation_sum", index),
                "precipitation_probability": cls._value(
                    daily, "precipitation_probability_max", index
                ),
                "wind_speed": cls._value(daily, "wind_speed_10m_max", index),
                "condition": cls._weather_label(cls._value(daily, "weather_code", index)),
                "data_basis": "Weather model forecast",
                "data_note": "Daily forecast from the multi-model weather forecast service.",
            }
        )
        return record

    @classmethod
    def _climate_report(cls, target_date, location, today):
        first_year = max(cls.EARLIEST_DATE.year, today.year - cls.CLIMATE_YEARS)
        last_year = today.year - 1
        samples = []
        for sample_year in range(first_year, last_year + 1):
            anchor_day = min(target_date.day, cls._days_in_month(sample_year, target_date.month))
            anchor = date(sample_year, target_date.month, anchor_day)
            window_start = max(cls.EARLIEST_DATE, anchor - timedelta(days=cls.CLIMATE_WINDOW_DAYS))
            window_end = anchor + timedelta(days=cls.CLIMATE_WINDOW_DAYS)
            daily = cls._archive_daily(
                location,
                window_start.isoformat(),
                window_end.isoformat(),
            )

            for index, iso_date in enumerate(daily.get("time", [])):
                try:
                    sample_day = date.fromisoformat(iso_date)
                except (TypeError, ValueError):
                    continue
                if sample_day.year < first_year or sample_day.year > last_year:
                    continue
                mean_temp = cls._value(daily, "temperature_2m_mean", index)
                low = cls._value(daily, "temperature_2m_min", index)
                high = cls._value(daily, "temperature_2m_max", index)
                if mean_temp is None:
                    if low is None or high is None:
                        continue
                    mean_temp = (low + high) / 2
                samples.append(
                    {
                        "mean": mean_temp,
                        "low": low,
                        "high": high,
                        "apparent_low": cls._value(daily, "apparent_temperature_min", index),
                        "apparent_high": cls._value(daily, "apparent_temperature_max", index),
                        "precipitation": cls._value(daily, "precipitation_sum", index),
                        "wind": cls._value(daily, "wind_speed_10m_max", index),
                        "code": cls._value(daily, "weather_code", index),
                    }
                )

        if not samples:
            raise WeatherDataError("There is not enough historical data to build a climate outlook.")

        means = [sample["mean"] for sample in samples]
        observed_precipitation = [
            sample["precipitation"]
            for sample in samples
            if sample["precipitation"] is not None
        ]
        codes = [sample["code"] for sample in samples if sample["code"] is not None]
        precipitation_probability = None
        if observed_precipitation:
            precipitation_probability = round(
                100 * sum(amount >= 0.1 for amount in observed_precipitation)
                / len(observed_precipitation)
            )
        common_code = cls._mode(codes)
        common_condition = cls._weather_label(common_code)
        condition_frequency = cls._mode_frequency(codes)
        condition_note = (
            f"{common_condition} was the most frequent condition ({condition_frequency}% of coded days). "
            if condition_frequency is not None
            else "Weather condition codes were unavailable in the archive. "
        )

        record = cls._base_record(target_date, location, "climate_outlook", HISTORICAL_DOCS)
        record.update(
            {
                "temperature": round(statistics.median(means), 1),
                "temperature_min": cls._median_field(samples, "low"),
                "temperature_max": cls._median_field(samples, "high"),
                "temperature_range_low": cls._percentile(means, 0.1),
                "temperature_range_high": cls._percentile(means, 0.9),
                "feels_like_min": cls._median_field(samples, "apparent_low"),
                "feels_like_max": cls._median_field(samples, "apparent_high"),
                "precipitation_sum": cls._median_field(samples, "precipitation"),
                "precipitation_probability": precipitation_probability,
                "wind_speed": cls._median_field(samples, "wind"),
                "condition": common_condition,
                "condition_frequency": condition_frequency,
                "sample_count": len(samples),
                "sample_years": last_year - first_year + 1,
                "data_basis": "10-year climate outlook",
                "data_note": (
                    f"Median and likelihoods from {len(samples)} historical days within "
                    f"±{cls.CLIMATE_WINDOW_DAYS} calendar days of this date. "
                    f"{condition_note}"
                    "This is a climate outlook, not a day-specific forecast."
                ),
            }
        )
        return record

    @classmethod
    def _archive_daily(cls, location, start_date, end_date):
        params = cls._coordinates(location)
        params.update(
            {
                "daily": cls.ARCHIVE_VARIABLES,
                "start_date": start_date,
                "end_date": end_date,
                "timezone": "auto",
                "models": "era5",
            }
        )
        data = cls._get_json("https://archive-api.open-meteo.com/v1/archive?" + urlencode(params))
        if "daily" not in data:
            reason = data.get("reason") or "The archive returned no daily weather data."
            raise WeatherDataError(str(reason))
        return data["daily"]

    @staticmethod
    def _get_json(url):
        request = Request(
            url,
            headers={"User-Agent": "WeatherJournal/2.0 (educational local app)"},
        )
        try:
            with urlopen(request, timeout=25) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                details = json.loads(exc.read().decode("utf-8"))
                reason = details.get("reason") or details.get("message")
            except (UnicodeDecodeError, json.JSONDecodeError):
                reason = None
            message = f"Weather service returned HTTP {exc.code}."
            if reason:
                message += f" {reason}"
            raise WeatherDataError(message) from exc
        except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise WeatherDataError(
                "Could not reach the weather service. Check your internet connection and try again."
            ) from exc

    @staticmethod
    def _coordinates(location):
        return {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
        }

    @staticmethod
    def _number(value, label):
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise WeatherDataError(f"A valid {label} is required. Select an area from the search results.") from exc

    @staticmethod
    def _date_index(daily, target_date):
        try:
            return daily.get("time", []).index(target_date.isoformat())
        except ValueError:
            return None

    @staticmethod
    def _value(daily, key, index):
        values = daily.get(key) or []
        if index >= len(values) or values[index] is None:
            return None
        try:
            return float(values[index])
        except (TypeError, ValueError):
            return None

    @classmethod
    def _weather_label(cls, code):
        if code is None:
            return "Conditions unavailable"
        return cls.WEATHER_CODES.get(int(code), "Variable conditions")

    @staticmethod
    def _base_record(target_date, location, scenario_type, source_url):
        season = WeatherEngine._season_for(target_date)
        generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
        place_parts = [location["name"], location["region"], location["country"]]
        return {
            "timestamp": target_date.isoformat(),
            "date": target_date.isoformat(),
            "generated_at": generated_at,
            "location": ", ".join(dict.fromkeys(part for part in place_parts if part)),
            "region": location["region"],
            "country": location["country"],
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "season": season,
            "scenario_type": scenario_type,
            "source": "Open-Meteo",
            "source_url": source_url,
        }

    @staticmethod
    def _season_for(target_date):
        month = target_date.month
        if month in (12, 1, 2):
            return "Winter"
        if month in (3, 4, 5):
            return "Spring"
        if month in (6, 7, 8):
            return "Summer"
        return "Autumn"

    @staticmethod
    def _days_in_month(year, month):
        if month == 12:
            return 31
        return (date(year, month + 1, 1) - timedelta(days=1)).day

    @staticmethod
    def _median_field(samples, key):
        values = [sample[key] for sample in samples if sample[key] is not None]
        return round(statistics.median(values), 1) if values else None

    @staticmethod
    def _percentile(values, fraction):
        ordered = sorted(values)
        position = round((len(ordered) - 1) * fraction)
        return round(ordered[position], 1)

    @staticmethod
    def _mode(values):
        if not values:
            return None
        counts = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        return max(counts, key=counts.get)

    @staticmethod
    def _mode_frequency(values):
        if not values:
            return None
        mode = WeatherEngine._mode(values)
        return round(100 * values.count(mode) / len(values))
