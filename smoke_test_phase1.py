"""Phase 1 smoke test — run from project root: python smoke_test_phase1.py"""
import sys
import asyncio
sys.path.insert(0, '.')

def test_stochastic_engine():
    from backend.services.stochastic_events import stochastic_engine
    res = stochastic_engine.sample_events(simulation_month=6, num_simulations=500, route="suez")
    assert res["p95_delay_days"] >= res["p50_delay_days"], "P95 delay must be >= P50 delay"
    assert len(res["event_frequency_table"]) <= 4, "Should be max 4 events"
    assert "mean_delay_days" in res
    print(f"[PASS] Stochastic Events:  Avg delay = {res['mean_delay_days']:.1f} days, Chance = {res['probability_any_disruption']*100:.1f}%")

def test_system_dynamics():
    from backend.services.system_dynamics import twin_engine
    res = twin_engine.run(duration_days=30, dt=1.0)
    final = res["final_state"]
    assert final["time_days"] == 30.0, "Simulation horizon mismatch"
    assert final["carbon_pool_tco2"] > 0, "Carbon pool must grow"
    diag = res["loop_diagnostics"]
    print(f"[PASS] System Dynamics  :  Final ETS = {final['ets_price_eur']:.2f} EUR, Loop = {diag['dominant_feedback_loop'].split(' ')[0]}")

def test_pareto_optimizer():
    # Need to mock the emission_calculator for the pareto_optimizer
    from backend.services.emission_calculator import EmissionCalculator
    from backend import main  # This imports EmissionCalculator into main's namespace
    import backend.services.pareto_optimizer as po

    res = po.pareto_optimizer.optimize(
        cargo_weight_t=1000,
        ets_price_eur=85.0,
        charter_rate_usd_per_day=35000.0,
        suez_blocked=True
    )
    assert not any(s["route"] == "suez" for s in res["pareto_front"]), "Blocked route not excluded"
    assert len(res["pareto_front"]) > 0, "Pareto front should not be empty"
    rec = res["balanced_recommendation"]
    print(f"[PASS] Pareto Optimizer :  Front size = {res['front_size']}, Rec = {rec['fuel_type']} @ {rec['speed_knots']}kn via {rec['route']}")

def test_weather_service():
    from backend.services.weather_service import weather_service
    # Test valid API URL format
    res = weather_service.get_route_weather(route_key="imec", simulation_month=6)
    assert len(res["waypoints"]) == 5, "Missing waypoints"
    assert 0.0 <= res["speed_penalty_factor"] <= 1.0, "Penalty factor out of bounds"
    print(f"[PASS] Weather Service  :  Route = {res['route']}, Status = {res['route_summary']['route_status']}")

def test_slow_steam_main():
    # Only tests if it imports cleanly, logic covered in Phase 0
    import backend.main as main
    assert hasattr(main, "optimize_slow_steam")

if __name__ == "__main__":
    try:
        test_stochastic_engine()
        test_system_dynamics()
        test_pareto_optimizer()
        test_weather_service()
        test_slow_steam_main()
        print("\n=======================================================")
        print("  All Phase 1 upgrade smoke tests PASSED")
        print("=======================================================")
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
