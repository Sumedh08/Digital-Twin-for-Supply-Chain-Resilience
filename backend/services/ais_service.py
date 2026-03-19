"""
AIS (Automatic Identification System) Service
Live vessel tracking for cargo ships on India-EU routes.

Uses AISStream.io free WebSocket feed for real-time data.
"""

import asyncio
import json
import websockets
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import random
import math


class VesselType(str, Enum):
    CONTAINER = "container"
    BULK_CARRIER = "bulk_carrier"
    TANKER = "tanker"
    GENERAL_CARGO = "general_cargo"


@dataclass
class VesselPosition:
    """Vessel position data"""
    mmsi: str
    name: str
    vessel_type: VesselType
    lat: float
    lng: float
    speed_knots: float
    heading: float
    destination: str
    eta: str
    last_updated: str


@dataclass
class RouteVessel:
    """Vessel on a specific route"""
    vessel: VesselPosition
    route: str
    progress_pct: float
    estimated_carbon_kg: float


class AISService:
    """
    Real-time AIS vessel tracking service
    
    In production, connects to AISStream.io WebSocket.
    For demo, returns simulated vessel data.
    """
    
    # AISStream.io WebSocket URL
    AISSTREAM_URL = "wss://stream.aisstream.io/v0/stream"
    
    # Areas of interest for filtering
    BOUNDING_BOXES = {
        "indian_ocean": {
            "lat_min": -10,
            "lat_max": 25,
            "lng_min": 50,
            "lng_max": 95
        },
        "red_sea": {
            "lat_min": 12,
            "lat_max": 30,
            "lng_min": 32,
            "lng_max": 45
        },
        "mediterranean": {
            "lat_min": 30,
            "lat_max": 45,
            "lng_min": -5,
            "lng_max": 35
        },
        "north_sea": {
            "lat_min": 48,
            "lat_max": 60,
            "lng_min": -5,
            "lng_max": 10
        }
    }
    
    # Simulated vessels for demo
    SIMULATED_VESSELS = [
        {
            "mmsi": "419001234",
            "name": "TATA TRIUMPH",
            "vessel_type": VesselType.BULK_CARRIER,
            "route": "INMUN_NLRTM_SUEZ",
            "origin": {"lat": 18.94, "lng": 72.82},
            "destination": {"lat": 51.90, "lng": 4.50},
            "cargo": "Steel coils",
            "cargo_weight_tonnes": 45000
        },
        {
            "mmsi": "419005678",
            "name": "JSW GLORY",
            "vessel_type": VesselType.CONTAINER,
            "route": "INMUN_DEHAM_SUEZ",
            "origin": {"lat": 22.84, "lng": 69.72},
            "destination": {"lat": 53.55, "lng": 9.99},
            "cargo": "Steel products",
            "cargo_weight_tonnes": 32000
        },
        {
            "mmsi": "419009012",
            "name": "HINDALCO EXPRESS",
            "vessel_type": VesselType.BULK_CARRIER,
            "route": "INPRT_NLRTM_SUEZ",
            "origin": {"lat": 20.27, "lng": 86.62},
            "destination": {"lat": 51.90, "lng": 4.50},
            "cargo": "Aluminium ingots",
            "cargo_weight_tonnes": 28000
        },
        {
            "mmsi": "538001111",
            "name": "MAERSK MUMBAI",
            "vessel_type": VesselType.CONTAINER,
            "route": "INMUN_NLRTM_IMEC",
            "origin": {"lat": 18.94, "lng": 72.82},
            "destination": {"lat": 51.90, "lng": 4.50},
            "cargo": "Mixed steel",
            "cargo_weight_tonnes": 38000
        },
        {
            "mmsi": "419002222",
            "name": "NALCO NAVIGATOR",
            "vessel_type": VesselType.BULK_CARRIER,
            "route": "INVTZ_BEANR_SUEZ",
            "origin": {"lat": 17.69, "lng": 83.22},
            "destination": {"lat": 51.22, "lng": 4.40},
            "cargo": "Aluminium",
            "cargo_weight_tonnes": 35000
        },
        {
            "mmsi": "419003333",
            "name": "VEDANTA VOYAGER",
            "vessel_type": VesselType.BULK_CARRIER,
            "route": "INPRT_DEHAM_SUEZ",
            "origin": {"lat": 20.27, "lng": 86.62},
            "destination": {"lat": 53.55, "lng": 9.99},
            "cargo": "Aluminium products",
            "cargo_weight_tonnes": 42000
        }
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._vessels: Dict[str, VesselPosition] = {}
        self._callbacks: List[Callable] = []
    
    def _interpolate_position(self, origin: Dict, destination: Dict, progress: float) -> Dict:
        """
        Interpolate vessel position along great circle route
        
        Args:
            origin: {lat, lng}
            destination: {lat, lng}
            progress: 0.0 to 1.0
            
        Returns:
            {lat, lng} of current position
        """
        lat = origin["lat"] + (destination["lat"] - origin["lat"]) * progress
        lng = origin["lng"] + (destination["lng"] - origin["lng"]) * progress
        
        # Add some realistic variation
        lat += random.uniform(-0.1, 0.1)
        lng += random.uniform(-0.1, 0.1)
        
        return {"lat": round(lat, 4), "lng": round(lng, 4)}
    
    def _calculate_heading(self, origin: Dict, destination: Dict) -> float:
        """Calculate heading in degrees"""
        lat1, lng1 = math.radians(origin["lat"]), math.radians(origin["lng"])
        lat2, lng2 = math.radians(destination["lat"]), math.radians(destination["lng"])
        
        dLng = lng2 - lng1
        x = math.sin(dLng) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLng)
        
        heading = math.degrees(math.atan2(x, y))
        return (heading + 360) % 360
    
    def _estimate_carbon(self, weight_tonnes: float, distance_km: float) -> float:
        """Estimate carbon emissions for voyage"""
        # Sea transport: ~8-16 gCO2/tonne-km for bulk carriers
        emission_factor = 10.0  # gCO2/tonne-km average
        return weight_tonnes * distance_km * emission_factor / 1000  # Return in kg
    
    def get_simulated_vessels(self) -> List[RouteVessel]:
        """
        Get simulated vessels for demo
        
        Returns:
            List of RouteVessel objects
        """
        vessels = []
        now = datetime.now()
        
        for i, ship in enumerate(self.SIMULATED_VESSELS):
            # Simulate different progress for each vessel
            # Based on current time to make it dynamic
            base_progress = (now.hour * 60 + now.minute) / (24 * 60)
            progress = (base_progress + i * 0.15) % 1.0
            
            pos = self._interpolate_position(
                ship["origin"],
                ship["destination"],
                progress
            )
            
            heading = self._calculate_heading(ship["origin"], ship["destination"])
            
            # Estimate ETA based on progress
            total_days = 18 if "SUEZ" in ship["route"] else 28
            remaining_days = total_days * (1 - progress)
            eta = (now + timedelta(days=remaining_days)).strftime("%Y-%m-%d %H:%M")
            
            vessel = VesselPosition(
                mmsi=ship["mmsi"],
                name=ship["name"],
                vessel_type=ship["vessel_type"],
                lat=pos["lat"],
                lng=pos["lng"],
                speed_knots=round(12 + random.uniform(-2, 2), 1),
                heading=round(heading, 1),
                destination=ship["destination"]["lat"],
                eta=eta,
                last_updated=now.isoformat()
            )
            
            # Route distance estimate
            route_distance_km = {
                "INMUN_NLRTM_SUEZ": 11735,
                "INMUN_DEHAM_SUEZ": 11296,
                "INMUN_NLRTM_IMEC": 10742,
                "INPRT_NLRTM_SUEZ": 15002,
                "INVTZ_BEANR_SUEZ": 14500,
                "INPRT_DEHAM_SUEZ": 14500
            }.get(ship["route"], 12000)
            
            carbon_kg = self._estimate_carbon(
                ship["cargo_weight_tonnes"],
                route_distance_km * progress
            )
            
            route_vessel = RouteVessel(
                vessel=vessel,
                route=ship["route"],
                progress_pct=round(progress * 100, 1),
                estimated_carbon_kg=round(carbon_kg, 0)
            )
            
            vessels.append(route_vessel)
        
        return vessels
    
    def get_vessels_geojson(self) -> Dict:
        """
        Get vessels in GeoJSON format for map display
        
        Returns:
            GeoJSON FeatureCollection
        """
        vessels = self.get_simulated_vessels()
        
        features = []
        for rv in vessels:
            v = rv.vessel
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [v.lng, v.lat]
                },
                "properties": {
                    "mmsi": v.mmsi,
                    "name": v.name,
                    "vessel_type": v.vessel_type,
                    "speed": v.speed_knots,
                    "heading": v.heading,
                    "route": rv.route,
                    "progress": rv.progress_pct,
                    "carbon_kg": rv.estimated_carbon_kg,
                    "eta": v.eta
                }
            }
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "generated_at": datetime.now().isoformat()
        }
    
    async def connect_live(self, on_message: Callable[[VesselPosition], None]):
        """
        Connect to live AIS stream
        
        Args:
            on_message: Callback function for new vessel positions
        """
        if not self.api_key:
            print("AIS API key not configured. Using simulated data.")
            return
        
        try:
            async with websockets.connect(self.AISSTREAM_URL) as ws:
                # Subscribe to vessel types and bounding boxes
                subscribe_message = {
                    "APIKey": self.api_key,
                    "BoundingBoxes": [
                        list(self.BOUNDING_BOXES["indian_ocean"].values()),
                        list(self.BOUNDING_BOXES["red_sea"].values()),
                        list(self.BOUNDING_BOXES["mediterranean"].values()),
                    ],
                    "FilterMessageTypes": ["PositionReport"]
                }
                
                await ws.send(json.dumps(subscribe_message))
                
                async for message in ws:
                    data = json.loads(message)
                    if "PositionReport" in data:
                        # Parse and callback
                        pos = self._parse_ais_message(data)
                        if pos:
                            on_message(pos)
        except Exception as e:
            print(f"AIS connection error: {e}")
    
    def _parse_ais_message(self, data: Dict) -> Optional[VesselPosition]:
        """Parse raw AIS message to VesselPosition"""
        try:
            report = data["Message"]["PositionReport"]
            meta = data["MetaData"]
            
            return VesselPosition(
                mmsi=str(meta.get("MMSI", "")),
                name=meta.get("ShipName", "Unknown"),
                vessel_type=VesselType.GENERAL_CARGO,
                lat=report.get("Latitude", 0),
                lng=report.get("Longitude", 0),
                speed_knots=report.get("Sog", 0),
                heading=report.get("Cog", 0),
                destination="",
                eta="",
                last_updated=datetime.now().isoformat()
            )
        except Exception:
            return None


# Create singleton instance
ais_service = AISService()


def get_live_vessels() -> List[Dict]:
    """Get list of live vessels as dictionaries"""
    vessels = ais_service.get_simulated_vessels()
    return [
        {
            "mmsi": rv.vessel.mmsi,
            "name": rv.vessel.name,
            "vessel_type": rv.vessel.vessel_type.value,
            "lat": rv.vessel.lat,
            "lng": rv.vessel.lng,
            "speed_knots": rv.vessel.speed_knots,
            "heading": rv.vessel.heading,
            "route": rv.route,
            "progress_pct": rv.progress_pct,
            "carbon_kg": rv.estimated_carbon_kg,
            "eta": rv.vessel.eta
        }
        for rv in vessels
    ]


if __name__ == "__main__":
    print("=" * 50)
    print("AIS SERVICE TEST")
    print("=" * 50)
    
    vessels = ais_service.get_simulated_vessels()
    
    for rv in vessels:
        print(f"\n🚢 {rv.vessel.name}")
        print(f"   Route: {rv.route}")
        print(f"   Position: {rv.vessel.lat}°N, {rv.vessel.lng}°E")
        print(f"   Speed: {rv.vessel.speed_knots} knots")
        print(f"   Progress: {rv.progress_pct}%")
        print(f"   Est. Carbon: {rv.estimated_carbon_kg:,.0f} kg CO2")
        print(f"   ETA: {rv.vessel.eta}")
    
    print("\n" + "=" * 50)
    print("GEOJSON OUTPUT")
    print("=" * 50)
    geojson = ais_service.get_vessels_geojson()
    print(f"Features: {len(geojson['features'])}")
