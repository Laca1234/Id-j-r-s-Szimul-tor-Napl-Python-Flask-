"""Weather data retrieval, climate context, and local response caching."""

import hashlib
import json
import statistics
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FORECAST_DOCS = "https://open-meteo.com/en/docs"
HISTORICAL_DOCS = "https://open-meteo.com/en/docs/historical-weather-api"
CACHE_FILE = Path(__file__).with_name(".weather_cache.json")
CACHE_LOCK = threading.RLock()


class WeatherDataError(Exception):
    """Raised when the selected date or external weather data is unavailable."""


class WeatherEngine:
    FORECAST_DAYS = 16
    CLIMATE_YEARS = 10
    CLIMATE_WINDOW_DAYS = 7
    MAX_RANGE_DAYS = 31
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
        """Return one historical, forecast, or climate-based report."""
        return cls.generate_weather_range(target_date, target_date, location, today)[0]

    @classmethod
    def generate_weather_range(cls, start_date, end_date, location, today=None):
        """Build up to 31 daily reports, batching provider requests by data source."""
        today = today or date.today()
        normalized_location = cls.normalize_location(location)
        if start_date < cls.EARLIEST_DATE or end_date < cls.EARLIEST_DATE:
            raise WeatherDataError("Historical data is available from 1940 onward.")
        if end_date < start_date:
            raise WeatherDataError("The end date must be the same day or after the start date.")
        if (end_date - start_date).days >= cls.MAX_RANGE_DAYS:
            raise WeatherDataError("Choose a date range of 31 days or less.")

        dates = [start_date + timedelta(days=offset) for offset in range((end_date - start_date).days + 1)]
        reports = {}

        past_dates = [selected for selected in dates if selected < today]
        forecast_dates = [
            selected
            for selected in dates
            if today <= selected < today + timedelta(days=cls.FORECAST_DAYS)
        ]
        climate_dates = [
            selected
            for selected in dates
            if selected >= today + timedelta(days=cls.FORECAST_DAYS)
        ]

        if past_dates:
            reports.update(
                cls._historical_reports(past_dates, normalized_location, today)
            )
        if forecast_dates:
            reports.update(
                cls._forecast_reports(forecast_dates, normalized_location, today)
            )
        if climate_dates:
            reports.update(cls._climate_reports(climate_dates, normalized_location, today))

        return [reports[selected.isoformat()] for selected in dates]

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
    def normalize_location(cls, location):
        latitude = cls._number(location.get("latitude"), "latitude")
        longitude = cls._number(location.get("longitude"), "longitude")
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise WeatherDataError("Choose a valid location from the search results.")
        return {
            "name": str(location.get("name", "Selected area"))[:100],
            "region": str(location.get("region", ""))[:100],
            "country": str(location.get("country", ""))[:100],
            "latitude": latitude,
            "longitude": longitude,
        }

    @classmethod
    def _historical_reports(cls, target_dates, location, today):
        start_date = min(target_dates).isoformat()
        end_date = max(target_dates).isoformat()
        try:
            daily = cls._archive_daily(location, start_date, end_date)
        except WeatherDataError:
            if all(0 < (today - selected).days <= 5 for selected in target_dates):
                return {
                    selected.isoformat(): cls._recent_report(selected, location, today)
                    for selected in target_dates
                }
            raise

        reports = {}
        for selected in target_dates:
            index = cls._date_index(daily, selected)
            if index is None or cls._value(daily, "temperature_2m_mean", index) is None:
                if 0 < (today - selected).days <= 5:
                    report = cls._recent_report(selected, location, today)
                else:
                    raise WeatherDataError(
                        "Historical data is not available for that day yet. Recent archive data can be delayed by several days."
                    )
            else:
                report = cls._historical_record(selected, location, daily, index)
            reports[selected.isoformat()] = report
        return reports

    @classmethod
    def _historical_record(cls, target_date, location, daily, index):
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
                "condition": cls._weather_label(cls._value(daily, "weather_code", index)),
                "data_basis": "Historical weather reanalysis",
                "data_note": "Reconstructed gridded weather data; not a station-verified observation.",
            }
        )
        cls._append_cache_note(record, daily.get("_cache_notice"))
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
        cls._append_cache_note(record, data.get("_cache_notice"))
        return record

    @classmethod
    def _forecast_reports(cls, target_dates, location, today):
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
        reports = {}
        for selected in target_dates:
            index = cls._date_index(daily, selected)
            if index is None or cls._value(daily, "temperature_2m_mean", index) is None:
                raise WeatherDataError("The forecast provider has no data for that day.")
            lead_days = (selected - today).days
            if lead_days <= 2:
                confidence = "Higher"
            elif lead_days <= 6:
                confidence = "Moderate"
            else:
                confidence = "Lower"
            record = cls._base_record(selected, location, "forecast", FORECAST_DOCS)
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
                    "confidence_label": confidence,
                    "lead_days": lead_days,
                    "data_note": (
                        "Lead-time guide: confidence is generally higher in the first few days and "
                        "falls farther out. This label is guidance, not a provider-issued probability."
                    ),
                }
            )
            cls._append_cache_note(record, data.get("_cache_notice"))
            reports[selected.isoformat()] = record

        try:
            samples_by_date, cache_notices = cls._collect_climate_samples(
                target_dates,
                location,
                today.year - cls.CLIMATE_YEARS,
                today.year - 1,
            )
        except WeatherDataError:
            samples_by_date, cache_notices = {}, []

        for selected in target_dates:
            summary = cls._summarize_climate(samples_by_date.get(selected.isoformat(), []))
            if summary:
                record = reports[selected.isoformat()]
                record.update(
                    {
                        "normal_temperature": summary["temperature"],
                        "normal_range_low": summary["temperature_range_low"],
                        "normal_range_high": summary["temperature_range_high"],
                        "temperature_vs_normal": round(record["temperature"] - summary["temperature"], 1),
                        "normal_precipitation_probability": summary["precipitation_probability"],
                        "normal_condition": summary["condition"],
                        "normal_sample_count": summary["sample_count"],
                    }
                )
            for notice in cache_notices:
                cls._append_cache_note(reports[selected.isoformat()], notice)
        return reports

    @classmethod
    def _climate_reports(cls, target_dates, location, today):
        first_year = max(cls.EARLIEST_DATE.year, today.year - cls.CLIMATE_YEARS)
        last_year = today.year - 1
        samples_by_date, cache_notices = cls._collect_climate_samples(
            target_dates, location, first_year, last_year
        )
        reports = {}
        for selected in target_dates:
            samples = samples_by_date.get(selected.isoformat(), [])
            summary = cls._summarize_climate(samples)
            if not summary:
                raise WeatherDataError("There is not enough historical data to build a climate outlook.")
            condition_note = (
                f"{summary['condition']} was the most frequent condition "
                f"({summary['condition_frequency']}% of coded days). "
                if summary["condition_frequency"] is not None
                else "Weather condition codes were unavailable in the archive. "
            )
            record = cls._base_record(selected, location, "climate_outlook", HISTORICAL_DOCS)
            record.update(summary)
            record.update(
                {
                    "data_basis": "10-year climate outlook",
                    "data_note": (
                        f"Median and likelihoods from {summary['sample_count']} historical days within "
                        f"±{cls.CLIMATE_WINDOW_DAYS} calendar days of this date. "
                        f"{condition_note}This is a climate outlook, not a day-specific forecast."
                    ),
                }
            )
            for notice in cache_notices:
                cls._append_cache_note(record, notice)
            reports[selected.isoformat()] = record
        return reports

    @classmethod
    def _collect_climate_samples(cls, target_dates, location, first_year, last_year):
        target_dates = sorted(target_dates)
        samples_by_date = {selected.isoformat(): [] for selected in target_dates}
        cache_notices = []
        if first_year > last_year:
            return samples_by_date, cache_notices

        first_target_year = target_dates[0].year
        anchors_by_year = {}
        for sample_year in range(first_year, last_year + 1):
            anchors = {}
            for selected in target_dates:
                sample_calendar_year = sample_year + (selected.year - first_target_year)
                sample_day = min(selected.day, cls._days_in_month(sample_calendar_year, selected.month))
                anchors[selected.isoformat()] = date(sample_calendar_year, selected.month, sample_day)
            anchors_by_year[sample_year] = anchors
            window_start = max(
                cls.EARLIEST_DATE,
                min(anchors.values()) - timedelta(days=cls.CLIMATE_WINDOW_DAYS),
            )
            window_end = max(anchors.values()) + timedelta(days=cls.CLIMATE_WINDOW_DAYS)
            daily = cls._archive_daily(location, window_start.isoformat(), window_end.isoformat())
            if daily.get("_cache_notice"):
                cache_notices.append(daily["_cache_notice"])

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
                sample = {
                    "mean": mean_temp,
                    "low": low,
                    "high": high,
                    "apparent_low": cls._value(daily, "apparent_temperature_min", index),
                    "apparent_high": cls._value(daily, "apparent_temperature_max", index),
                    "precipitation": cls._value(daily, "precipitation_sum", index),
                    "wind": cls._value(daily, "wind_speed_10m_max", index),
                    "code": cls._value(daily, "weather_code", index),
                }
                for selected in target_dates:
                    anchor = anchors_by_year[sample_year][selected.isoformat()]
                    if abs((sample_day - anchor).days) <= cls.CLIMATE_WINDOW_DAYS:
                        samples_by_date[selected.isoformat()].append(sample)

        return samples_by_date, list(dict.fromkeys(cache_notices))

    @classmethod
    def _summarize_climate(cls, samples):
        if not samples:
            return None
        means = [sample["mean"] for sample in samples]
        precipitation = [
            sample["precipitation"]
            for sample in samples
            if sample["precipitation"] is not None
        ]
        codes = [sample["code"] for sample in samples if sample["code"] is not None]
        precipitation_probability = None
        if precipitation:
            precipitation_probability = round(
                100 * sum(amount >= 0.1 for amount in precipitation) / len(precipitation)
            )
        return {
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
            "condition": cls._weather_label(cls._mode(codes)),
            "condition_frequency": cls._mode_frequency(codes),
            "sample_count": len(samples),
        }

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
        daily = dict(data["daily"])
        daily["_cache_notice"] = data.get("_cache_notice")
        return daily

    @classmethod
    def _get_json(cls, url):
        cache_key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        cached = cls._read_cached_response(cache_key)
        now = time.time()
        ttl = cls._cache_ttl(url)
        if cached and now - cached.get("saved_at", 0) <= ttl:
            return cached["data"]

        request = Request(
            url,
            headers={"User-Agent": "WeatherJournal/2.1 (educational local app)"},
        )
        try:
            with urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
            cls._write_cached_response(cache_key, data, now)
            return data
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            cached = cls._read_cached_response(cache_key)
            if cached:
                age_hours = max(1, round((time.time() - cached.get("saved_at", 0)) / 3600))
                data = dict(cached["data"])
                data["_cache_notice"] = (
                    f"Live weather service unavailable; showing saved provider data from about {age_hours} hours ago."
                )
                return data
            if isinstance(exc, HTTPError):
                try:
                    details = json.loads(exc.read().decode("utf-8"))
                    reason = details.get("reason") or details.get("message")
                except (UnicodeDecodeError, json.JSONDecodeError):
                    reason = None
                message = f"Weather service returned HTTP {exc.code}."
                if reason:
                    message += f" {reason}"
                raise WeatherDataError(message) from exc
            raise WeatherDataError(
                "Could not reach the weather service. Check your internet connection and try again."
            ) from exc

    @staticmethod
    def _read_cached_response(cache_key):
        with CACHE_LOCK:
            try:
                with CACHE_FILE.open("r", encoding="utf-8") as file:
                    cache = json.load(file)
                if not isinstance(cache, dict):
                    return None
                return cache.get(cache_key)
            except (OSError, json.JSONDecodeError):
                return None

    @classmethod
    def _write_cached_response(cls, cache_key, data, saved_at):
        with CACHE_LOCK:
            try:
                with CACHE_FILE.open("r", encoding="utf-8") as file:
                    cache = json.load(file)
                if not isinstance(cache, dict):
                    cache = {}
            except (OSError, json.JSONDecodeError):
                cache = {}
            cache[cache_key] = {"saved_at": saved_at, "data": data}
            temporary_file = CACHE_FILE.with_suffix(".json.tmp")
            try:
                with temporary_file.open("w", encoding="utf-8") as file:
                    json.dump(cache, file, ensure_ascii=False)
                temporary_file.replace(CACHE_FILE)
            except OSError:
                try:
                    temporary_file.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _cache_ttl(url):
        if "geocoding-api.open-meteo.com" in url:
            return 30 * 24 * 60 * 60
        if "api.open-meteo.com/v1/forecast" in url:
            return 15 * 60
        return 24 * 60 * 60

    @staticmethod
    def _append_cache_note(record, notice):
        if notice and not record.get("cache_notice"):
            record["cache_notice"] = notice
            record["data_note"] = f"{record.get('data_note', '')} {notice}".strip()

    @staticmethod
    def _coordinates(location):
        return {"latitude": location["latitude"], "longitude": location["longitude"]}

    @staticmethod
    def _number(value, label):
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise WeatherDataError(
                f"A valid {label} is required. Select an area from the search results."
            ) from exc

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
        month = target_date.month
        if month in (12, 1, 2):
            season = "Winter"
        elif month in (3, 4, 5):
            season = "Spring"
        elif month in (6, 7, 8):
            season = "Summer"
        else:
            season = "Autumn"
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
