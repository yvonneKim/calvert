from flask import Flask, request, jsonify, render_template
from flask_session import Session
from models import Event
from utils import Claude, GoogleCalendar
from pathlib import Path


# Initialize the Flask app
app = Flask(__name__)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.config["CLAUDE"] = Claude()
app.config["GCAL"] = GoogleCalendar()


# Home route
@app.route("/")
def home():
    return render_template("index.html")


# API route to extract event details from an uploaded image
@app.route("/api/extract-event", methods=["POST"])
def extract_event():
    if "image" not in request.files:
        return jsonify({"error": "No image file uploaded."}), 400

    image_file = request.files["image"]
    temp_path = Path(f"/tmp/{image_file.filename}")
    image_file.save(temp_path)

    claude = app.config["CLAUDE"]
    event = claude.extract_event_from_image(temp_path)
    if not event:
        return jsonify(
            {"error": "Failed to extract event details from the image."}
        ), 500

    return jsonify(
        {
            "summary": event.summary,
            "description": event.description,
            "start": {
                "dateTime": event.start.dateTime,
                "timeZone": event.start.timeZone,
            },
            "end": {
                "dateTime": event.end.dateTime,
                "timeZone": event.end.timeZone,
            },
        }
    )


# API route to add an event to Google Calendar
@app.route("/api/add-event", methods=["POST"])
def add_event():
    data = request.get_json()
    try:
        event = Event.from_dict(data)
        gcal = app.config["GCAL"]
        gcal.add_event(event)
        return jsonify({"message": "Event added to Google Calendar successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


def main():
    app.run(debug=True)

    # parser = argparse.ArgumentParser(
    #     description="Create Google Calendar events from images."
    # )
    # parser.add_argument("-d", "--directory", help="Path to a directory of images.")
    # path_to_images = Path(parser.parse_args().directory)

    # events = []
    # for image_path in path_to_images.iterdir():
    #     events.append(claude.extract_event_from_image(image_path))

    # for event in events:
    #     gcal.add_event(event)


if __name__ == "__main__":
    main()
