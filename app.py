import os
from datetime import date

from flask import (
    Flask,
    flash,
    get_flashed_messages,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from engine import WeatherDataError, WeatherEngine
from service import WeatherService


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "local-weather-journal-dev-key")


def _dashboard(latest=None):
    records = WeatherService.get_all_records()
    temperatures = [
        float(record["temperature"])
        for record in records
        if isinstance(record, dict) and record.get("temperature") is not None
    ]
    average_temperature = round(sum(temperatures) / len(temperatures), 1) if temperatures else None
    return render_template(
        "index.html",
        latest=latest if latest is not None else (records[-1] if records else None),
        records=records,
        average_temperature=average_temperature,
        today=date.today().isoformat(),
        messages=get_flashed_messages(with_categories=True),
    )


@app.route("/")
def index():
    return _dashboard()


@app.route("/locations")
def locations():
    query = request.args.get("q", "")
    if len(query.strip()) < 2:
        return jsonify(results=[])
    try:
        return jsonify(results=WeatherEngine.search_locations(query))
    except WeatherDataError as exc:
        return jsonify(error=str(exc)), 502


@app.route("/generate", methods=["POST"])
def generate():
    try:
        selected_date = date.fromisoformat(request.form.get("date", ""))
        location = {
            "name": request.form.get("location_name", ""),
            "region": request.form.get("location_region", ""),
            "country": request.form.get("location_country", ""),
            "latitude": request.form.get("latitude"),
            "longitude": request.form.get("longitude"),
        }
        if not location["name"]:
            raise WeatherDataError("Search for and select a city or region first.")
        record = WeatherEngine.generate_weather_data(selected_date, location)
        WeatherService.save_record(record)
        flash("Weather report saved.", "success")
    except ValueError:
        flash("Choose a valid date.", "error")
    except WeatherDataError as exc:
        flash(str(exc), "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
