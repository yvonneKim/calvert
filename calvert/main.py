import argparse
from pathlib import Path


from utils import Claude, GoogleCalendar


def main():
    parser = argparse.ArgumentParser(
        description="Create Google Calendar events from images."
    )
    parser.add_argument("-d", "--directory", help="Path to a directory of images.")
    path_to_images = Path(parser.parse_args().directory)

    claude = Claude()
    gcal = GoogleCalendar()

    events = []
    for image_path in path_to_images.iterdir():
        events.append(claude.extract_event_from_image(image_path))

    for event in events:
        gcal.add_event(event)


if __name__ == "__main__":
    main()
