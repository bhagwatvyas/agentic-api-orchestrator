from __future__ import annotations


def search_flights(origin: str, destination: str) -> dict[str, object]:
    return {
        "origin": origin,
        "destination": destination,
        "options": [
            {"airline": "SkyJet", "price_usd": 320},
            {"airline": "CloudAir", "price_usd": 355},
        ],
    }


def search_hotels(city: str) -> dict[str, object]:
    return {
        "city": city,
        "options": [
            {"name": "Central Suites", "price_per_night_usd": 180},
            {"name": "Harbor Hotel", "price_per_night_usd": 220},
        ],
    }


def get_weather(city: str) -> dict[str, object]:
    return {
        "city": city,
        "forecast": "Sunny",
        "temperature_f": 72,
    }
