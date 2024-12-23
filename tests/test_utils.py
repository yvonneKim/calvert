import pytest
from pathlib import Path
import base64
from PIL import Image
import io
import json
from unittest.mock import Mock, patch
from calvert.utils import resize_image, Claude
from calvert.models import Event


@pytest.fixture
def test_image(tmp_path):
    img = Image.new("RGB", (100, 100), color="red")
    path = tmp_path / "test.jpg"
    img.save(path)
    return path


@pytest.fixture
def test_png_image(tmp_path):
    img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 255))
    path = tmp_path / "test.png"
    img.save(path)
    return path


def test_resize_image(test_image):
    base64_str, media_type = resize_image(test_image)
    assert media_type == "image/jpeg"
    assert isinstance(base64_str, str)
    decoded = base64.b64decode(base64_str)
    img = Image.open(io.BytesIO(decoded))
    assert img.mode == "RGB"


def test_resize_png_image(test_png_image):
    base64_str, media_type = resize_image(test_png_image)
    assert media_type == "image/png"
    assert isinstance(base64_str, str)
    decoded = base64.b64decode(base64_str)
    img = Image.open(io.BytesIO(decoded))
    assert img.mode == "RGB"  # Should be converted from RGBA


def test_resize_image_invalid():
    with pytest.raises(ValueError):
        resize_image(Path("test.txt"))


@patch("calvert.utils.ChatAnthropic")
def test_claude_extract_event(mock_anthropic, test_image):
    mock_response = Mock()
    mock_response.content = json.dumps(
        {
            "start": {"dateTime": "2024-03-20T10:00:00", "timeZone": "UTC"},
            "end": {"dateTime": "2024-03-20T11:00:00", "timeZone": "UTC"},
            "summary": "Test Event",
            "description": "Test Description",
        }
    )
    mock_anthropic.return_value.invoke.return_value = mock_response

    claude = Claude()
    event = claude.extract_event_from_image(test_image)

    assert isinstance(event, Event)
    assert event.summary == "Test Event"
    assert event.description == "Test Description"
