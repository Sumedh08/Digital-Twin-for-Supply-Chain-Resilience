import pandas as pd
import numpy as np

# Set seed for reproducibility of the simulation (not random generation)
np.random.seed(42)

def calculate_fuel_admiralty(speed_knots, displacement_tonnes, admiralty_constant):
    """
    Admiralty Coefficient Formula:
    Fuel Consumption (tonnes/day) = (Displacement^(2/3) * Speed^3) / Admiralty_Constant
    
    This is a standard Naval Architecture formula for estimating ship power and fuel.
    """
    return (np.power(displacement_tonnes, 2/3) * np.power(speed_knots, 3)) / admiralty_constant

def generate_physics_data(num_samples=3000):
    data = []
    
    # Standard Admiralty Constants (C) for different ship types
    # Higher C = More efficient hull form
    ship_params = {
        'Container Ship': {'C': 600, 'Disp_Range': (50000, 200000), 'Speed_Range': (12, 24)},
        'Bulk Carrier':   {'C': 550, 'Disp_Range': (30000, 150000), 'Speed_Range': (10, 16)},
        'Oil Tanker':     {'C': 580, 'Disp_Range': (40000, 300000), 'Speed_Range': (11, 15)},
        'Ro-Ro Cargo':    {'C': 500, 'Disp_Range': (20000, 60000),  'Speed_Range': (14, 20)},
        'General Cargo':  {'C': 450, 'Disp_Range': (10000, 40000),  'Speed_Range': (10, 14)}
    }
    
    routes = ['Asia-Europe', 'Trans-Pacific', 'North Atlantic', 'Indian Ocean', 'Intra-Asia']

    for _ in range(num_samples):
        # Select Ship Type
        ship_type = np.random.choice(list(ship_params.keys()))
        params = ship_params[ship_type]
        
        # Physics Parameters
        displacement = np.random.uniform(params['Disp_Range'][0], params['Disp_Range'][1])
        speed = np.random.uniform(params['Speed_Range'][0], params['Speed_Range'][1])
        
        # Calculate Fuel using PHYSICS FORMULA
        fuel_per_day = calculate_fuel_admiralty(speed, displacement, params['C'])
        
        # Voyage Parameters
        distance = np.random.uniform(500, 12000)
        days = distance / (speed * 24)
        
        # Weather Impact (Physics: Added Resistance)
        # 0 = Calm, 1 = Storm (Adds 10-30% resistance)
        weather_index = np.random.choice([0, 0.2, 0.4, 0.6, 0.8], p=[0.5, 0.2, 0.15, 0.1, 0.05])
        weather_penalty = 1 + (weather_index * 0.3)
        
        total_fuel_consumption = fuel_per_day * days * weather_penalty
        
        # CO2 Emissions (Standard Factor: 3.114 tonnes CO2 per tonne HFO)
        co2_emissions = total_fuel_consumption * 3.114
        
        # Draft (Approximation based on displacement)
        # Draft ~ Displacement^(1/3)
        draft = np.power(displacement / 1000, 1/3) * 2.5 

        data.append({
            'ship_type': ship_type,
            'route_type': np.random.choice(routes),
            'distance_nm': round(distance, 2),
            'speed_knots': round(speed, 2),
            'draft_m': round(draft, 2),
            'cargo_weight_tonnes': round(displacement * 0.8, 2), # Approx deadweight
            'weather_impact_index': round(weather_index, 1),
            'fuel_consumption_tonnes': round(total_fuel_consumption, 2),
            'co2_emissions_tonnes': round(co2_emissions, 2)
        })
        
    return pd.DataFrame(data)

if __name__ == "__main__":
    df = generate_physics_data()
    output_path = "backend/data/ship_fuel_dataset.csv"
    df.to_csv(output_path, index=False)
    print(f"Physics-Based Dataset generated at {output_path}")
    print("Formula Used: Admiralty Coefficient (Naval Architecture Standard)")
