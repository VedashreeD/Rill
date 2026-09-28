"""
The Cindervale Watershed — a small, entirely fictional world of 10 stream
locations used for this demo. None of these are real places; coordinates
are synthetic (a tiny made-up grid, not tied to any real geography).

This is the single source of truth for the world's locations. The API
serves this catalog via GET /api/locations; reports are (for now) randomly
assigned to one of these on submission — see routers/reports.py.
"""

from typing import TypedDict


class WorldLocation(TypedDict):
    code: str
    name: str
    description: str
    illustration: str  # one of ILLUSTRATION_VARIANTS, used by the frontend's LocationArt component
    lat: float
    lng: float


ILLUSTRATION_VARIANTS = ("calm", "rocky", "wooded", "bridge", "wetland")

WORLD_LOCATIONS: list[WorldLocation] = [
    {
        "code": "SEG-01",
        "name": "Millrace Crossing",
        "description": "An old mill bridge over the upper Cindervale creek.",
        "illustration": "bridge",
        "lat": 10.021,
        "lng": 20.014,
    },
    {
        "code": "SEG-02",
        "name": "Hollowmere Landing",
        "description": "A wide, usually-calm pool used as a canoe launch.",
        "illustration": "calm",
        "lat": 10.033,
        "lng": 20.027,
    },
    {
        "code": "SEG-03",
        "name": "Cinderwood Ford",
        "description": "A shallow, rocky ford through a burned-wood grove.",
        "illustration": "rocky",
        "lat": 10.045,
        "lng": 20.041,
    },
    {
        "code": "SEG-04",
        "name": "Thistledown Weir",
        "description": "A small weir just downstream of Cinderwood Ford.",
        "illustration": "wooded",
        "lat": 10.058,
        "lng": 20.052,
    },
    {
        "code": "SEG-05",
        "name": "Quarrystone Bend",
        "description": "A wide bend in the river past a disused quarry.",
        "illustration": "wetland",
        "lat": 10.071,
        "lng": 20.063,
    },
    {
        "code": "SEG-06",
        "name": "Willowmarsh Confluence",
        "description": "Where two tributaries meet in a reedy marsh.",
        "illustration": "calm",
        "lat": 10.084,
        "lng": 20.075,
    },
    {
        "code": "SEG-07",
        "name": "Ashgrove Footbridge",
        "description": "A narrow footbridge through a stand of ash trees.",
        "illustration": "bridge",
        "lat": 10.096,
        "lng": 20.088,
    },
    {
        "code": "SEG-08",
        "name": "Duskwater Overlook",
        "description": "A scenic overlook above a short stretch of rapids.",
        "illustration": "rocky",
        "lat": 10.108,
        "lng": 20.101,
    },
    {
        "code": "SEG-09",
        "name": "Emberfall Sluice",
        "description": "A sluice gate near a stretch of ember-colored cliffs.",
        "illustration": "wooded",
        "lat": 10.121,
        "lng": 20.114,
    },
    {
        "code": "SEG-10",
        "name": "Graymoor Basin",
        "description": "A wide, slow basin just before the river's mouth.",
        "illustration": "wetland",
        "lat": 10.134,
        "lng": 20.127,
    },
]

WORLD_BY_CODE: dict[str, WorldLocation] = {loc["code"]: loc for loc in WORLD_LOCATIONS}
