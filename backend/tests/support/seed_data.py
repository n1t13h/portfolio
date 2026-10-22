"""A small seed file in the shape scripts/export-curation.mjs produces."""

from typing import Any

SEED: dict[str, Any] = {
    "photos": [
        {
            "id": "a",
            "pid": "p-a",
            "aspectRatio": 1.5,
            "title": "Photo A",
            "place": "Ram Ghat, Ujjain",
            "exif": {"camera": "Sony ZV-E10", "focalLength": 38, "iso": 640},
            "unsplashUrl": "https://unsplash.com/photos/a",
        },
        {"id": "b", "pid": "p-b", "aspectRatio": 1.5, "title": "Photo B", "unsplashUrl": "u/b"},
        {"id": "c", "pid": "p-c", "aspectRatio": 1.5, "title": "Photo C", "unsplashUrl": "u/c"},
    ],
    "order": ["c", "a", "b"],
    "excluded": [],
    "collections": [
        {
            "slug": "ujjain",
            "title": "Ujjain",
            "place": "Madhya Pradesh",
            "year": "2024",
            "intro": "Intro",
            "coverIds": ["a", "c"],
            "chapters": [
                {"title": "One", "note": "First", "photoIds": ["a", "b"]},
                {"title": "Two", "note": "Second", "photoIds": ["c"]},
            ],
        }
    ],
}
