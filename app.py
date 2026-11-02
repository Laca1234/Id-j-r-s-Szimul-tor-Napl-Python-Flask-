from engine import WeatherEngine
from flask import Flask, redirect, render_template, url_for
from service import WeatherService

app = Flask(__name__)


@app.route("/")
def index():
  records = WeatherService.get_all_records()

  # Statisztika számítás
  avg_temp = 0
  if records:
    avg_temp = round(
        sum(item["temperature"] for item in records) / len(records), 1
    )

  latest = records[-1] if records else None

  return render_template(
      "index.html", latest=latest, records=records, avg_temp=avg_temp
  )


@app.route("/generate", methods=["POST"])
def generate():
  new_data = WeatherEngine.generate_weather_data()
  WeatherService.save_record(new_data)
  return redirect(url_for("index"))


if __name__ == "__main__":
  app.run(debug=True)