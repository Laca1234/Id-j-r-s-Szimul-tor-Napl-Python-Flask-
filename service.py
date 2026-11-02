"""Local JSON persistence for requested weather reports."""

import json
import os
from pathlib import Path


LOG_FILE = Path(__file__).with_name("weather_log.json")


class WeatherService:
    @staticmethod
    def save_record(record):
        data = WeatherService.get_all_records()
        data.append(record)
        temporary_file = LOG_FILE.with_suffix(".json.tmp")
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(temporary_file, LOG_FILE)
        return record

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
