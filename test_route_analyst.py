import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

from backend.services.route_analyst import (
    MAX_NEWS_AGE_DAYS,
    MIN_QUALIFYING_ARTICLES,
    ROUTE_DATA,
    RouteAnalyst,
)


def make_article(
    title: str,
    *,
    reference_time: datetime,
    hours_ago: int,
    query: str,
    link_suffix: str,
):
    published_at = reference_time - timedelta(hours=hours_ago)
    published_at = published_at.astimezone(timezone.utc)
    return {
        "title": title,
        "published_at": format_datetime(published_at),
        "link": f"https://example.com/{link_suffix}",
        "query": query,
    }


class RouteAnalystTests(unittest.TestCase):
    def setUp(self):
        self.analyst = RouteAnalyst()
        self.analyst.client = None
        self.reference_time = datetime(2026, 3, 24, 12, 0, tzinfo=timezone.utc)
        self.route_info = ROUTE_DATA["mumbai_rotterdam_suez"]

    def test_collect_route_news_dedupes_and_caps_to_thirty(self):
        call_index = {"value": 0}

        def fake_fetch(query, limit=12):
            call_index["value"] += 1
            batch = []
            for item_index in range(4):
                batch.append(
                    make_article(
                        f"Red Sea shipping update {call_index['value']}-{item_index}",
                        reference_time=self.reference_time,
                        hours_ago=call_index["value"] + item_index,
                        query=query,
                        link_suffix=f"{call_index['value']}-{item_index}",
                    )
                )
            batch.append(
                make_article(
                    "Shared Bab el-Mandeb disruption alert",
                    reference_time=self.reference_time,
                    hours_ago=2,
                    query=query,
                    link_suffix="shared",
                )
            )
            return batch[:limit]

        self.analyst._fetch_news_articles = fake_fetch  # type: ignore[method-assign]

        articles = self.analyst._collect_route_news(self.route_info, self.reference_time.replace(tzinfo=None))

        self.assertEqual(len(articles), 30)
        self.assertEqual(len({article["title"] for article in articles}), 30)
        self.assertTrue(all("collector" in article for article in articles))

    def test_analysis_qualifies_full_live_confidence_with_ten_or_more_articles(self):
        articles = [
            make_article(
                f"Red Sea attack shipping alert {index}",
                reference_time=self.reference_time,
                hours_ago=index + 1,
                query="security",
                link_suffix=f"full-{index}",
            )
            for index in range(12)
        ]

        analysis = self.analyst._build_deterministic_analysis(
            self.route_info,
            articles,
            self.reference_time.replace(tzinfo=None),
        )

        self.assertEqual(analysis["qualified_reference_count"], 12)
        self.assertEqual(analysis["target_reference_count"], MIN_QUALIFYING_ARTICLES)
        self.assertEqual(analysis["insufficient_reference_depth"], 0)
        self.assertTrue(analysis["live_articles_qualified"])
        self.assertFalse(analysis["analysis_provisional"])
        self.assertEqual(analysis["recency_model"]["minimum_articles_required"], 10)
        self.assertGreaterEqual(len(analysis["scored_headlines"]), 10)

    def test_analysis_marks_partial_reference_depth_as_provisional(self):
        articles = [
            make_article(
                f"Suez Canal congestion shipping delay {index}",
                reference_time=self.reference_time,
                hours_ago=index + 2,
                query="congestion",
                link_suffix=f"partial-{index}",
            )
            for index in range(7)
        ]

        analysis = self.analyst._build_deterministic_analysis(
            self.route_info,
            articles,
            self.reference_time.replace(tzinfo=None),
        )

        self.assertEqual(analysis["qualified_reference_count"], 7)
        self.assertEqual(analysis["insufficient_reference_depth"], 3)
        self.assertFalse(analysis["live_articles_qualified"])
        self.assertTrue(analysis["analysis_provisional"])
        self.assertIn("provisional", analysis["recommendation"].lower())
        self.assertGreater(analysis["overall_risk_score"], 0)

    def test_sparse_reference_depth_falls_back_to_baseline_guidance(self):
        articles = [
            make_article(
                f"Mediterranean trade route update {index}",
                reference_time=self.reference_time,
                hours_ago=index + 6,
                query="geopolitics",
                link_suffix=f"sparse-{index}",
            )
            for index in range(3)
        ]

        analysis = self.analyst._build_deterministic_analysis(
            self.route_info,
            articles,
            self.reference_time.replace(tzinfo=None),
        )

        self.assertEqual(analysis["qualified_reference_count"], 3)
        self.assertEqual(analysis["insufficient_reference_depth"], 7)
        self.assertFalse(analysis["live_articles_qualified"])
        self.assertTrue(analysis["analysis_provisional"])
        self.assertEqual(
            analysis["recency_model"]["max_window_days"],
            MAX_NEWS_AGE_DAYS,
        )


if __name__ == "__main__":
    unittest.main()
