from dataclasses import dataclass
import io
import subprocess
import tempfile
import base64
from pathlib import Path
from typing import List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
import json

from PIL import Image


@dataclass
class EventDateTime:
    dateTime: str
    timeZone: str


@dataclass
class Event:
    summary: str
    description: str
    start: EventDateTime
    end: EventDateTime

    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        return cls(
            summary=data["summary"],
            description=data["description"],
            start=EventDateTime(**data["start"]),
            end=EventDateTime(**data["end"]),
        )


def prepare_image(image_path: Path, max_size_mb: float = 99) -> tuple[str, str]:
    """
    Encode an image for Claude, automatically resizing if it's too large.
    Returns tuple of (base64_string, media_type)
    """
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
        new_size = tuple(dim // 2 for dim in img.size)
        img = img.resize(new_size)
        buffer = io.BytesIO()
        img.save(buffer, format=supported_types[ext])

    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
    media_type = f"image/{supported_types[ext]}"

    return base64_image, media_type


model = ChatAnthropic(
    model_name="claude-3-sonnet-20240229",
    timeout=60,
    stop=None,
)


def query_ai_model(image_path: Path) -> Event | None:
    try:
        image_b64_data, media_type = prepare_image(image_path)
    except ValueError as e:
        print(f"Error preparing image: {e}")
        return None

    response = model.invoke(
        [
            SystemMessage(
                content="""
                Analyze the following image and extract event details as a json with this schema:
                {
                    "start": {
                        "dateTime": "<start_date_time>",
                        "timeZone": "<time_zone>"
                    },
                    "end": {
                        "dateTime": "<end_date_time>",
                        "timeZone": "<time_zone>"
                    },
                    "summary": "<event_summary>",
                    "description": "<event_summary>"
                }
                """
            ),
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
        event_details = json.loads(str(response.content))
    except json.JSONDecodeError as e:
        print(f"Error decoding response: {e}")
        return None

    event = Event.from_dict(event_details)

    return event


def images_to_events(path: Path) -> List[Event]:
    events = []
    for img_file in path.glob("*"):
        events.append(query_ai_model(img_file))
    return events


def dl_images(input: str) -> Path:
    temp_dir = Path(tempfile.mkdtemp())
    subprocess.run(["gallery-dl", "-D", str(temp_dir), input], check=True)
    return temp_dir
