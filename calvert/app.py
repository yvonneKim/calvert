import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_session import Session
from models import Event
from utils import Claude, GoogleCalendar
from pathlib import Path

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Initialize the Flask app
app = Flask(__name__)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

if app.debug:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]

app.config["CLAUDE"] = Claude()
app.config["GCAL"] = GoogleCalendar()


@app.route("/")
def home():
    user_logged_in = "credentials" in session
    return render_template("index.html", user_logged_in=user_logged_in)


@app.route("/authorize")
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for("oauth2callback", _external=True),
    )
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


# OAuth callback route
@app.route("/oauth2callback")
def oauth2callback():
    state = session["state"]
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for("oauth2callback", _external=True),
    )
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    session["credentials"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# Check and build Google Calendar service
def get_calendar_service():
    if "credentials" not in session:
        return None
    credentials = session["credentials"]
    return build("calendar", "v3", credentials=credentials)


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


@app.route("/api/add-event", methods=["POST"])
def add_event():
    data = request.get_json()
    try:
        event = Event.from_dict(data)
        service = get_calendar_service()
        if not service:
            return jsonify({"error": "User not authenticated."}), 401

        service.add_event(event)
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
