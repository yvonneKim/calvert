from dataclasses import asdict
from datetime import datetime
import io
import subprocess
import tempfile
import base64
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
import json

from PIL import Image
import os
from google.auth import default
from googleapiclient.discovery import build
from google.cloud import secretmanager
from pydantic import SecretStr

from models import Event

SYSTEM_PROMPT = """
Analyze the following image and extract event details as a json with this schema.
All dateTime values must be in ISO 8601 format with UTC timezone (e.g. "2024-03-22T15:30:00Z").

Return strictly valid JSON matching this schema:
{{
    "start": {{
        "dateTime": "<ISO8601_datetime>",  # Required, must include time
        "timeZone": "UTC"                  # Always UTC
    }},
    "end": {{
        "dateTime": "<ISO8601_datetime>",  # Required, must include time
        "timeZone": "UTC"                  # Always UTC
    }},
    "summary": "<event_title>",            # Required, brief title
    "description": "<full_details>"        # Required, include all context and details
}}

Rules:
- If no end time specified, assume event lasts 1 hour
- If no timezone specified, use UTC
- If date is mentioned without year, use {year}
- If time is ambiguous (e.g., "5pm"), interpret as 17:00 UTC
- description should include all text visible in image that provides context
- summary should be a concise title suitable for calendar view

Return only the JSON, no other text.
"""


class GoogleCalendar:
    def __init__(self):
        self.calendar_id = os.environ["CALENDAR_ID"]
        credentials, _ = default(scopes=["https://www.googleapis.com/auth/calendar"])
        self.service = build("calendar", "v3", credentials=credentials)

        calendars = {
            cal["id"]: cal
            for cal in self.service.calendarList().list().execute()["items"]
        }

        self.calendar = calendars[self.calendar_id]

    def add_event(self, event: Event):
        result = (
            self.service.events()
            .insert(calendarId=self.calendar_id, body=asdict(event))
            .execute()
        )
        print(f"Created event: {result.get('htmlLink')}")


def resize_image(image_path: Path, max_size_mb: float = 99) -> tuple[str, str]:
    supported_types = {
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".png": "png",
        ".webp": "webp",
        ".gif": "gif",
    }

    ext = Path(image_path).suffix.lower()
    if ext not in supported_types:
        raise ValueError(f"Unsupported file type: {ext}")

    img = Image.open(image_path)

    if img.mode == "RGBA":
        img = img.convert("RGB")

    buffer = io.BytesIO()
    img.save(buffer, format=supported_types[ext])
    if buffer.tell() > 100 * 1024 * 1024:
        x, y = img.size
        new_size = (x // 2, y // 2)
        img = img.resize(new_size)
        buffer = io.BytesIO()
        img.save(buffer, format=supported_types[ext])

    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
    media_type = f"image/{supported_types[ext]}"

    return base64_image, media_type


class Claude:
    def __init__(self):
        self.model = ChatAnthropic(
            api_key=self.get_anthropic_api_key(),
            model_name="claude-3-sonnet-20240229",
            timeout=60,
            stop=None,
        )

    def get_anthropic_api_key(self) -> SecretStr:
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(
            name=f"projects/{os.environ['PROJECT_ID']}/secrets/ANTHROPIC_API_KEY/versions/latest"
        )
        return SecretStr(response.payload.data.decode("UTF-8"))

    def extract_event_from_image(self, image_path: Path) -> Event | None:
        image_b64_data, media_type = resize_image(image_path)
        response = self.model.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT.format(year=datetime.now().year)),
                HumanMessage(
                    content=[
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64_data,
                            },
                        }
                    ]
                ),
            ]
        )

        try:
            event = Event.from_dict(json.loads(str(response.content)))
        except json.JSONDecodeError as e:
            print(f"Error decoding response: {e}")
            return None

        return event


def dl_images(input: str) -> Path:
    temp_dir = Path(tempfile.mkdtemp())
    subprocess.run(["gallery-dl", "-D", str(temp_dir), input], check=True)
    return temp_dir
