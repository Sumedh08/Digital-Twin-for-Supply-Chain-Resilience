import os
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from groq import Groq

class AISentinel:
    CACHE_TTL_MINUTES = 10
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        self._cache = None
        self._cache_time = None
        if self.api_key:
            self.client = Groq(api_key=self.api_key)
            print("✅ Groq (Sentinel RSS) initialized")
        else:
            print("⚠️ No GROQ_API_KEY found. AI Sentinel running in MOCK mode.")

    def _is_cache_valid(self):
        if self._cache is None or self._cache_time is None:
            return False
        return datetime.now() - self._cache_time < timedelta(minutes=self.CACHE_TTL_MINUTES)

    def get_live_news_rss(self, query: str) -> str:
        """Highly reliable scraper using Google News RSS, completely immune to standard DDG/Bing rate-limits."""
        try:
            encoded_query = urllib.parse.quote(query + " shipping maritime supply chain")
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                xml_data = response.read()
                
            root = ET.fromstring(xml_data)
            news_items = []
            # Extract top 3 news items
            for item in root.findall('./channel/item')[:3]:
                title = item.find('title').text
                pubDate = item.find('pubDate').text
                news_items.append(f"- [{pubDate}] {title}")
                
            if news_items:
                return "\n".join(news_items)
            return "No recent news found."
        except Exception as e:
            print(f"Google News RSS Failed: {e}")
            return "No internet connection or news blocked."

    async def analyze_risk(self, route="India-Europe", context="Red Sea", force=False):
        if not force and self._is_cache_valid():
            cached = self._cache.copy()
            cached["timestamp"] = datetime.now().isoformat()
            cached["source"] = cached.get("source", "Cached") + " (Cached)"
            return cached
        
        live_news = self.get_live_news_rss(context)
        
        if not self.client:
            # Enhanced Mock with Comparative Data
            result = {
                "risk_score": 85,
                "risk_level": "HIGH",
                "safety_category": "DANGEROUS",
                "summary": f"Simulated based on context. Live News: {live_news[:100]}...",
                "recommendation": "Reroute via Cape of Good Hope immediately.",
                "comparison": [
                    {"route": "Suez Canal", "risk_score": 92, "category": "EXTREME", "status": "Active Conflict"},
                    {"route": "IMEC Corridor", "risk_score": 45, "category": "CAUTION", "status": "Geopolitical Tension"},
                    {"route": "Cape Route", "risk_score": 15, "category": "SAFE", "status": "Stable but Slow"}
                ],
                "timestamp": datetime.now().isoformat(),
                "source": "Mock AI + RSS Search"
            }
            self._cache = result
            self._cache_time = datetime.now()
            return result

        try:
            print(f"🤖 Calling Groq API for COMPARATIVE {context} analysis...")
            prompt = f"""
            You are a Maritime Security Analyst. Analyze and COMPARE the risk for the following major corridors between India and Europe:
            1. Suez Canal Route (via Red Sea)
            2. IMEC Corridor (Land-Sea bridge via UAE-Israel)
            3. Cape of Good Hope (Detour around Africa)

            Here is the absolute latest LIVE NEWS from the internet:
            {live_news}
            
            Synthesize this live data and provide a JSON response ONLY:
            {{
                "risk_score": <overall_max_integer 0-100>,
                "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
                "safety_category": "<SAFE|CAUTION|RISKY|DANGEROUS|EXTREME>",
                "comparison": [
                    {{
                        "route": "Suez Canal",
                        "risk_score": <0-100>,
                        "category": "<SAFE|CAUTION|RISKY|DANGEROUS|EXTREME>",
                        "status": "<e.g., Congested, Volatile, Stable>"
                    }},
                    {{
                        "route": "IMEC Corridor",
                        "risk_score": <0-100>,
                        "category": "<SAFE|CAUTION|RISKY|DANGEROUS|EXTREME>",
                        "status": "<e.g., Stable, Tense, Developing>"
                    }},
                    {{
                        "route": "Cape Route",
                        "risk_score": <0-100>,
                        "category": "<SAFE|CAUTION|RISKY|DANGEROUS|EXTREME>",
                        "status": "<e.g., Safe, Slow, Weather-prone>"
                    }}
                ],
                "summary": "<2 sentences max integrating the live news and explaining the primary threat>",
                "recommendation": "<Actionable advice on which route is objectively best right now>"
            }}
            """
            
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            content = completion.choices[0].message.content
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                content = match.group(0)
                
            parsed = json.loads(content)
            
            result = {
                "risk_score": parsed.get("risk_score", 75),
                "risk_level": parsed.get("risk_level", "HIGH"),
                "safety_category": parsed.get("safety_category", "RISKY"),
                "comparison": parsed.get("comparison", []),
                "summary": parsed.get("summary", "Analysis completed."),
                "recommendation": parsed.get("recommendation", "Exercise caution."),
                "timestamp": datetime.now().isoformat(),
                "source": "Llama 3.3 70B (Comparative Intelligence)"
            }
            
            self._cache = result
            self._cache_time = datetime.now()
            return result
            
        except Exception as e:
            print(f"Groq Error: {e}")
            result = {
                "risk_score": 85,
                "risk_level": "HIGH",
                "safety_category": "DANGEROUS",
                "comparison": [
                    {"route": "Suez Canal", "risk_score": 85, "category": "DANGEROUS", "status": "Conflict"},
                    {"route": "IMEC", "risk_score": 50, "category": "CAUTION", "status": "Tense"},
                    {"route": "Cape", "risk_score": 20, "category": "SAFE", "status": "Stable"}
                ],
                "summary": "Simulated Analysis (API Error).",
                "recommendation": "Reroute via Cape of Good Hope immediately.",
                "timestamp": datetime.now().isoformat(),
                "source": "Simulation (Fallback)"
            }
            self._cache = result
            self._cache_time = datetime.now()
            return result

ai_sentinel = AISentinel()
