import os
import time as _time
from groq import Groq
import re
import json

# ---------------------------------------------------------------------------
# TTL Cache — prevents Groq free-tier rate limit exhaustion when the
# frontend polls /simulate repeatedly with identical slider positions.
# Cache TTL: 30 seconds. Keys are rounded to 1 d.p. for stable hash.
# ---------------------------------------------------------------------------
_risk_cache: dict = {}
_CACHE_TTL_SECONDS: float = 30.0


def _cache_key(heatwave: float, conflict: float,
               piracy: float, suez_blocked: bool) -> str:
    return f"{heatwave:.1f}_{conflict:.1f}_{piracy:.1f}_{int(suez_blocked)}"


def predict_network_risk_deterministic(heatwave, conflict, piracy, suez_blocked):
    """
    Fallback deterministic causal propagation model.
    Implements the same node-edge rules as the Groq LLM prompt,
    ensuring identical output structure without the API dependency.
    """
    risks = [10.0, 15.0, 20.0, 25.0, 10.0, 30.0]
    if suez_blocked:
        risks[5] += 60.0; risks[4] += 15.0; risks[0] += 10.0
    risks[5] += piracy   * 50.0; risks[1] += piracy   * 10.0
    risks[1] += conflict * 20.0; risks[2] += conflict * 40.0
    risks[3] += conflict * 60.0; risks[4] += conflict *  5.0
    risks[1] += heatwave * 30.0; risks[2] += heatwave * 30.0
    return [round(min(r, 100.0) / 100.0, 4) for r in risks]


async def predict_network_risk(heatwave, conflict, piracy, suez_blocked):
    """
    Hybrid GNN risk engine:
      Primary  — Groq Llama-3.1-8b-instant acts as a graph propagation oracle.
                 The LLM receives the 6-node topology and stressor parameters
                 and returns propagated risk scores (0-1 per node).
      Fallback — deterministic causal model with identical output contract.
      Cache    — 30-second TTL prevents Groq rate-limit exhaustion on
                 rapid identical calls from the frontend.

    Node Map: Mumbai(0) UAE(1) Saudi(2) Israel(3) Greece(4) Suez/RedSea(5)
    """
    key = _cache_key(heatwave, conflict, piracy, suez_blocked)
    cached = _risk_cache.get(key)
    if cached and (_time.time() - cached["ts"] < _CACHE_TTL_SECONDS):
        return cached["result"]

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        result = predict_network_risk_deterministic(
            heatwave, conflict, piracy, suez_blocked)
        _risk_cache[key] = {"result": result, "ts": _time.time()}
        return result

    try:
        client = Groq(api_key=api_key)
        prompt = f"""
You are an AI-GNN Node Engine. Predict risk scores for a 6-node network
(0-1-2-3-4-5) between Mumbai and Greece.
Network Topology:
  Mumbai(0) --[Sea]--> UAE(1) --[Land]--> Saudi(2) --[Land]--> Israel(3)
  Israel(3) --[Sea]--> Greece(4)
  Port(5) = Suez / Red Sea corridor connecting Mumbai(0) to Greece(4).

INPUT PARAMETERS (0.0 to 1.0):
  Heatwave Exposure : {heatwave}
  Regional Conflict : {conflict}
  Maritime Piracy   : {piracy}
  Suez Blocked      : {suez_blocked}

TASK: Propagate stressors through the network.
  - Conflict at Israel(3) elevates Saudi(2) and Greece(4).
  - Piracy elevates Red Sea(5) and UAE(1).
  - Suez blockage spikes nodes 5, 4, and 0.
  - Heatwave degrades UAE(1) and Saudi(2) rail/road efficiency.

RETURN ONLY a JSON list of 6 floats [0.0–1.0] for nodes 0–5.
Example: [0.12, 0.45, 0.78, 0.89, 0.23, 0.95]
"""
        print("🤖 Calling AI-GNN Prophet for risk propagation...")
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "text"}
        )
        response_text = completion.choices[0].message.content
        match = re.search(r'\[.*?\]', response_text, re.DOTALL)
        if match:
            scores = json.loads(match.group(0))
            if len(scores) == 6:
                result = [round(float(s), 4) for s in scores]
                _risk_cache[key] = {"result": result, "ts": _time.time()}
                return result

        result = predict_network_risk_deterministic(
            heatwave, conflict, piracy, suez_blocked)
        _risk_cache[key] = {"result": result, "ts": _time.time()}
        return result

    except Exception as e:
        print(f"Prophet AI Error: {e}")
        result = predict_network_risk_deterministic(
            heatwave, conflict, piracy, suez_blocked)
        _risk_cache[key] = {"result": result, "ts": _time.time()}
        return result
