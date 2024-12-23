from dataclasses import dataclass


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
