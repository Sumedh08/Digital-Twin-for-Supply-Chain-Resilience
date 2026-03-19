import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict
from groq import Groq

ROUTE_DATA = {
    "mumbai_rotterdam_suez": {
        "name": "Mumbai → Rotterdam (Suez Canal)",
        "waypoints": ["Arabian Sea", "Gulf of Aden", "Red Sea", "Suez Canal", "Mediterranean Sea", "Strait of Gibraltar", "English Channel"],
        "chokepoints": ["Bab el-Mandeb Strait", "Suez Canal"],
        "risk_zones": ["Red Sea (Houthi activity)", "Gulf of Aden (Piracy)", "Suez Canal (Congestion)"],
        "distance_nm": 6337,
        "typical_days": 18,
        "alternative": "mumbai_rotterdam_cape"
    },
    "mumbai_rotterdam_cape": {
        "name": "Mumbai → Rotterdam (Cape of Good Hope)",
        "waypoints": ["Arabian Sea", "Indian Ocean", "Mozambique Channel", "Cape of Good Hope", "South Atlantic", "English Channel"],
        "chokepoints": ["Mozambique Channel"],
        "risk_zones": ["Mozambique Channel (Piracy)", "South Atlantic (Weather)"],
        "distance_nm": 10750,
        "typical_days": 28,
        "alternative": "mumbai_rotterdam_suez"
    },
    "mumbai_rotterdam_imec": {
        "name": "Mumbai → Rotterdam (IMEC Corridor)",
        "waypoints": ["Arabian Sea", "Jebel Ali (UAE)", "Rail: UAE to Israel", "Haifa Port", "Mediterranean Sea", "English Channel"],
        "chokepoints": ["Strait of Hormuz"],
        "risk_zones": ["Strait of Hormuz (Iran tensions)", "UAE-Israel Rail (Geopolitical)"],
        "distance_nm": 5800,
        "typical_days": 14,
        "alternative": "mumbai_rotterdam_suez"
    },
    "mumbai_hamburg_suez": {
        "name": "Mumbai → Hamburg (Suez Canal)",
        "waypoints": ["Arabian Sea", "Gulf of Aden", "Red Sea", "Suez Canal", "Mediterranean Sea", "North Sea"],
        "chokepoints": ["Bab el-Mandeb Strait", "Suez Canal"],
        "risk_zones": ["Red Sea (Houthi activity)", "Gulf of Aden (Piracy)"],
        "distance_nm": 6100,
        "typical_days": 18,
        "alternative": "mumbai_rotterdam_cape"
    },
    "chennai_rotterdam_suez": {
        "name": "Chennai → Rotterdam (Suez Canal)",
        "waypoints": ["Bay of Bengal", "Indian Ocean", "Arabian Sea", "Gulf of Aden", "Red Sea", "Suez Canal", "Mediterranean Sea"],
        "chokepoints": ["Bab el-Mandeb Strait", "Suez Canal"],
        "risk_zones": ["Red Sea (Houthi activity)", "Gulf of Aden (Piracy)"],
        "distance_nm": 8100,
        "typical_days": 22,
        "alternative": "mumbai_rotterdam_cape"
    }
}

ROUTE_CODE_MAP = {
    "INMUN_NLRTM_SUEZ": "mumbai_rotterdam_suez",
    "INMUN_NLRTM_CAPE": "mumbai_rotterdam_cape",
    "INMUN_NLRTM_IMEC": "mumbai_rotterdam_imec",
    "INMUN_DEHAM_SUEZ": "mumbai_hamburg_suez",
    "INMAA_NLRTM_SUEZ": "chennai_rotterdam_suez"
}

class RouteAnalyst:
    CACHE_TTL_MINUTES = 10
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        self._cache = {}
        if self.api_key:
            self.client = Groq(api_key=self.api_key)
            print("✅ Groq (Route Analyst) initialized")

    def _is_cache_valid(self, route_key: str) -> bool:
        if route_key not in self._cache:
            return False
        _, timestamp = self._cache[route_key]
        return datetime.now() - timestamp < timedelta(minutes=self.CACHE_TTL_MINUTES)

    async def analyze_route(self, route_code: str, ship_type: str = "Container Ship", force: bool = False) -> Dict:
        route_key = ROUTE_CODE_MAP.get(route_code, "mumbai_rotterdam_suez")
        route_info = ROUTE_DATA.get(route_key, ROUTE_DATA["mumbai_rotterdam_suez"])
        
        if not force and self._is_cache_valid(route_key):
            cached_result, _ = self._cache[route_key]
            result = cached_result.copy()
            result["cached"] = True
            return result

        if self.client:
            try:
                return await self._analyze_with_groq(route_key, route_info, ship_type)
            except Exception as e:
                print(f"Groq Error (Route Analyst): {e}")
                return self._get_mock_analysis(route_key, route_info, ship_type)
        else:
            return self._get_mock_analysis(route_key, route_info, ship_type)

    async def _analyze_with_groq(self, route_key: str, route_info: Dict, ship_type: str) -> Dict:
        prompt = f"""You are a Maritime Risk Intelligence Analyst. Analyze CURRENT risks for this route:
ROUTE: {route_info['name']}
SHIP: {ship_type}
WAYPOINTS: {', '.join(route_info['waypoints'])}
CHOKEPOINTS: {', '.join(route_info['chokepoints'])}
RISKZONES: {', '.join(route_info['risk_zones'])}

Respond EXACTLY in this JSON format ONLY:
{{
    "overall_risk_score": 65,
    "risk_level": "HIGH",
    "risks": [
        {{"category": "SECURITY", "zone": "Red Sea", "severity": "HIGH", "description": "Houthi attacks"}}
    ],
    "recommendation": "Use Cape route.",
    "should_reroute": true,
    "alternative_route": "Cape of Good Hope"
}}"""

        print(f"🤖 Calling Groq for route analysis: {route_info['name']}...")
        
        completion = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        response_text = completion.choices[0].message.content
        import re
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            response_text = match.group(0)
        analysis = json.loads(response_text)

        result = {
            "route_name": route_info["name"],
            "route_code": [k for k, v in ROUTE_CODE_MAP.items() if v == route_key][0],
            "ship_type": ship_type,
            "distance_nm": route_info["distance_nm"],
            "typical_days": route_info["typical_days"],
            "waypoints": route_info["waypoints"],
            "chokepoints": route_info["chokepoints"],
            "analysis": analysis,
            "alternative": self._get_alternative_info(route_info.get("alternative")),
            "timestamp": datetime.now().isoformat(),
            "source": "Groq LLaMA 3.3 70B (Real-time Analysis)",
            "cached": False
        }

        self._cache[route_key] = (result, datetime.now())
        return result

    def _get_mock_analysis(self, route_key: str, route_info: Dict, ship_type: str) -> Dict:
        # Simplistic fallback
        analysis = {
            "overall_risk_score": 72,
            "risk_level": "HIGH",
            "risks": [{"category": "SECURITY", "zone": route_info["risk_zones"][0] if route_info["risk_zones"] else "Zone", "severity": "HIGH", "description": "Elevated risks"}],
            "recommendation": "Exercise caution.",
            "should_reroute": True,
            "alternative_route": "Cape of Good Hope"
        }
        result = {
            "route_name": route_info["name"],
            "route_code": [k for k, v in ROUTE_CODE_MAP.items() if v == route_key][0],
            "ship_type": ship_type,
            "distance_nm": route_info["distance_nm"],
            "typical_days": route_info["typical_days"],
            "waypoints": route_info["waypoints"],
            "chokepoints": route_info["chokepoints"],
            "analysis": analysis,
            "alternative": self._get_alternative_info(route_info.get("alternative")),
            "timestamp": datetime.now().isoformat(),
            "source": "CarbonShip Intelligence (Simulated)",
            "cached": False
        }
        self._cache[route_key] = (result, datetime.now())
        return result

    def _get_alternative_info(self, alt_key: Optional[str]) -> Optional[Dict]:
        if not alt_key or alt_key not in ROUTE_DATA:
            return None
        alt = ROUTE_DATA[alt_key]
        return {"name": alt["name"], "distance_nm": alt["distance_nm"], "typical_days": alt["typical_days"]}

route_analyst = RouteAnalyst()
