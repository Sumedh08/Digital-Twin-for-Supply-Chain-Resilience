"""
Stochastic Events Engine
========================
Monte Carlo disruption engine for the CarbonShip Digital Twin.

Implements 4 calibrated maritime disruption event types with
Poisson arrival rates based on historical incident data.

Sources
-------
- Suez blockage frequency: IMO MSC circulars 2009-2024
- Red Sea piracy: IMO piracy reports 2017-2024
- Port strike: LMU Logistics Disruption Index 2020-2024
- Cyclone frequency: WMO Tropical Cyclone Reports (Arabian Sea basin)

Usage
-----
    from backend.services.stochastic_events import StochasticEventEngine
    engine = StochasticEventEngine()
    result = engine.sample_events(simulation_month=5, num_simulations=1000)
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Event Catalogue
# ---------------------------------------------------------------------------

@dataclass
class DisruptionEvent:
    """
    A single calibrated disruption event.

    Parameters
    ----------
    name          : Human-readable event name
    route_affected: Which route this primarily disrupts ('suez' | 'imec' | 'both')
    poisson_lambda: Expected number of events per year (λ)
    min_delay_days: Minimum delay when event occurs
    max_delay_days: Maximum delay when event occurs
    co2_multiplier: CO₂ factor inflation (1.0 = no change; >1 = reroute penalty)
    seasonal_peak : Calendar months where λ is amplified (1-12). Empty = uniform.
    seasonal_amp  : Amplitude multiplier during seasonal peak months
    """
    name: str
    route_affected: str
    poisson_lambda: float
    min_delay_days: float
    max_delay_days: float
    co2_multiplier: float = 1.0
    seasonal_peak: List[int] = field(default_factory=list)
    seasonal_amp: float = 1.0


# Calibrated catalogue — each event is independently simulated per voyage
DISRUPTION_CATALOGUE: List[DisruptionEvent] = [
    DisruptionEvent(
        name="Suez Canal Blockage",
        route_affected="suez",
        poisson_lambda=0.4,           # ~1 significant blockage every 2.5 years
        min_delay_days=3.0,
        max_delay_days=18.0,
        co2_multiplier=1.35,          # Cape of Good Hope reroute: +35% CO₂
        seasonal_peak=[],
        seasonal_amp=1.0,
    ),
    DisruptionEvent(
        name="Red Sea Piracy / Houthi Strike",
        route_affected="suez",
        poisson_lambda=2.8,           # Elevated since 2023; ~2-3 incidents/year
        min_delay_days=1.0,
        max_delay_days=12.0,
        co2_multiplier=1.15,          # Evasive routing adds ~15% distance
        seasonal_peak=[11, 12, 1, 2], # Winter NE monsoon: worse sea states
        seasonal_amp=1.4,
    ),
    DisruptionEvent(
        name="Major Port Strike (India/EU)",
        route_affected="both",
        poisson_lambda=0.6,           # ~1 significant strike every 1.7 years
        min_delay_days=2.0,
        max_delay_days=10.0,
        co2_multiplier=1.05,          # Slow steaming while waiting
        seasonal_peak=[6, 7],         # Summer: labour dispute season in EU
        seasonal_amp=1.3,
    ),
    DisruptionEvent(
        name="Arabian Sea Cyclone",
        route_affected="both",
        poisson_lambda=1.5,           # ~1-2 per year (RSMC New Delhi data)
        min_delay_days=2.0,
        max_delay_days=8.0,
        co2_multiplier=1.10,
        seasonal_peak=[5, 6, 10, 11], # Pre- and post-monsoon cyclone windows
        seasonal_amp=3.5,             # Strongly seasonal
    ),
]


# ---------------------------------------------------------------------------
# Simulation Engine
# ---------------------------------------------------------------------------

class StochasticEventEngine:
    """
    Monte Carlo engine that simulates voyage disruptions over N runs and
    returns P50/P95/P99 delay and carbon bands.

    Design
    ------
    - Each simulation run draws disruptions from a Poisson process
    - Disruption delay ~ Uniform(min_delay, max_delay) when event fires
    - Events fire independently — multiple events can co-occur
    - Seasonal amplitude adjusts the Poisson rate for the given month
    """

    def __init__(self, catalogue: Optional[List[DisruptionEvent]] = None):
        self.catalogue = catalogue or DISRUPTION_CATALOGUE

    def _seasonal_lambda(
        self,
        event: DisruptionEvent,
        simulation_month: int,
    ) -> float:
        """Adjust Poisson λ for seasonal effects."""
        if event.seasonal_peak and simulation_month in event.seasonal_peak:
            return event.poisson_lambda * event.seasonal_amp
        return event.poisson_lambda

    def _simulate_one_voyage(
        self,
        simulation_month: int,
        route: str,
        voyage_days: float,
    ) -> Dict[str, float]:
        """
        Simulate a single voyage.

        Returns
        -------
        dict with delay_days, co2_multiplier, events_fired (list of names)
        """
        total_delay = 0.0
        cumulative_co2_mult = 1.0
        events_fired = []

        for event in self.catalogue:
            # Only apply events relevant to this route
            if event.route_affected not in (route, "both"):
                continue

            lam = self._seasonal_lambda(event, simulation_month)
            # Per-voyage λ: annual rate × (voyage_days / 365)
            voyage_lambda = lam * (voyage_days / 365.0)
            n_occurrences = random.random() < (
                1.0 - math.exp(-voyage_lambda)
            )

            if n_occurrences:
                delay = random.uniform(event.min_delay_days, event.max_delay_days)
                total_delay += delay
                cumulative_co2_mult *= event.co2_multiplier
                events_fired.append(event.name)

        return {
            "delay_days": total_delay,
            "co2_multiplier": round(cumulative_co2_mult, 4),
            "events_fired": events_fired,
        }

    def sample_events(
        self,
        simulation_month: int = 6,
        num_simulations: int = 1000,
        route: str = "suez",
        base_voyage_days: float = 20.0,
        base_co2_tonnes: float = 25.0,
    ) -> Dict:
        """
        Run N Monte Carlo simulations and return uncertainty bands.

        Parameters
        ----------
        simulation_month  : Calendar month (1-12) for seasonal calibration
        num_simulations   : Number of Monte Carlo runs (200-10,000 typical)
        route             : 'suez' | 'imec' | 'both'
        base_voyage_days  : Nominal voyage duration (deterministic base)
        base_co2_tonnes   : Nominal CO₂ for the voyage (tCO₂)

        Returns
        -------
        dict with P50/P95/P99 delay and carbon bands, event frequency table
        """
        delays, co2_values, event_counts = [], [], {}

        for _ in range(num_simulations):
            voyage = self._simulate_one_voyage(
                simulation_month, route, base_voyage_days
            )
            delays.append(voyage["delay_days"])
            co2_values.append(base_co2_tonnes * voyage["co2_multiplier"])
            for ev in voyage["events_fired"]:
                event_counts[ev] = event_counts.get(ev, 0) + 1

        delays.sort()
        co2_values.sort()

        def pct(lst, p):
            idx = max(0, min(len(lst) - 1, int(len(lst) * p / 100)))
            return round(lst[idx], 3)

        prob_disruption = sum(1 for d in delays if d > 0) / num_simulations

        # Event frequency table (sorted by frequency descending)
        freq_table = {
            k: round(v / num_simulations, 4)
            for k, v in sorted(event_counts.items(),
                               key=lambda x: x[1], reverse=True)
        }

        return {
            # Delay uncertainty bands (days added to nominal voyage)
            "p50_delay_days":   pct(delays, 50),
            "p95_delay_days":   pct(delays, 95),
            "p99_delay_days":   pct(delays, 99),
            "mean_delay_days":  round(sum(delays) / len(delays), 2),

            # Carbon uncertainty bands (tCO₂ total voyage)
            "p50_co2_tonnes":   pct(co2_values, 50),
            "p95_co2_tonnes":   pct(co2_values, 95),
            "p99_co2_tonnes":   pct(co2_values, 99),

            # Summary statistics
            "probability_any_disruption": round(prob_disruption, 4),
            "num_simulations":            num_simulations,
            "simulation_month":           simulation_month,
            "route":                      route,
            "base_voyage_days":           base_voyage_days,
            "base_co2_tonnes":            base_co2_tonnes,

            # Event frequency table
            "event_frequency_table": freq_table,

            # Methodology note (for API consumers)
            "methodology": (
                "Poisson arrival process per event type with seasonal amplitude. "
                "Delay per event drawn from Uniform(min, max). "
                "Events fire independently — co-occurrence is possible. "
                "All λ values calibrated from IMO/WMO historical incident data."
            ),
        }


# Module-level singleton
stochastic_engine = StochasticEventEngine()
