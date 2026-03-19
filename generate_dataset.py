import pandas as pd
import numpy as np
import random

# Seed for reproducibility
np.random.seed(42)

def generate_ship_data(num_samples=2000):
    data = []
    
    # Ship Types and their base characteristics
    # Type: (Mean Speed (knots), Mean Draft (m), Efficiency Factor)
    ship_types = {
        'Container Ship': (18.0, 12.0, 1.2),
        'Bulk Carrier': (14.0, 10.0, 1.0),
        'Oil Tanker': (13.5, 15.0, 1.1),
        'Ro-Ro Cargo': (16.0, 8.0, 0.9),
        'General Cargo': (12.0, 7.0, 0.85)
    }
    
    routes = ['Asia-Europe', 'Trans-Pacific', 'North Atlantic', 'Indian Ocean', 'Intra-Asia']

    for _ in range(num_samples):
        ship_type = random.choice(list(ship_types.keys()))
        base_speed, base_draft, eff_factor = ship_types[ship_type]
        
        # 1. Distance (nautical miles) - Log-normal distribution for realistic route lengths
        distance = int(np.random.lognormal(mean=7.5, sigma=0.6)) 
        distance = max(500, min(distance, 12000)) # Clip to realistic range
        
        # 2. Speed (knots) - Normal distribution around base speed
        speed = np.random.normal(base_speed, 1.5)
        speed = max(5.0, min(speed, 25.0))
        
        # 3. Draft (meters) - How deep the ship is in water (Load factor)
        draft = np.random.normal(base_draft, 1.0)
        draft = max(5.0, min(draft, 20.0))
        
        # 4. Cargo Weight (tonnes) - Correlated with Draft
        # A simplified displacement calculation
        cargo_weight = (draft * 2000) + np.random.normal(0, 500)
        cargo_weight = max(1000, cargo_weight)

        # 5. Weather Condition (0=Calm, 1=Rough)
        weather_factor = np.random.choice([0, 0.1, 0.2, 0.3], p=[0.6, 0.2, 0.1, 0.1])
        
        # --- PHYSICS-BASED TARGET GENERATION ---
        # Admiralty Coefficient Formula Approximation: Fuel ~ Speed^3 * Displacement^(2/3)
        # We add noise to make it a "learning" problem, not just a formula
        
        # Base consumption (tonnes per day)
        # Speed is the dominant factor (cubic relationship)
        speed_impact = (speed / 12.0) ** 3 
        
        # Draft/Weight impact
        load_impact = (cargo_weight / 10000) * 0.5
        
        # Daily Fuel Consumption (tonnes/day)
        daily_fuel = (15 * eff_factor * speed_impact) + load_impact
        
        # Add Weather Impact
        daily_fuel *= (1 + weather_factor)
        
        # Add random noise (engine efficiency variations, hull fouling)
        daily_fuel *= np.random.uniform(0.9, 1.1)
        
        # Total Fuel for Voyage (tonnes)
        days_at_sea = distance / (speed * 24)
        total_fuel = daily_fuel * days_at_sea
        
        # CO2 Emissions (tonnes) - Standard factor approx 3.114 for HFO
        co2_emissions = total_fuel * 3.114

        data.append({
            'ship_type': ship_type,
            'route_type': random.choice(routes),
            'distance_nm': round(distance, 2),
            'speed_knots': round(speed, 2),
            'draft_m': round(draft, 2),
            'cargo_weight_tonnes': round(cargo_weight, 2),
            'weather_impact_index': weather_factor,
            'fuel_consumption_tonnes': round(total_fuel, 2),
            'co2_emissions_tonnes': round(co2_emissions, 2)
        })
        
    return pd.DataFrame(data)

if __name__ == "__main__":
    df = generate_ship_data(3000)
    # Save to CSV
    output_path = "backend/data/ship_fuel_dataset.csv"
    df.to_csv(output_path, index=False)
    print(f"Dataset generated with {len(df)} samples at {output_path}")
    print(df.head())
