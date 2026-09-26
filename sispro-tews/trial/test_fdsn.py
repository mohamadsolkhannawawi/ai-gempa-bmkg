from fastapi import FastAPI
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
import json

app = FastAPI()

# Example data structure for earthquake events
class Event(BaseModel):
    id: str
    time: datetime
    latitude: float
    longitude: float
    depth: float
    magnitude: float

# Example in-memory database for demonstration
events_db = [
    {
        "id": "eq1",
        "time": datetime(2020, 1, 1, 12, 0),
        "latitude": -3.14,
        "longitude": 42.0,
        "depth": 10.0,
        "magnitude": 5.5,
    }
]

@app.get("/events/")
def read_events(starttime: Optional[datetime] = None, endtime: Optional[datetime] = None):
    if starttime and endtime:
        # Filter events based on the provided starttime and endtime
        filtered_events = [
            event for event in events_db if starttime <= event["time"] <= endtime
        ]
        return filtered_events
    return events_db

@app.get("/events/{event_id}")
def read_event(event_id: str):
    # Retrieve a specific event by ID
    event = next((event for event in events_db if event["id"] == event_id), None)
    if event:
        return event
    return {"message": "Event not found"}, 404
