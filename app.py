import os
from datetime import date
from uuid import uuid4

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


def _dashboard():
    records = WeatherService.get_all_records()
    latest = records[-1] if records else None
    timeline_group = latest.get("range_group") if isinstance(latest, dict) else None
    comparison_group = latest.get("comparison_group") if isinstance(latest, dict) else None
    timeline_records = [
        record
        for record in records
        if timeline_group and isinstance(record, dict) and record.get("range_group") == timeline_group
    ]
    comparison_records = [
        record
        for record in records
        if comparison_group
        and isinstance(record, dict)
        and record.get("comparison_group") == comparison_group
    ]
    range_values = [
        float(record.get(key))
        for record in timeline_records
        for key in ("temperature_min", "temperature_max")
        if record.get(key) is not None
    ]
    timeline_min_temperature = min(range_values) if range_values else None
    timeline_max_temperature = max(range_values) if range_values else None
    span = max((timeline_max_temperature or 0) - (timeline_min_temperature or 0), 1)
    for record in timeline_records:
        low = record.get("temperature_min")
        high = record.get("temperature_max")
        if low is None:
            low = record.get("temperature", 0)
        if high is None:
            high = record.get("temperature", 0)
        if low is not None and high is not None and timeline_min_temperature is not None:
            record["range_left"] = round(100 * (float(low) - timeline_min_temperature) / span, 1)
            record["range_width"] = max(3, round(100 * (float(high) - float(low)) / span, 1))
    temperatures = [
        float(record["temperature"])
        for record in records
        if isinstance(record, dict) and record.get("temperature") is not None
    ]
    average_temperature = round(sum(temperatures) / len(temperatures), 1) if temperatures else None
    return render_template(
        "index.html",
        latest=latest,
        records=records,
        favorites=WeatherService.get_saved_locations(),
        timeline_records=timeline_records,
        timeline_min_temperature=timeline_min_temperature,
        timeline_max_temperature=timeline_max_temperature,
        comparison_records=comparison_records,
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


@app.route("/favorites", methods=["GET"])
def favorites():
    return jsonify(locations=WeatherService.get_saved_locations())


@app.route("/favorites", methods=["POST"])
def save_favorite():
    payload = request.get_json(silent=True) or request.form
    try:
        location = WeatherEngine.normalize_location(
            {
                "name": payload.get("name", ""),
                "region": payload.get("region", ""),
                "country": payload.get("country", ""),
                "latitude": payload.get("latitude"),
                "longitude": payload.get("longitude"),
            }
        )
        if not location["name"]:
            raise WeatherDataError("Select an area before saving it.")
        return jsonify(location=WeatherService.save_location(location))
    except WeatherDataError as exc:
        return jsonify(error=str(exc)), 400


@app.route("/favorites/<location_id>", methods=["DELETE"])
def delete_favorite(location_id):
    return jsonify(locations=WeatherService.delete_location(location_id))


@app.route("/generate", methods=["POST"])
def generate():
    try:
        selected_date = date.fromisoformat(request.form.get("date", ""))
        end_date_text = request.form.get("end_date", "").strip()
        location = {
            "name": request.form.get("location_name", ""),
            "region": request.form.get("location_region", ""),
            "country": request.form.get("location_country", ""),
            "latitude": request.form.get("latitude"),
            "longitude": request.form.get("longitude"),
        }
        if not location["name"]:
            raise WeatherDataError("Search for and select a city or region first.")

        compare_id = request.form.get("compare_location_id", "").strip()
        if end_date_text:
            end_date = date.fromisoformat(end_date_text)
            if compare_id:
                raise WeatherDataError("Area comparison is available for a single-day report.")
            reports = WeatherEngine.generate_weather_range(selected_date, end_date, location)
            range_group = uuid4().hex
            for report in reports:
                report["range_group"] = range_group
            WeatherService.save_records(reports)
            flash(f"Saved a {len(reports)}-day weather timeline.", "success")
        else:
            first_report = WeatherEngine.generate_weather_data(selected_date, location)
            reports = [first_report]
            if compare_id:
                other = next(
                    (
                        item
                        for item in WeatherService.get_saved_locations()
                        if item.get("id") == compare_id
                    ),
                    None,
                )
                if other is None:
                    raise WeatherDataError("That saved comparison area no longer exists.")
                if (
                    float(other["latitude"]) == first_report["latitude"]
                    and float(other["longitude"]) == first_report["longitude"]
                ):
                    raise WeatherDataError("Choose a different saved area to compare.")
                second_report = WeatherEngine.generate_weather_data(selected_date, other)
                comparison_group = uuid4().hex
                first_report["comparison_group"] = comparison_group
                second_report["comparison_group"] = comparison_group
                reports.append(second_report)
            WeatherService.save_records(reports)
            flash(
                "Saved the weather report and comparison." if compare_id else "Weather report saved.",
                "success",
            )
    except ValueError:
        flash("Choose valid start and end dates.", "error")
    except WeatherDataError as exc:
        flash(str(exc), "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
