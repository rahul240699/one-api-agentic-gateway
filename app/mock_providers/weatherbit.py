from typing import Any

import httpx

from app.config import provider_keys
from app.mock_providers.jina import ProviderUnavailable

BASE_URL = "https://api.weatherbit.io/v2.0"


async def current(payload: dict[str, Any]) -> dict[str, Any]:
    """Fetch current weather for a city or lat/lon via Weatherbit."""
    api_key = provider_keys.weatherbit_api_key
    if not api_key:
        raise ProviderUnavailable("Weatherbit API key is not configured on the server.")

    params: dict[str, str] = {"key": api_key}

    if "city" in payload:
        params["city"] = payload["city"]
    elif "lat" in payload and "lon" in payload:
        params["lat"] = str(payload["lat"])
        params["lon"] = str(payload["lon"])
    else:
        raise ValueError("Provide 'city' or 'lat'+'lon'")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(BASE_URL + "/current", params=params)
    except httpx.RequestError as exc:
        raise ProviderUnavailable(f"Weatherbit network error: {exc}") from exc

    if resp.status_code in (401, 403):
        raise ProviderUnavailable("Weatherbit API key is invalid or expired.")
    if resp.status_code == 429:
        raise ProviderUnavailable("Weatherbit rate limit reached — server is out of credits for this API.")
    if resp.status_code >= 400:
        raise ProviderUnavailable(f"Weatherbit returned {resp.status_code}: {resp.text[:200]}")

    body = resp.json()
    obs = body.get("data", [{}])[0]
    weather = obs.get("weather", {})
    return {
        "city": obs.get("city_name", payload.get("city", "")),
        "country": obs.get("country_code", ""),
        "temp_c": obs.get("temp"),
        "feels_like_c": obs.get("app_temp"),
        "humidity_pct": obs.get("rh"),
        "wind_spd_ms": obs.get("wind_spd"),
        "description": weather.get("description", ""),
        "icon": weather.get("icon", ""),
        "uv": obs.get("uv"),
        "aqi": obs.get("aqi"),
        "observed_at": obs.get("ob_time", ""),
    }
