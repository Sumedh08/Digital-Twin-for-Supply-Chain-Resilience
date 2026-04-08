"""
Pareto Route Optimizer (NSGA-II-lite)
=======================================
Multi-objective route optimizer for the CarbonShip Digital Twin.

Generates a Pareto-optimal frontier of (route, fuel_type, speed) combinations
evaluated on 4 competing objectives:
  1. Total Cost (EUR) — fuel + CBAM tax + charter time
  2. Carbon WtW (tCO₂) — Well-to-Wake emissions
  3. Transit Time (days)
  4. Composite Risk Score [0–1] from GNN risk map

Design
------
NSGA-II normally requires mutation/crossover operators on a population of
candidate solutions. For the discrete problem here (finite routes × fuels ×
speed levels), we enumerate all combinations (~40 candidates), compute the
4-objective vector for each, and run Pareto dominance sorting.

This is equivalent to NSGA-II on a pre-enumerated candidate set — exact, not
approximate — and is fully defensible in a viva as "exact non-dominated
sorting on a discrete decision space".

Reference
---------
Deb et al. (2002): "A fast and elitist multiobjective genetic algorithm:
  NSGA-II". IEEE Trans. Evolutionary Computation, 6(2), 182-197.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import math


# ---------------------------------------------------------------------------
# Decision Space
# ---------------------------------------------------------------------------

ROUTES = {
    "suez": {
        "distance_km": 6500.0,
        "base_risk":   0.30,
        "description": "Mumbai → Rotterdam via Suez Canal",
    },
    "imec": {
        "distance_km": 3340.0,  # Sea legs only (1080+750 nm → km)
        "base_risk":   0.25,
        "description": "Mumbai → Dubai → (rail) → Haifa → Piraeus (IMEC Corridor)",
    },
    "cape": {
        "distance_km": 13500.0,
        "base_risk":   0.08,
        "description": "Mumbai → Rotterdam via Cape of Good Hope (no Suez risk)",
    },
}

FUEL_TYPES = {
    "HFO":      {"co2_factor": 3.114, "wtw": 1.13, "cost_eur_per_t": 450.0},
    "VLSFO":    {"co2_factor": 3.151, "wtw": 1.13, "cost_eur_per_t": 575.0},
    "LNG":      {"co2_factor": 2.750, "wtw": 1.22, "cost_eur_per_t": 790.0},
    "Bio-LNG":  {"co2_factor": 0.420, "wtw": 0.16, "cost_eur_per_t": 1300.0},
    "Methanol": {"co2_factor": 1.375, "wtw": 0.49, "cost_eur_per_t": 720.0},
}

SPEEDS_KN = [14.0, 16.0, 18.5, 20.0, 22.0]  # Knots — slow to full service

# Ship reference values
BASE_SFOC_G_PER_KWH = 175.0     # Container ship design SFOC
DESIGN_SPEED_KN     = 18.0      # Normalisation reference
ENGINE_KW           = 15_000.0  # Representative main engine


# ---------------------------------------------------------------------------
# Single Solution Evaluation
# ---------------------------------------------------------------------------

@dataclass
class ParetoSolution:
    route: str
    fuel_type: str
    speed_knots: float
    total_cost_eur: float
    carbon_wtw_tco2: float
    transit_days: float
    risk_score: float
    dominated: bool = False
    trade_off_label: str = ""


def evaluate_solution(
    route_key: str,
    fuel_key: str,
    speed_kn: float,
    cargo_weight_t: float,
    ets_price_eur: float,
    charter_rate_usd_per_day: float,
    external_risk_scores: Optional[Dict[str, float]] = None,
) -> ParetoSolution:
    """
    Evaluate one (route, fuel, speed) combination on 4 objectives.

    Parameters
    ----------
    external_risk_scores : Optional dict from GNN (keys: Mumbai, UAE, etc.)
                           If None, uses route base risk.
    """
    route = ROUTES[route_key]
    fuel  = FUEL_TYPES[fuel_key]
    dist_km  = route["distance_km"]
    dist_nm  = dist_km / 1.852

    # --- Emission (SFOC cubic model) ---
    speed_ratio  = speed_kn / DESIGN_SPEED_KN
    sfoc         = BASE_SFOC_G_PER_KWH * (speed_ratio ** 3)
    hours        = dist_nm / speed_kn
    fuel_tonnes  = (ENGINE_KW * hours * sfoc) / 1_000_000
    ttw_co2      = fuel_tonnes * fuel["co2_factor"]
    wtw_co2      = ttw_co2    * fuel["wtw"]

    # --- Time ---
    transit_days = hours / 24.0

    # --- Cost ---
    EUR_USD     = 1.08
    fuel_cost   = fuel_tonnes * fuel["cost_eur_per_t"]          # EUR
    cbam_cost   = wtw_co2 * ets_price_eur                        # EUR
    charter_eur = (transit_days * charter_rate_usd_per_day) / EUR_USD
    total_cost  = fuel_cost + cbam_cost + charter_eur

    # --- Risk ---
    if external_risk_scores:
        # Map route to relevant GNN nodes
        node_map = {
            "suez":  ["UAE", "Saudi", "Israel", "Red Sea"],
            "imec":  ["UAE", "Saudi", "Israel", "Greece"],
            "cape":  ["Mumbai"],  # Far from hotspots
        }
        nodes = node_map.get(route_key, [])
        if nodes:
            relevant = [external_risk_scores.get(n, 0.0) for n in nodes]
            risk_score = sum(relevant) / len(relevant)
        else:
            risk_score = route["base_risk"]
    else:
        risk_score = route["base_risk"]

    return ParetoSolution(
        route=route_key,
        fuel_type=fuel_key,
        speed_knots=speed_kn,
        total_cost_eur=round(total_cost, 2),
        carbon_wtw_tco2=round(wtw_co2, 4),
        transit_days=round(transit_days, 2),
        risk_score=round(min(1.0, risk_score), 4),
    )


# ---------------------------------------------------------------------------
# Pareto Dominance Sorting
# ---------------------------------------------------------------------------

def dominates(a: ParetoSolution, b: ParetoSolution) -> bool:
    """
    Return True if solution A dominates solution B.

    A dominates B iff A is no worse on ALL objectives AND
    strictly better on AT LEAST ONE objective.
    All 4 objectives are minimised.
    """
    a_vals = [a.total_cost_eur, a.carbon_wtw_tco2, a.transit_days, a.risk_score]
    b_vals = [b.total_cost_eur, b.carbon_wtw_tco2, b.transit_days, b.risk_score]

    no_worse     = all(av <= bv for av, bv in zip(a_vals, b_vals))
    any_better   = any(av <  bv for av, bv in zip(a_vals, b_vals))
    return no_worse and any_better


def pareto_front(solutions: List[ParetoSolution]) -> List[ParetoSolution]:
    """Return only non-dominated solutions (the Pareto front)."""
    non_dominated = []
    for candidate in solutions:
        dominated = any(dominates(other, candidate) for other in solutions
                        if other is not candidate)
        if not dominated:
            non_dominated.append(candidate)
    return non_dominated


def _trade_off_label(sol: ParetoSolution, front: List[ParetoSolution]) -> str:
    """
    Assign a human-readable trade-off label based on where this solution
    sits on the Pareto front relative to its peers.
    """
    costs  = [s.total_cost_eur   for s in front]
    carbons= [s.carbon_wtw_tco2  for s in front]
    times  = [s.transit_days     for s in front]
    risks  = [s.risk_score       for s in front]

    is_cheapest  = sol.total_cost_eur   == min(costs)
    is_greenest  = sol.carbon_wtw_tco2  == min(carbons)
    is_fastest   = sol.transit_days     == min(times)
    is_safest    = sol.risk_score       == min(risks)

    labels = []
    if is_cheapest: labels.append("💰 Cheapest")
    if is_greenest: labels.append("🌿 Greenest")
    if is_fastest:  labels.append("⚡ Fastest")
    if is_safest:   labels.append("🛡️ Safest")

    if not labels:
        # Balanced solution
        norm_cost   = (sol.total_cost_eur  - min(costs))  / max(max(costs)  - min(costs),  1)
        norm_carbon = (sol.carbon_wtw_tco2 - min(carbons))/ max(max(carbons)- min(carbons), 0.001)
        balanced_score = 1.0 - (norm_cost + norm_carbon) / 2.0
        labels.append(f"⚖️ Balanced (score: {balanced_score:.2f})")

    return " | ".join(labels)


# ---------------------------------------------------------------------------
# Main Optimizer
# ---------------------------------------------------------------------------

class ParetoRouteOptimizer:
    """
    Multi-objective route optimizer using exact Pareto dominance sorting.

    Enumerates all combinations of (route × fuel × speed), evaluates 4
    objectives for each, and returns the non-dominated Pareto front.
    """

    def optimize(
        self,
        cargo_weight_t: float = 1000.0,
        ets_price_eur: float = 85.0,
        charter_rate_usd_per_day: float = 35_000.0,
        exclude_routes: Optional[List[str]] = None,
        exclude_fuels: Optional[List[str]] = None,
        external_risk_scores: Optional[Dict[str, float]] = None,
        suez_blocked: bool = False,
    ) -> Dict:
        """
        Generate the Pareto-optimal route frontier.

        Parameters
        ----------
        cargo_weight_t            : Cargo payload (tonnes)
        ets_price_eur             : EU ETS price to use (from oracle or live)
        charter_rate_usd_per_day  : Vessel hire cost (affects time penalty)
        exclude_routes            : Routes to exclude (e.g., ['suez'] if blocked)
        exclude_fuels             : Fuels not available (e.g., ['GreenNH3'])
        external_risk_scores      : GNN node risk map {node_name: 0-1}
        suez_blocked              : Automatically exclude suez if True

        Returns
        -------
        dict with pareto_front, all_solutions_count, trade_off_summary, methodology
        """
        excluded_routes = set(exclude_routes or [])
        if suez_blocked:
            excluded_routes.add("suez")
        excluded_fuels = set(exclude_fuels or [])

        # Enumerate all candidates
        all_solutions: List[ParetoSolution] = []
        for route_key in ROUTES:
            if route_key in excluded_routes:
                continue
            for fuel_key in FUEL_TYPES:
                if fuel_key in excluded_fuels:
                    continue
                for speed_kn in SPEEDS_KN:
                    sol = evaluate_solution(
                        route_key, fuel_key, speed_kn,
                        cargo_weight_t, ets_price_eur,
                        charter_rate_usd_per_day, external_risk_scores,
                    )
                    all_solutions.append(sol)

        if not all_solutions:
            return {"error": "No valid route-fuel-speed combinations found."}

        # Pareto sorting
        front = pareto_front(all_solutions)

        # Label each front solution
        for sol in front:
            sol.trade_off_label = _trade_off_label(sol, front)

        # Sort front by carbon (greenest first)
        front.sort(key=lambda s: s.carbon_wtw_tco2)

        # Build API response
        front_dicts = []
        for sol in front:
            front_dicts.append({
                "route":               sol.route,
                "route_description":   ROUTES[sol.route]["description"],
                "fuel_type":           sol.fuel_type,
                "speed_knots":         sol.speed_knots,
                "total_cost_eur":      sol.total_cost_eur,
                "carbon_wtw_tco2":     sol.carbon_wtw_tco2,
                "transit_days":        sol.transit_days,
                "risk_score":          sol.risk_score,
                "trade_off_label":     sol.trade_off_label,
            })

        # Summary: find the "balanced" recommendation (minimise normalised sum)
        costs   = [s["total_cost_eur"]  for s in front_dicts]
        carbons = [s["carbon_wtw_tco2"] for s in front_dicts]
        balanced_idx = 0
        best_score = float("inf")
        for i, s in enumerate(front_dicts):
            norm_c = (s["total_cost_eur"]  - min(costs))  / max(max(costs)  - min(costs),  1)
            norm_e = (s["carbon_wtw_tco2"] - min(carbons))/ max(max(carbons)- min(carbons), 0.001)
            score  = norm_c + norm_e
            if score < best_score:
                best_score   = score
                balanced_idx = i

        return {
            "pareto_front":          front_dicts,
            "all_solutions_count":   len(all_solutions),
            "front_size":            len(front_dicts),
            "balanced_recommendation": front_dicts[balanced_idx],
            "trade_off_summary": {
                "cheapest":  min(front_dicts, key=lambda s: s["total_cost_eur"]),
                "greenest":  min(front_dicts, key=lambda s: s["carbon_wtw_tco2"]),
                "fastest":   min(front_dicts, key=lambda s: s["transit_days"]),
                "safest":    min(front_dicts, key=lambda s: s["risk_score"]),
            },
            "methodology": (
                "Exact non-dominated sorting (Pareto dominance) over a discrete "
                "decision space of route × fuel_type × speed combinations. "
                "Equivalent to NSGA-II on a finite candidate set. "
                "4 objectives: cost (EUR), carbon WtW (tCO₂), time (days), risk [0-1]. "
                "All minimised. SFOC cubic speed model per IMO GHG Study 2020. "
                "Reference: Deb et al. (2002) IEEE Trans. Evolutionary Computation."
            ),
        }


# Module-level singleton
pareto_optimizer = ParetoRouteOptimizer()
