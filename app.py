from datetime import date

from flask import Flask, jsonify, render_template, request, send_from_directory

from engine import WeatherDataError, WeatherEngine


# Vercel serves files in /public through its CDN. This route serves the same
# stylesheet when running Flask locally.
app = Flask(__name__, static_folder=None)


@app.route("/style.css")
def stylesheet():
    return send_from_directory("public", "style.css")


@app.route("/")
def index():
    # No report or favorite history is loaded from the server. The browser
    # stores each visitor's own data in its IndexedDB profile.
    return render_template("index.html", today=date.today().isoformat())


@app.route("/locations")
def locations():
    query = request.args.get("q", "")
    language = request.args.get("lang", "en")
    if len(query.strip()) < 2:
        return jsonify(results=[])
    try:
        return jsonify(results=WeatherEngine.search_locations(query, language))
    except WeatherDataError as exc:
        return jsonify(error=str(exc)), 502


@app.route("/generate", methods=["POST"])
def generate():
    payload = request.get_json(silent=True) or {}
    try:
        selected_date = date.fromisoformat(str(payload.get("date", "")))
        end_date_text = str(payload.get("end_date", "")).strip()
        location = WeatherEngine.normalize_location(payload.get("location") or {})
        if not location["name"]:
            raise WeatherDataError("Search for and select a city or region first.")

        if end_date_text:
            end_date = date.fromisoformat(end_date_text)
            if payload.get("compare_location"):
                raise WeatherDataError("Area comparison is available for a single-day report.")
            reports = WeatherEngine.generate_weather_range(selected_date, end_date, location)
            return jsonify(reports=reports, comparison_report=None)

        first_report = WeatherEngine.generate_weather_data(selected_date, location)
        second_report = None
        compare_data = payload.get("compare_location")
        if compare_data:
            other = WeatherEngine.normalize_location(compare_data)
            if (
                float(other["latitude"]) == first_report["latitude"]
                and float(other["longitude"]) == first_report["longitude"]
            ):
                raise WeatherDataError("Choose a different saved area to compare.")
            second_report = WeatherEngine.generate_weather_data(selected_date, other)
        return jsonify(reports=[first_report], comparison_report=second_report)
    except ValueError:
        return jsonify(error="Choose valid start and end dates."), 400
    except WeatherDataError as exc:
        return jsonify(error=str(exc)), 400


if __name__ == "__main__":
    app.run(debug=True)
