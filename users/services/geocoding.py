from functools import lru_cache

import requests
from django.conf import settings


class GeocodingError(Exception):
    """Raised when geocoding is unavailable or fails."""


def _normalize(value: str | None) -> str:
    return (value or "").strip()


@lru_cache(maxsize=512)
def geocode_city(city: str, country: str | None = None) -> dict[str, object]:
    normalized_city = _normalize(city)
    normalized_country = _normalize(country)
    if not normalized_city:
        raise GeocodingError("City is required for geocoding.")

    if not getattr(settings, "GEOCODING_ENABLED", True):
        raise GeocodingError("Geocoding is disabled.")

    api_url = getattr(
        settings,
        "GEOCODING_API_URL",
        "https://nominatim.openstreetmap.org/search",
    )
    timeout = getattr(settings, "GEOCODING_TIMEOUT_SECONDS", 8)
    user_agent = getattr(settings, "GEOCODING_USER_AGENT", "radici-rotariane/1.0")

    query = normalized_city if not normalized_country else f"{normalized_city}, {normalized_country}"
    params = {
        "q": query,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 1,
    }
    headers = {"User-Agent": user_agent}

    try:
        response = requests.get(api_url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise GeocodingError("Geocoding request failed.") from exc
    except ValueError as exc:
        raise GeocodingError("Invalid geocoding response.") from exc

    if not payload:
        raise GeocodingError("Location not found.")

    item = payload[0]
    try:
        latitude = float(item["lat"])
        longitude = float(item["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise GeocodingError("Geocoding did not return coordinates.") from exc

    address = item.get("address") or {}
    resolved_city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or normalized_city
    )
    resolved_country = address.get("country") or normalized_country
    if not resolved_country:
        raise GeocodingError("Geocoding did not return country.")

    return {
        "city": resolved_city,
        "country": resolved_country,
        "latitude": latitude,
        "longitude": longitude,
    }
