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
            result = {
                "risk_score": 85,
                "risk_level": "HIGH",
                "summary": f"Simulated based on context. Live News: {live_news[:100]}...",
                "recommendation": "Reroute via Cape of Good Hope immediately.",
                "timestamp": datetime.now().isoformat(),
                "source": "Mock AI + RSS Search"
            }
            self._cache = result
            self._cache_time = datetime.now()
            return result

        try:
            print(f"🤖 Calling Groq API for {context} analysis...")
            prompt = f"""
            You are a Maritime Security Analyst. Analyze risk for shipping routes between {route}, specifically focusing on {context}.
            Here is the absolute latest LIVE NEWS from the internet:
            {live_news}
            
            Synthesize this live data and provide a JSON response ONLY (no markdown text outside it):
            {{
                "risk_score": <integer 0-100>,
                "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
                "summary": "<2 sentences max integrating the live news>",
                "recommendation": "<Actionable advice>"
            }}
            """
            
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            content = completion.choices[0].message.content
            
            # Bulletproof Regex extraction
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                content = match.group(0)
                
            parsed = json.loads(content)
            
            result = {
                "risk_score": parsed.get("risk_score", 75),
                "risk_level": parsed.get("risk_level", "HIGH"),
                "summary": parsed.get("summary", "Analysis completed."),
                "recommendation": parsed.get("recommendation", "Exercise caution."),
                "timestamp": datetime.now().isoformat(),
                "source": "Llama 3.3 70B + Google RSS Data"
            }
            
            self._cache = result
            self._cache_time = datetime.now()
            return result
            
        except Exception as e:
            print(f"Groq Error: {e}")
            result = {
                "risk_score": 85,
                "risk_level": "HIGH",
                "summary": "Simulated Analysis (API Error).",
                "recommendation": "Reroute via Cape of Good Hope immediately.",
                "timestamp": datetime.now().isoformat(),
                "source": "Simulation (Fallback)"
            }
            self._cache = result
            self._cache_time = datetime.now()
            return result

ai_sentinel = AISentinel()
