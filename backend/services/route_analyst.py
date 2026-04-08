from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Callable, Dict, List, Optional, Protocol

try:
    from groq import Groq
except ImportError:
    Groq = None


ROUTE_DATA = {
    "mumbai_rotterdam_suez": {
        "name": "Mumbai -> Rotterdam (Suez Canal)",
        "waypoints": [
            "Arabian Sea",
            "Gulf of Aden",
            "Red Sea",
            "Suez Canal",
            "Mediterranean Sea",
            "Strait of Gibraltar",
            "English Channel",
        ],
        "chokepoints": ["Bab el-Mandeb Strait", "Suez Canal"],
        "risk_zones": [
            "Red Sea (Houthi activity)",
            "Gulf of Aden (Piracy)",
            "Suez Canal (Congestion)",
        ],
        "distance_nm": 6337,
        "typical_days": 18,
        "alternative": "mumbai_rotterdam_cape",
        "baseline_risk": 54,
        "queries": [
            "Red Sea shipping attacks maritime security",
            "Suez Canal congestion shipping delay",
            "Bab el-Mandeb piracy shipping news",
        ],
        "zone_keywords": [
            "red sea",
            "suez",
            "bab el-mandeb",
            "gulf of aden",
            "yemen",
            "houthi",
        ],
    },
    "mumbai_rotterdam_cape": {
        "name": "Mumbai -> Rotterdam (Cape of Good Hope)",
        "waypoints": [
            "Arabian Sea",
            "Indian Ocean",
            "Mozambique Channel",
            "Cape of Good Hope",
            "South Atlantic",
            "English Channel",
        ],
        "chokepoints": ["Mozambique Channel"],
        "risk_zones": [
            "Mozambique Channel (Piracy)",
            "South Atlantic (Weather)",
        ],
        "distance_nm": 10750,
        "typical_days": 28,
        "alternative": "mumbai_rotterdam_suez",
        "baseline_risk": 23,
        "queries": [
            "Cape of Good Hope shipping weather disruption",
            "Mozambique Channel piracy maritime shipping",
            "South Atlantic storm shipping route",
        ],
        "zone_keywords": [
            "cape of good hope",
            "mozambique channel",
            "south atlantic",
            "cape route",
            "south africa shipping",
        ],
    },
    "mumbai_rotterdam_imec": {
        "name": "Mumbai -> Rotterdam (IMEC Corridor)",
        "waypoints": [
            "Arabian Sea",
            "Jebel Ali (UAE)",
            "Rail: UAE to Israel",
            "Haifa Port",
            "Mediterranean Sea",
            "English Channel",
        ],
        "chokepoints": ["Strait of Hormuz"],
        "risk_zones": [
            "Strait of Hormuz (Iran tensions)",
            "UAE-Israel Rail (Geopolitical)",
        ],
        "distance_nm": 5800,
        "typical_days": 14,
        "alternative": "mumbai_rotterdam_suez",
        "baseline_risk": 36,
        "queries": [
            "IMEC corridor shipping rail geopolitics",
            "Strait of Hormuz shipping tension",
            "Haifa port shipping security",
        ],
        "zone_keywords": [
            "imec",
            "hormuz",
            "haifa",
            "uae",
            "israel",
            "iran",
        ],
    },
    "mumbai_hamburg_suez": {
        "name": "Mumbai -> Hamburg (Suez Canal)",
        "waypoints": [
            "Arabian Sea",
            "Gulf of Aden",
            "Red Sea",
            "Suez Canal",
            "Mediterranean Sea",
            "North Sea",
        ],
        "chokepoints": ["Bab el-Mandeb Strait", "Suez Canal"],
        "risk_zones": ["Red Sea (Houthi activity)", "Gulf of Aden (Piracy)"],
        "distance_nm": 6100,
        "typical_days": 18,
        "alternative": "mumbai_rotterdam_cape",
        "baseline_risk": 52,
        "queries": [
            "Red Sea shipping attacks maritime security",
            "Suez Canal congestion shipping delay",
            "Gulf of Aden piracy cargo ship",
        ],
        "zone_keywords": [
            "red sea",
            "suez",
            "gulf of aden",
            "bab el-mandeb",
            "houthi",
        ],
    },
    "chennai_rotterdam_suez": {
        "name": "Chennai -> Rotterdam (Suez Canal)",
        "waypoints": [
            "Bay of Bengal",
            "Indian Ocean",
            "Arabian Sea",
            "Gulf of Aden",
            "Red Sea",
            "Suez Canal",
            "Mediterranean Sea",
        ],
        "chokepoints": ["Bab el-Mandeb Strait", "Suez Canal"],
        "risk_zones": ["Red Sea (Houthi activity)", "Gulf of Aden (Piracy)"],
        "distance_nm": 8100,
        "typical_days": 22,
        "alternative": "mumbai_rotterdam_cape",
        "baseline_risk": 53,
        "queries": [
            "Red Sea shipping attacks maritime security",
            "Suez Canal congestion shipping delay",
            "Bab el-Mandeb piracy shipping news",
        ],
        "zone_keywords": [
            "red sea",
            "suez",
            "gulf of aden",
            "bab el-mandeb",
            "houthi",
        ],
    },
}

ROUTE_CODE_MAP = {
    "INMUN_NLRTM_SUEZ": "mumbai_rotterdam_suez",
    "INMUN_NLRTM_CAPE": "mumbai_rotterdam_cape",
    "INMUN_NLRTM_IMEC": "mumbai_rotterdam_imec",
    "INMUN_DEHAM_SUEZ": "mumbai_hamburg_suez",
    "INMAA_NLRTM_SUEZ": "chennai_rotterdam_suez",
}

CATEGORY_RULES = {
    "SECURITY": {
        "keywords": {
            "attack": 10,
            "missile": 10,
            "drone": 9,
            "strike": 9,
            "piracy": 8,
            "pirate": 8,
            "boarding": 8,
            "seized": 8,
            "navy": 6,
            "security": 5,
            "houthi": 10,
            "militant": 8,
            "explosion": 9,
        },
        "zone": "Maritime security corridor",
    },
    "CONGESTION": {
        "keywords": {
            "congestion": 8,
            "delay": 6,
            "queue": 6,
            "backlog": 7,
            "closure": 9,
            "blocked": 9,
            "grounded": 8,
            "strike action": 7,
            "canal traffic": 6,
        },
        "zone": "Port and canal operations",
    },
    "WEATHER": {
        "keywords": {
            "storm": 8,
            "cyclone": 10,
            "weather": 5,
            "rough seas": 7,
            "wind": 5,
            "flood": 6,
            "monsoon": 6,
            "wave": 5,
        },
        "zone": "Weather-exposed sea lane",
    },
    "GEOPOLITICAL": {
        "keywords": {
            "war": 10,
            "conflict": 9,
            "tension": 7,
            "sanction": 7,
            "iran": 8,
            "israel": 8,
            "ceasefire": 4,
            "trade route": 5,
            "corridor": 5,
            "tariff": 5,
            "military": 7,
        },
        "zone": "Geopolitical corridor",
    },
}

MAX_NEWS_AGE_DAYS = 10
TARGET_REFERENCE_COUNT = 10
MIN_QUALIFYING_ARTICLES = TARGET_REFERENCE_COUNT


class RouteNewsCollector(Protocol):
    name: str

    def collect(
        self,
        route_info: Dict,
        fetch_articles: Callable[[str, int], List[Dict]],
    ) -> List[Dict]:
        ...


def _clean_zone_name(label: str) -> str:
    return label.split("(")[0].strip()


class GoogleNewsRouteCollector:
    name = "google_news_rss"
    per_query_limit = 8
    max_queries = 18

    def _build_queries(self, route_info: Dict) -> List[str]:
        candidates: List[str] = list(route_info.get("queries", []))
        route_name = route_info.get("name", "")

        if route_name:
            candidates.extend(
                [
                    f"{route_name} shipping disruption",
                    f"{route_name} maritime security",
                    f"{route_name} supply chain risk",
                ]
            )

        for chokepoint in route_info.get("chokepoints", []):
            chokepoint_name = _clean_zone_name(chokepoint)
            candidates.extend(
                [
                    f"{chokepoint_name} shipping disruption",
                    f"{chokepoint_name} maritime security",
                    f"{chokepoint_name} shipping delay",
                ]
            )

        for zone in route_info.get("risk_zones", []):
            zone_name = _clean_zone_name(zone)
            candidates.extend(
                [
                    f"{zone_name} shipping news",
                    f"{zone_name} maritime risk",
                    f"{zone_name} supply chain disruption",
                ]
            )

        for waypoint in route_info.get("waypoints", [])[:4]:
            waypoint_name = _clean_zone_name(waypoint)
            candidates.extend(
                [
                    f"{waypoint_name} shipping maritime",
                    f"{waypoint_name} port congestion shipping",
                ]
            )

        ordered: List[str] = []
        seen = set()
        for candidate in candidates:
            normalized = " ".join(candidate.lower().split())
            if normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(candidate)
        return ordered[: self.max_queries]

    def collect(
        self,
        route_info: Dict,
        fetch_articles: Callable[[str, int], List[Dict]],
    ) -> List[Dict]:
        articles: List[Dict] = []
        for query in self._build_queries(route_info):
            for article in fetch_articles(query, self.per_query_limit):
                articles.append(
                    {
                        **article,
                        "collector": self.name,
                    }
                )
        return articles


def _normalize_title(title: str) -> str:
    return " ".join(title.lower().split())


def _parse_pubdate(pub_date: str) -> datetime:
    parsed = parsedate_to_datetime(pub_date)
    if parsed.tzinfo is not None:
        return parsed.astimezone().replace(tzinfo=None)
    return parsed


class RouteAnalyst:
    CACHE_TTL_MINUTES = 10
    MAX_ARTICLES = 30

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        self._cache = {}
        self.collectors: List[RouteNewsCollector] = [GoogleNewsRouteCollector()]
        if self.api_key and Groq:
            self.client = Groq(api_key=self.api_key)
            print("[ok] Groq (Route Analyst) initialized")

    def _is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self._cache:
            return False
        _, timestamp = self._cache[cache_key]
        return datetime.now() - timestamp < timedelta(minutes=self.CACHE_TTL_MINUTES)

    def _build_cache_key(self, route_key: str, ship_type: str) -> str:
        return f"{route_key}:{ship_type.lower()}"

    def _fetch_news_articles(self, query: str, limit: int = 12) -> List[Dict]:
        try:
            encoded_query = urllib.parse.quote(f"{query} shipping maritime supply chain")
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=5) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)
            articles: List[Dict] = []
            for item in root.findall("./channel/item")[:limit]:
                title = (item.findtext("title") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                link = (item.findtext("link") or "").strip()
                if not title or not pub_date:
                    continue
                articles.append(
                    {
                        "title": title,
                        "published_at": pub_date,
                        "link": link,
                        "query": query,
                    }
                )
            return articles
        except Exception as exc:  # noqa: BLE001
            print(f"Google News RSS fetch failed for '{query}': {exc}")
            return []

    def _collect_route_news(self, route_info: Dict, reference_time: datetime) -> List[Dict]:
        deduped: Dict[str, Dict] = {}
        effective_cutoff = reference_time - timedelta(days=MAX_NEWS_AGE_DAYS)
        for collector in self.collectors:
            for article in collector.collect(route_info, self._fetch_news_articles):
                published_at = _parse_pubdate(article["published_at"])
                if published_at < effective_cutoff or published_at > reference_time:
                    continue
                key = _normalize_title(article["title"])
                existing = deduped.get(key)
                if existing is None or published_at > _parse_pubdate(existing["published_at"]):
                    deduped[key] = article

        articles = list(deduped.values())
        articles.sort(key=lambda item: _parse_pubdate(item["published_at"]), reverse=True)
        return articles[: self.MAX_ARTICLES]

    def _relevance_factor(self, published_at: str, reference_time: datetime) -> float:
        age_days = max(
            (reference_time - _parse_pubdate(published_at)).total_seconds() / 86400,
            0.0,
        )
        if age_days > MAX_NEWS_AGE_DAYS:
            return 0.0
        if age_days <= 3:
            return 3.0
        if age_days <= 7:
            return 2.0
        return 1.0

    def _severity_from_title(self, title: str, route_info: Dict) -> Dict:
        title_lower = title.lower()
        best_category = "GEOPOLITICAL"
        best_score = 3
        matched_keywords: List[str] = []

        for category, config in CATEGORY_RULES.items():
            category_matches = [
                keyword
                for keyword in config["keywords"]
                if keyword in title_lower
            ]
            if not category_matches:
                continue

            category_score = max(config["keywords"][keyword] for keyword in category_matches)
            if category_score > best_score:
                best_category = category
                best_score = category_score
                matched_keywords = category_matches

        zone_hits = [keyword for keyword in route_info["zone_keywords"] if keyword in title_lower]
        route_relevance = 10 if zone_hits else 6 if "shipping" in title_lower or "maritime" in title_lower else 4

        return {
            "category": best_category,
            "severity_factor": float(best_score),
            "matched_keywords": matched_keywords[:4],
            "route_relevance": float(route_relevance),
            "zone": zone_hits[0] if zone_hits else CATEGORY_RULES[best_category]["zone"],
        }

    def _risk_label(self, score: float) -> str:
        if score >= 75:
            return "CRITICAL"
        if score >= 55:
            return "HIGH"
        if score >= 30:
            return "MEDIUM"
        return "LOW"

    def _score_articles(
        self,
        articles: List[Dict],
        route_info: Dict,
        reference_time: datetime,
    ) -> List[Dict]:
        scored_articles = []
        for article in articles:
            severity = self._severity_from_title(article["title"], route_info)
            relevance_factor = self._relevance_factor(article["published_at"], reference_time)
            article_score = round(
                (
                    severity["severity_factor"] * 0.45
                    + severity["route_relevance"] * 0.25
                    + relevance_factor * 0.30
                )
                * 10,
                2,
            )
            scored_articles.append(
                {
                    **article,
                    "category": severity["category"],
                    "zone": severity["zone"],
                    "severity_factor": severity["severity_factor"],
                    "route_relevance": severity["route_relevance"],
                    "relevance_factor": relevance_factor,
                    "recency_factor": relevance_factor,
                    "article_score": article_score,
                    "matched_keywords": severity["matched_keywords"],
                }
            )

        scored_articles.sort(
            key=lambda item: (item["article_score"], item["relevance_factor"]),
            reverse=True,
        )
        return scored_articles

    def _aggregate_overall_score(self, scored_articles: List[Dict], route_info: Dict) -> float:
        if not scored_articles:
            return float(route_info["baseline_risk"])

        top_articles = scored_articles[: min(len(scored_articles), 15)]
        weighted_total = 0.0
        weight_sum = 0.0
        for article in top_articles:
            weight = article["relevance_factor"] * 0.6 + article["severity_factor"] * 0.4
            weighted_total += article["article_score"] * weight
            weight_sum += weight

        live_score = weighted_total / weight_sum if weight_sum else route_info["baseline_risk"]
        coverage_factor = min(len(scored_articles) / MIN_QUALIFYING_ARTICLES, 1.0)
        live_weight = 0.15 + coverage_factor * 0.50
        baseline_weight = 1.0 - live_weight
        overall = route_info["baseline_risk"] * baseline_weight + live_score * live_weight
        return round(min(max(overall, route_info["baseline_risk"] * 0.75), 99.0), 0)

    def _build_risks(self, scored_articles: List[Dict]) -> List[Dict]:
        if not scored_articles:
            return []
        risks = []
        seen_categories = set()

        for article in scored_articles:
            if article["category"] in seen_categories:
                continue
            seen_categories.add(article["category"])
            published = _parse_pubdate(article["published_at"]).strftime("%Y-%m-%d")
            severity = self._risk_label(article["article_score"])
            risks.append(
                {
                    "category": article["category"],
                    "zone": article["zone"],
                    "severity": severity,
                    "description": f"[{published}] {article['title']}",
                }
            )
            if len(risks) == 4:
                break

        return risks

    def _build_recommendation(self, overall_score: float, route_info: Dict, scored_articles: List[Dict]) -> str:
        if not scored_articles:
            return (
                "No qualifying route headlines were retrieved inside the last 10 days. This score is "
                "currently a structural baseline based on chokepoints and known corridor exposure."
            )

        if len(scored_articles) < MIN_QUALIFYING_ARTICLES:
            return (
                f"Only {len(scored_articles)} recent headlines qualified inside the last 10 days. "
                "The current score uses the available evidence, but the assessment remains provisional "
                f"until at least {MIN_QUALIFYING_ARTICLES} recent references qualify."
            )

        freshest = scored_articles[0]
        published = _parse_pubdate(freshest["published_at"]).strftime("%Y-%m-%d")
        if overall_score >= 75:
            return (
                f"Reroute away from {route_info['name']} if schedule allows. The latest high-impact "
                f"headline from {published} materially increases near-term disruption risk."
            )
        if overall_score >= 55:
            return (
                f"Proceed only with active monitoring and contingency planning. The {freshest['category'].lower()} "
                f"signals in the latest headlines are elevated but not yet route-closing."
            )
        return (
            "Proceed on the planned route while continuing to monitor the feed. Live headlines are "
            "present but are not concentrated enough to justify rerouting right now."
        )

    def _build_deterministic_analysis(
        self,
        route_info: Dict,
        articles: List[Dict],
        reference_time: datetime,
    ) -> Dict:
        effective_cutoff = reference_time - timedelta(days=MAX_NEWS_AGE_DAYS)
        scored_articles = self._score_articles(articles, route_info, reference_time)
        overall_score = int(self._aggregate_overall_score(scored_articles, route_info))
        risk_level = self._risk_label(overall_score)
        alternative_key = route_info.get("alternative")
        live_articles_qualified = len(scored_articles) >= MIN_QUALIFYING_ARTICLES
        collector_sources = sorted({article.get("collector", "unknown") for article in articles})
        qualified_reference_count = len(scored_articles)
        insufficient_reference_depth = max(
            MIN_QUALIFYING_ARTICLES - qualified_reference_count,
            0,
        )

        return {
            "overall_risk_score": overall_score,
            "risk_level": risk_level,
            "live_articles_qualified": live_articles_qualified,
            "analysis_provisional": not live_articles_qualified,
            "qualified_reference_count": qualified_reference_count,
            "target_reference_count": MIN_QUALIFYING_ARTICLES,
            "insufficient_reference_depth": insufficient_reference_depth,
            "risks": self._build_risks(scored_articles),
            "recommendation": self._build_recommendation(overall_score, route_info, scored_articles),
            "should_reroute": overall_score >= 75,
            "alternative_route": ROUTE_DATA.get(alternative_key, {}).get("name"),
            "articles_analyzed": len(scored_articles),
            "collector_sources": collector_sources,
            "recency_model": {
                "fresh_window_days": 3,
                "medium_window_days": 7,
                "max_window_days": MAX_NEWS_AGE_DAYS,
                "scale": "1-3",
                "window_start_date": effective_cutoff.strftime("%Y-%m-%d"),
                "minimum_articles_required": MIN_QUALIFYING_ARTICLES,
                "target_reference_count": MIN_QUALIFYING_ARTICLES,
                "max_scored_headlines": self.MAX_ARTICLES,
                "formula": "0-3 days = 3, 3-7 days = 2, 7-10 days = 1. Older headlines are excluded.",
            },
            "scored_headlines": [
                {
                    "title": article["title"],
                    "published_at": article["published_at"],
                    "category": article["category"],
                    "zone": article["zone"],
                    "relevance_factor": article["relevance_factor"],
                    "recency_factor": article["recency_factor"],
                    "severity_factor": article["severity_factor"],
                    "route_relevance": article["route_relevance"],
                    "article_score": article["article_score"],
                    "query": article["query"],
                    "collector": article.get("collector"),
                    "matched_keywords": article["matched_keywords"],
                    "link": article["link"],
                }
                for article in scored_articles
            ],
        }

    def _enrich_with_groq(self, route_info: Dict, base_analysis: Dict) -> Dict:
        if (
            not self.client
            or not base_analysis["scored_headlines"]
            or not base_analysis.get("live_articles_qualified", False)
        ):
            return base_analysis

        headlines = base_analysis["scored_headlines"][:10]
        prompt = f"""You are a maritime risk analyst.
The numeric route risk score has already been fixed by a deterministic scoring engine.
Do not change the score or the risk level.

Route: {route_info['name']}
Fixed score: {base_analysis['overall_risk_score']}
Fixed risk level: {base_analysis['risk_level']}

Headlines:
{json.dumps(headlines, indent=2)}

Return JSON only:
{{
  "recommendation": "<one concise recommendation>",
  "risks": [
    {{
      "category": "<SECURITY|CONGESTION|WEATHER|GEOPOLITICAL>",
      "zone": "<route zone>",
      "severity": "<LOW|MEDIUM|HIGH|CRITICAL>",
      "description": "<mention a specific headline and date>"
    }}
  ]
}}
"""

        try:
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            content = completion.choices[0].message.content
            enriched = json.loads(content)
            risks = enriched.get("risks") or base_analysis["risks"]
            recommendation = enriched.get("recommendation") or base_analysis["recommendation"]
            return {
                **base_analysis,
                "risks": risks[:4],
                "recommendation": recommendation,
            }
        except Exception as exc:  # noqa: BLE001
            print(f"Groq enrichment error (Route Analyst): {exc}")
            return base_analysis

    async def analyze_route(
        self,
        route_code: str,
        ship_type: str = "Container Ship",
        force: bool = False,
    ) -> Dict:
        route_key = ROUTE_CODE_MAP.get(route_code, "mumbai_rotterdam_suez")
        route_info = ROUTE_DATA.get(route_key, ROUTE_DATA["mumbai_rotterdam_suez"])
        cache_key = self._build_cache_key(route_key, ship_type)

        if not force and self._is_cache_valid(cache_key):
            cached_result, _ = self._cache[cache_key]
            result = cached_result.copy()
            result["cached"] = True
            return result

        reference_time = datetime.now()
        articles = self._collect_route_news(route_info, reference_time)
        analysis = self._build_deterministic_analysis(route_info, articles, reference_time)
        analysis = self._enrich_with_groq(route_info, analysis)

        result = {
            "route_name": route_info["name"],
            "route_code": [key for key, value in ROUTE_CODE_MAP.items() if value == route_key][0],
            "ship_type": ship_type,
            "distance_nm": route_info["distance_nm"],
            "typical_days": route_info["typical_days"],
            "waypoints": route_info["waypoints"],
            "chokepoints": route_info["chokepoints"],
            "analysis": analysis,
            "alternative": self._get_alternative_info(route_info.get("alternative")),
            "timestamp": datetime.now().isoformat(),
            "source": "Pluggable route news collectors + recency-weighted risk engine + optional Groq narrative",
            "cached": False,
        }

        self._cache[cache_key] = (result, datetime.now())
        return result

    def _get_alternative_info(self, alt_key: Optional[str]) -> Optional[Dict]:
        if not alt_key or alt_key not in ROUTE_DATA:
            return None
        alt = ROUTE_DATA[alt_key]
        return {
            "name": alt["name"],
            "distance_nm": alt["distance_nm"],
            "typical_days": alt["typical_days"],
        }


route_analyst = RouteAnalyst()
