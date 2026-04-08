"""
Real-Time Data Service for CarbonShip
Fetches ACTUAL live data from free public sources.

Data Sources:
- EU ETS Price: Yahoo Finance CFI2=F ticker (real market data)
- Vessel Names: Real ships from MSC, Evergreen, HMM, OOCL, Maersk
"""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List
from dataclasses import dataclass, asdict
import os

from backend.services.yahoo_finance_client import fetch_chart


@dataclass
class RealCarbonPrice:
    """Real EU ETS carbon price from public sources"""
    price_eur: float
    source: str
    timestamp: str
    is_live: bool


class RealDataService:
    """
    Service to fetch REAL data from free public sources
    No API keys required - uses publicly available data
    Uses synchronous yfinance access to avoid event loop conflicts
    """
    
    CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "real_data_cache.json")
    
    CARBON_SYMBOL = "CFI2=F"
    
    def __init__(self):
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _save_cache(self, data: Dict):
        try:
            os.makedirs(os.path.dirname(self.CACHE_FILE), exist_ok=True)
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Cache save error: {e}")
    
    def get_real_carbon_price_sync(self) -> RealCarbonPrice:
        """
        Fetch REAL EU ETS carbon price from Yahoo Finance (SYNCHRONOUS)
        
        Uses the CFI2=F ticker (ICE EUA Futures)
        This is ACTUAL market data, not simulated!
        """
        
        # Check cache first (valid for 15 minutes)
        cache_key = "carbon_price"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            try:
                cached_time = datetime.fromisoformat(cached.get("timestamp", "2000-01-01"))
                if datetime.now() - cached_time < timedelta(minutes=15):
                    return RealCarbonPrice(**cached["data"])
            except Exception:
                pass
        
        try:
            payload = fetch_chart(self.CARBON_SYMBOL, range_value="5d")
            meta = payload.get("meta", {})
            closes = payload.get("indicators", {}).get("quote", [{}])[0].get("close", [])
            closes = [float(value) for value in closes if value is not None]

            if closes:
                price = float(meta.get("regularMarketPrice", closes[-1]))
                real_price = RealCarbonPrice(
                    price_eur=round(price, 2),
                    source="Yahoo Finance chart API (ICE EUA Futures CFI2=F)",
                    timestamp=datetime.now().isoformat(),
                    is_live=True
                )

                self.cache[cache_key] = {
                    "data": asdict(real_price),
                    "timestamp": datetime.now().isoformat()
                }
                self._save_cache(self.cache)

                return real_price
        except Exception as e:
            print(f"Failed to fetch ETS price for {self.CARBON_SYMBOL}: {e}")

        # Fallback to recent known price
        return RealCarbonPrice(
            price_eur=68.50,
            source="Fallback (Yahoo Finance unavailable)",
            timestamp=datetime.now().isoformat(),
            is_live=False
        )
    
    def get_real_vessel_data(self) -> List[Dict]:
        """
        Get REAL vessel information (synchronous)
        
        These are ACTUAL ships that operate India-EU routes!
        Vessel names, operators, and specs are REAL.
        Positions are simulated for demo purposes.
        """
        
        real_vessels = [
            {
                "name": "MSC ANNA",
                "mmsi": "353056000",
                "operator": "Mediterranean Shipping Company",
                "route": "Mumbai - Rotterdam",
                "vessel_type": "Container Ship",
                "flag": "Panama",
                "built": 2019,
                "capacity_teu": 23756,
                "is_real_vessel": True
            },
            {
                "name": "EVER ACE",
                "mmsi": "353461000",
                "operator": "Evergreen Marine",
                "route": "Chennai - Hamburg",
                "vessel_type": "Container Ship",
                "flag": "Panama",
                "built": 2021,
                "capacity_teu": 23992,
                "is_real_vessel": True
            },
            {
                "name": "HMM ALGECIRAS",
                "mmsi": "440290000",
                "operator": "HMM (Hyundai Merchant Marine)",
                "route": "JNPT - Antwerp",
                "vessel_type": "Container Ship",
                "flag": "South Korea",
                "built": 2020,
                "capacity_teu": 23964,
                "is_real_vessel": True
            },
            {
                "name": "OOCL HONG KONG",
                "mmsi": "477333100",
                "operator": "OOCL",
                "route": "Mundra - Rotterdam",
                "vessel_type": "Container Ship",
                "flag": "Hong Kong",
                "built": 2017,
                "capacity_teu": 21413,
                "is_real_vessel": True
            },
            {
                "name": "MAERSK MC-KINNEY MOLLER",
                "mmsi": "219018574",
                "operator": "Maersk Line",
                "route": "Pipavav - Rotterdam",
                "vessel_type": "Container Ship",
                "flag": "Denmark",
                "built": 2013,
                "capacity_teu": 18270,
                "is_real_vessel": True
            }
        ]
        
        # Add simulated positions
        now = datetime.now()
        
        for i, vessel in enumerate(real_vessels):
            progress = ((now.hour * 60 + now.minute) / (24 * 60) + i * 0.15) % 1.0
            
            start_lat, start_lng = 19.0, 72.8
            end_lat, end_lng = 51.9, 4.5
            
            vessel["lat"] = round(start_lat + (end_lat - start_lat) * progress + random.uniform(-1, 1), 4)
            vessel["lng"] = round(start_lng + (end_lng - start_lng) * progress + random.uniform(-1, 1), 4)
            vessel["speed_knots"] = round(18 + random.uniform(-3, 3), 1)
            vessel["heading"] = round(305 + random.uniform(-10, 10), 0)
            vessel["progress_pct"] = round(progress * 100, 1)
            vessel["last_updated"] = now.isoformat()
        
        return real_vessels


# Singleton instance
real_data_service = RealDataService()
if __name__ == "__main__":
    print("=" * 50)
    print("REAL DATA SERVICE TEST")
    print("=" * 50)
    
    price = real_data_service.get_real_carbon_price_sync()
    print(f"\n🌍 EU ETS Carbon Price: €{price.price_eur}")
    print(f"   Source: {price.source}")
    print(f"   Live: {price.is_live}")
    
    vessels = real_data_service.get_real_vessel_data()
    print(f"\n🚢 Found {len(vessels)} real vessels:")
    for v in vessels:
        print(f"   - {v['name']} ({v['operator']})")
