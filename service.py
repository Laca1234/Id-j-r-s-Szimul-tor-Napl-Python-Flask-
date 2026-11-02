"""Local JSON persistence for requested weather reports."""

import json
import os
from pathlib import Path
from uuid import uuid4


LOG_FILE = Path(__file__).with_name("weather_log.json")
FAVORITES_FILE = Path(__file__).with_name(".saved_locations.json")


class WeatherService:
    @staticmethod
    def save_record(record):
        WeatherService.save_records([record])
        return record

    @staticmethod
    def save_records(records):
        data = WeatherService.get_all_records()
        data.extend(records)
        WeatherService._write_json(LOG_FILE, data)

    @staticmethod
    def get_all_records():
        if not LOG_FILE.exists():
            return []
        try:
            with LOG_FILE.open("r", encoding="utf-8") as file:
                records = json.load(file)
            return records if isinstance(records, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    @staticmethod
    def get_saved_locations():
        try:
            with FAVORITES_FILE.open("r", encoding="utf-8") as file:
                locations = json.load(file)
            if not isinstance(locations, list):
                return []
            return [item for item in locations if isinstance(item, dict) and item.get("id")]
        except (OSError, json.JSONDecodeError):
            return []

    @staticmethod
    def save_location(location):
        locations = WeatherService.get_saved_locations()
        for saved in locations:
            if not isinstance(saved, dict):
                continue
            if (
                saved.get("name") == location.get("name")
                and saved.get("region") == location.get("region")
                and saved.get("country") == location.get("country")
            ):
                return saved
        saved = dict(location)
        saved["id"] = uuid4().hex
        locations.append(saved)
        WeatherService._write_json(FAVORITES_FILE, locations)
        return saved

    @staticmethod
    def delete_location(location_id):
        locations = WeatherService.get_saved_locations()
        remaining = [item for item in locations if item.get("id") != location_id]
        if len(remaining) != len(locations):
            WeatherService._write_json(FAVORITES_FILE, remaining)
        return remaining

    @staticmethod
    def _write_json(path, data):
        temporary_file = path.with_suffix(path.suffix + ".tmp")
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(temporary_file, path)
