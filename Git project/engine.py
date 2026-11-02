import random
from datetime import datetime


class WeatherEngine:

  @staticmethod
  def generate_weather_data():
    seasons = ["Tavasz", "Nyár", "Ősz", "Tél"]
    season = random.choice(seasons)

    if season == "Tél":
      temp = round(random.uniform(-10.0, 5.0), 1)
      condition = random.choice(["Hófúvás", "Borús", "Ködös", "Enyhe fagy"])
    elif season == "Nyár":
      temp = round(random.uniform(22.0, 38.0), 1)
      condition = random.choice(["Napos", "Kánikula", "Zivataros", "Fátyolfelhős"])
    elif season == "Tavasz":
      temp = round(random.uniform(10.0, 22.0), 1)
      condition = random.choice(
          ["Változóan felhős", "Enyhe eső", "Napos", "Szeles"]
      )
    else:
      temp = round(random.uniform(5.0, 18.0), 1)
      condition = random.choice(["Esős", "Ködös", "Hűvös, de napos", "Szeles"])

    humidity = random.randint(30, 95)
    wind_speed = round(random.uniform(0.0, 45.0), 1)

    # Komfortindex számítás
    feels_like = temp
    if temp > 25 and humidity > 60:
      feels_like = round(temp + (humidity / 10), 1)
    elif temp < 10 and wind_speed > 10:
      feels_like = round(temp - (wind_speed / 5), 1)

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "season": season,
        "temperature": temp,
        "feels_like": feels_like,
        "condition": condition,
        "humidity": humidity,
        "wind_speed": wind_speed,
    }