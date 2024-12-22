from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import pytest
from calvert.utils import dl_images, images_to_events, query_ai_model, Event


def test_dl_images():
    with patch("subprocess.run") as mock_run:
        input_url = "https://example.com/gallery"
        temp_dir = dl_images(input_url)
        mock_run.assert_called_once_with(
            ["gallery-dl", "-D", str(temp_dir), input_url], check=True
        )
        assert temp_dir.exists()
        assert temp_dir.is_dir()


def test_images_to_events():
    with patch("calvert.utils.query_ai_model") as mock_query_ai_model:
        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "test.jpg").touch()
        images_to_events(temp_dir)
        mock_query_ai_model.assert_called_once_with(temp_dir / "test.jpg")


def test_query_ai_model():
    with patch("langchain_anthropic.ChatAnthropic.invoke") as mock_invoke:
        mock_invoke.return_value = MagicMock(
            content='{"summary": "Test Event", "description": "This is a test event.", "start": {"dateTime": "2023-01-01T00:00:00Z", "timeZone": "UTC"}, "end": {"dateTime": "2023-01-01T01:00:00Z", "timeZone": "UTC"}}'
        )
        test_image = Path("./tests/data/test-image.jpg")
        result = query_ai_model(test_image)
        mock_invoke.assert_called_once()
        assert isinstance(result, Event)
        assert result.summary == "Test Event"
        assert result.description == "This is a test event."
        assert result.start.dateTime == "2023-01-01T00:00:00Z"
        assert result.start.timeZone == "UTC"
        assert result.end.dateTime == "2023-01-01T01:00:00Z"
        assert result.end.timeZone == "UTC"


if __name__ == "__main__":
    pytest.main()
