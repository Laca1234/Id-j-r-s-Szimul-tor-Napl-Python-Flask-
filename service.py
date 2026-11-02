import json
import os

LOG_FILE = "weather_log.json"


class WeatherService:

  @staticmethod
  def save_record(record):
    data = []
    if os.path.exists(LOG_FILE):
      try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
          data = json.load(f)
      except json.JSONDecodeError:
        data = []

    data.append(record)

    with open(LOG_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)

  @staticmethod
  def get_all_records():
    if not os.path.exists(LOG_FILE):
      return []
    try:
      with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except json.JSONDecodeError:
      return []