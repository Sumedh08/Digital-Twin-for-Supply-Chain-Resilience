"""
Live AIS Data Service using AISStream.io WebSocket
Real-time vessel tracking with actual ship positions.

API: AISStream.io (WebSocket)
"""

import asyncio
import json
import websockets
from datetime import datetime
from typing import Dict, List, Optional
import os
import threading

# AISStream.io API Key
AISSTREAM_API_KEY = os.getenv("AISSTREAM_API_KEY", "e94bd5fcb4d703ce45ac1c568b360a71b6847664")

class LiveAISService:
    """
    Live AIS data from AISStream.io via WebSocket
    Maintains a real-time cache of vessel positions
    """
    
    def __init__(self, api_key: str = AISSTREAM_API_KEY):
        self.api_key = api_key
        self.vessels: Dict[str, Dict] = {}
        self.running = False
        self._lock = threading.Lock()
        self.max_vessels = 50  # Limit to 50 ships to prevent overload
        
        # Pre-populate with known ships (fallback until live data comes in)
        self._init_fallback_data()

    def _init_fallback_data(self):
        """Initialize with some static data so the map isn't empty initially"""
        fallback_vessels = [
            {"name": "MSC ANNA", "mmsi": "353056000", "operator": "MSC", "lat": 19.0, "lng": 72.8, "route": "Mumbai-Rotterdam"},
            {"name": "EVER ACE", "mmsi": "353461000", "operator": "Evergreen", "lat": 13.1, "lng": 80.3, "route": "Chennai-Hamburg"},
            {"name": "HMM ALGECIRAS", "mmsi": "440290000", "operator": "HMM", "lat": 18.9, "lng": 72.9, "route": "JNPT-Antwerp"},
            {"name": "OOCL HONG KONG", "mmsi": "477333100", "operator": "OOCL", "lat": 22.8, "lng": 69.7, "route": "Mundra-Rotterdam"},
            {"name": "MAERSK MC-KINNEY MOLLER", "mmsi": "219018574", "operator": "Maersk", "lat": 20.9, "lng": 71.5, "route": "Pipavav-Rotterdam"},
        ]
        
        for v in fallback_vessels:
            self.vessels[v["mmsi"]] = {
                **v,
                "speed": 0.0,
                "heading": 0.0,
                "is_live": False,
                "timestamp": datetime.now().isoformat(),
                "note": "Waiting for live signal..."
            }

    async def connect_and_listen(self):
        """Connect to WebSocket and listen for updates"""
        uri = "wss://stream.aisstream.io/v0/stream"
        
        subscribe_message = {
            "APIKey": self.api_key,
            "BoundingBoxes": [[[-40, -20], [65, 100]]], # Covers Europe, Africa, India, Asia
            # Removed FiltersShipMMSI to allow dynamic discovery
            "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
        }

        while self.running:
            try:
                async with websockets.connect(uri) as websocket:
                    print(f"🔌 Connected to AISStream WebSocket")
                    await websocket.send(json.dumps(subscribe_message))
                    
                    async for message_json in websocket:
                        # print(f"DEBUG: Received message: {message_json}")
                        if not self.running:
                            break
                            
                        try:
                            message = json.loads(message_json)
                            msg_type = message.get("MessageType")
                            
                            if msg_type == "PositionReport":
                                ais = message["Message"]["PositionReport"]
                                mmsi = str(ais["UserID"])
                                
                                with self._lock:
                                    # If new ship and we have space, add it
                                    if mmsi not in self.vessels and len(self.vessels) < self.max_vessels:
                                        self.vessels[mmsi] = {
                                            "name": f"Vessel {mmsi}", # Placeholder until StaticData
                                            "mmsi": mmsi,
                                            "lat": ais["Latitude"],
                                            "lng": ais["Longitude"],
                                            "speed": ais.get("Sog", 0),
                                            "heading": ais.get("TrueHeading", 0),
                                            "route": "Unknown Route",
                                            "is_live": True,
                                            "timestamp": datetime.now().isoformat(),
                                            "note": "LIVE via AISStream"
                                        }
                                        print(f"🚢 New Ship Discovered: {mmsi}")
                                    
                                    # Update existing ship
                                    elif mmsi in self.vessels:
                                        self.vessels[mmsi].update({
                                            "lat": ais["Latitude"],
                                            "lng": ais["Longitude"],
                                            "speed": ais.get("Sog", 0),
                                            "heading": ais.get("TrueHeading", 0),
                                            "is_live": True,
                                            "timestamp": datetime.now().isoformat(),
                                            "note": "LIVE via AISStream"
                                        })
                                        # print(f"📍 LIVE UPDATE: {self.vessels[mmsi]['name']}")

                            elif msg_type == "ShipStaticData":
                                ais = message["Message"]["ShipStaticData"]
                                mmsi = str(ais["UserID"])
                                
                                with self._lock:
                                    if mmsi in self.vessels:
                                        name = ais.get("Name", "").strip().replace("@", "")
                                        if name:
                                            self.vessels[mmsi]["name"] = name
                                            # Try to guess route from destination if available
                                            # destination = ais.get("Destination", "")
                                            # if destination:
                                            #    self.vessels[mmsi]["route"] = f"To {destination}"
                                            print(f"🏷️ Updated Name: {name} ({mmsi})")

                        except Exception as e:
                            # print(f"Error parsing AIS message: {e}")
                            pass
                            
            except Exception as e:
                print(f"AIS WebSocket error: {e}")
                await asyncio.sleep(5) # Reconnect delay

    def start_background_task(self):
        """Start the WebSocket listener in a background thread"""
        if self.running:
            return
            
        self.running = True
        
        def run_async_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.connect_and_listen())
            
        thread = threading.Thread(target=run_async_loop, daemon=True)
        thread.start()
        print("🚀 AIS Background Service Started")

    def get_tracked_vessels(self) -> List[Dict]:
        """Get current state of all tracked vessels"""
        with self._lock:
            return list(self.vessels.values())

# Singleton
live_ais_service = LiveAISService()

def get_live_ais_vessels() -> List[Dict]:
    return live_ais_service.get_tracked_vessels()
