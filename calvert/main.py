import argparse

from pathlib import Path

from calvert.utils import images_to_events


def main():
    parser = argparse.ArgumentParser(description="Download images using gallery-dl")
    args = parser.parse_args()

    # path_to_images = dl_images(args.input)
    path_to_images = Path("temp_dir")
    print(f"Images downloaded to: {path_to_images}")
    events = images_to_events(path_to_images)
    print(events)


if __name__ == "__main__":
    main()
