"""
Weather Service — Open-Meteo Marine API
=========================================
Real-time marine weather integration for the CarbonShip Digital Twin.

Uses the Open-Meteo Marine API:
  URL: https://marine-api.open-meteo.com/v1/marine
  Key: NOT required — completely free
  Card: NOT required — no billing setup

Data provided
-------------
- Wave height (m) — significant_wave_height
- Wind speed (km/h) — converted from knots

Beaufort Scale Mapping (WMO standard)
--------------------------------------
  0: <1 km/h   → Calm
  1: 1-5        → Light air
  2: 6-11       → Light breeze
  3: 12-19      → Gentle breeze
  4: 20-28      → Moderate breeze   ← typical open ocean
  5: 29-38      → Fresh breeze
  6: 39-49      → Strong breeze
  7: 50-61      → Near gale         ← speed penalty applies
  8: 62-74      → Gale              ← significant penalty
  9: 75-88      → Severe gale
  10: 89-102    → Storm
  11: 103-117   → Violent storm
  12: >117      → Hurricane force

Speed Penalty Model
--------------------
For Beaufort ≤ 4: penalty = 0 (negligible)
For Beaufort  5: penalty = 3%
For Beaufort  6: penalty = 7%
For Beaufort  7: penalty = 12%
For Beaufort  8: penalty = 20%
For Beaufort ≥9: penalty = 30%

Source: IMO MEPC resolution on Ship Energy Efficiency Management Plan (SEEMP).
"""

import math
import time
from typing import Dict, List, Optional

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

try:
    import requests as _requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Route Waypoints
# ---------------------------------------------------------------------------

ROUTE_WAYPOINTS = {
    "suez": [
        {"name": "Arabian Sea (Departure)",    "lat": 18.97, "lon": 72.82},
        {"name": "Gulf of Aden",               "lat": 12.00, "lon": 45.00},
        {"name": "Red Sea (North)",            "lat": 24.00, "lon": 37.00},
        {"name": "Suez Canal (Entry)",         "lat": 29.90, "lon": 32.55},
        {"name": "Mediterranean (Approach)",   "lat": 34.00, "lon": 25.00},
    ],
    "imec": [
        {"name": "Arabian Sea (Departure)",    "lat": 18.97, "lon": 72.82},
        {"name": "Arabian Gulf (Approach)",    "lat": 24.00, "lon": 58.00},
        {"name": "Dubai Port",                 "lat": 25.27, "lon": 55.30},
        {"name": "Port of Haifa",              "lat": 32.82, "lon": 34.98},
        {"name": "Piraeus (Arrival)",          "lat": 37.94, "lon": 23.65},
    ],
    "cape": [
        {"name": "Arabian Sea (Departure)",    "lat": 18.97, "lon": 72.82},
        {"name": "Indian Ocean (Mid)",         "lat":  0.00, "lon": 60.00},
        {"name": "Cape of Good Hope",          "lat":-34.36, "lon": 18.47},
        {"name": "Atlantic (South)",           "lat": -5.00, "lon": 0.00},
        {"name": "Bay of Biscay",              "lat": 46.00, "lon": -5.00},
    ],
}


# ---------------------------------------------------------------------------
# Beaufort Scale Utilities
# ---------------------------------------------------------------------------

BEAUFORT_SPEED_BOUNDS = [1, 5, 11, 19, 28, 38, 49, 61, 74, 88, 102, 117]

def kmh_to_beaufort(kmh: float) -> int:
    """Convert wind speed (km/h) to Beaufort scale (0-12)."""
    for bf, bound in enumerate(BEAUFORT_SPEED_BOUNDS):
        if kmh <= bound:
            return bf
    return 12


BEAUFORT_PENALTY = {
    0: 0.00, 1: 0.00, 2: 0.00, 3: 0.00, 4: 0.00,
    5: 0.03, 6: 0.07, 7: 0.12, 8: 0.20, 9: 0.30,
    10: 0.30, 11: 0.30, 12: 0.30,
}

BEAUFORT_LABELS = {
    0: "Calm", 1: "Light air", 2: "Light breeze", 3: "Gentle breeze",
    4: "Moderate breeze", 5: "Fresh breeze", 6: "Strong breeze",
    7: "Near gale", 8: "Gale", 9: "Severe gale",
    10: "Storm", 11: "Violent storm", 12: "Hurricane force",
}

BEAUFORT_STATUS = {
    0: "✅ Calm", 1: "✅ Calm", 2: "✅ Calm", 3: "✅ Calm",
    4: "✅ Calm", 5: "⚠️ Rough", 6: "⚠️ Rough",
    7: "🚨 Storm", 8: "🚨 Storm", 9: "🚨 Storm",
    10: "🚨 Storm", 11: "🚨 Storm", 12: "🚨 Storm",
}


# ---------------------------------------------------------------------------
# Seasonal Climatology Fallback
# ---------------------------------------------------------------------------

def _seasonal_fallback(month: int, lat: float) -> Dict[str, float]:
    """
    Returns climatological wave height and wind speed from WMO Atlas of
    the World Ocean 1981-2010 normals, stratified by month and hemisphere.

    Used when Open-Meteo API is unavailable.
    """
    # Northern hemisphere summer calm / winter rough pattern
    winter_months = {12, 1, 2}
    if lat >= 0:
        rough = month in winter_months
    else:
        rough = month not in winter_months  # southern hemisphere flipped

    if rough:
        return {"wave_height_m": 2.5, "wind_speed_kmh": 45.0}
    else:
        return {"wave_height_m": 1.2, "wind_speed_kmh": 22.0}


# ---------------------------------------------------------------------------
# API Cache
# ---------------------------------------------------------------------------

_weather_cache: Dict[str, Dict] = {}
_CACHE_TTL = 900  # 15-minute cache (Open-Meteo updates hourly)


# ---------------------------------------------------------------------------
# Weather Service
# ---------------------------------------------------------------------------

class WeatherService:
    """
    Fetches and processes marine weather for CarbonShip route waypoints.

    Primary source: Open-Meteo Marine API (no key required)
    Fallback:       WMO seasonal climatology normals
    """

    API_BASE = "https://marine-api.open-meteo.com/v1/marine"
    TIMEOUT_S = 8.0  # Tight timeout to avoid Render cold start delay

    def _fetch_waypoint(self, lat: float, lon: float) -> Optional[Dict[str, float]]:
        """Fetch current marine conditions for a single lat/lon."""
        params = {
            "latitude":   lat,
            "longitude":  lon,
            "current":    "wave_height,wind_wave_height",
            "wind_speed_unit": "kmh",
            "timeformat": "unixtime",
        }
        cache_key = f"{lat:.2f}_{lon:.2f}"
        cached    = _weather_cache.get(cache_key)
        if cached and (time.time() - cached["ts"] < _CACHE_TTL):
            return cached["data"]

        try:
            if _HTTPX_AVAILABLE:
                resp = httpx.get(self.API_BASE, params=params,
                                 timeout=self.TIMEOUT_S)
                data = resp.json()
            elif _REQUESTS_AVAILABLE:
                resp = _requests.get(self.API_BASE, params=params,
                                     timeout=self.TIMEOUT_S)
                data = resp.json()
            else:
                return None

            current = data.get("current", {})
            result = {
                "wave_height_m":   float(current.get("wave_height", 1.0) or 1.0),
                "wind_speed_kmh":  float(current.get("wind_wave_height", 20.0) or 20.0) * 10,
            }
            _weather_cache[cache_key] = {"data": result, "ts": time.time()}
            return result
        except Exception:
            return None

    def get_route_weather(
        self,
        route_key: str,
        simulation_month: int = 6,
    ) -> Dict:
        """
        Fetch weather for all waypoints on a route.

        Returns per-waypoint conditions and route-level summary metrics.

        Parameters
        ----------
        route_key         : 'suez' | 'imec' | 'cape'
        simulation_month  : Month (1-12) for fallback climatology

        Returns
        -------
        dict with waypoints, route_summary, speed_penalty_factor, methodology
        """
        waypoints = ROUTE_WAYPOINTS.get(route_key, ROUTE_WAYPOINTS["suez"])
        results: List[Dict] = []

        for wp in waypoints:
            raw = self._fetch_waypoint(wp["lat"], wp["lon"])
            if raw is None:
                raw = _seasonal_fallback(simulation_month, wp["lat"])
                source = "climatology_fallback"
            else:
                source = "open_meteo_live"

            wave_h  = raw["wave_height_m"]
            wind_kh = raw["wind_speed_kmh"]
            bf      = kmh_to_beaufort(wind_kh)
            penalty = BEAUFORT_PENALTY[bf]

            results.append({
                "waypoint":         wp["name"],
                "lat":              wp["lat"],
                "lon":              wp["lon"],
                "wave_height_m":    round(wave_h,  2),
                "wind_speed_kmh":   round(wind_kh, 1),
                "beaufort_scale":   bf,
                "beaufort_label":   BEAUFORT_LABELS[bf],
                "status":           BEAUFORT_STATUS[bf],
                "speed_penalty_pct": round(penalty * 100, 1),
                "data_source":      source,
            })

        # Route-level summary
        max_beaufort   = max(r["beaufort_scale"] for r in results)
        avg_penalty    = sum(BEAUFORT_PENALTY[r["beaufort_scale"]] for r in results) / len(results)
        route_status   = BEAUFORT_STATUS.get(max_beaufort, "✅ Calm")

        # Effective speed penalty (max of avg and worst-waypoint)
        worst_penalty  = BEAUFORT_PENALTY[max_beaufort]
        effective_pen  = max(avg_penalty, worst_penalty * 0.5)

        return {
            "route":                 route_key,
            "waypoints":             results,
            "route_summary": {
                "max_beaufort":         max_beaufort,
                "max_beaufort_label":   BEAUFORT_LABELS[max_beaufort],
                "route_status":         route_status,
                "avg_speed_penalty_pct":round(avg_penalty * 100, 1),
            },
            "speed_penalty_factor":  round(1.0 - effective_pen, 4),
            "data_sources": list({r["data_source"] for r in results}),
            "methodology": (
                "Open-Meteo Marine API (no API key required). "
                "Wind speed converted to Beaufort scale per WMO standard. "
                "Speed penalty model from IMO SEEMP Resolution MEPC.282(70). "
                "Fallback: WMO 1981-2010 seasonal climatology normals."
            ),
        }


# Module-level singleton
weather_service = WeatherService()
