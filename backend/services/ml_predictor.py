import joblib
import pandas as pd
import os
from pydantic import BaseModel

class PredictionRequest(BaseModel):
    ship_type: str
    distance_nm: float
    speed_knots: float
    draft_m: float
    cargo_weight_tonnes: float
    weather_impact_index: float = 0.0

class MLPredictor:
    def __init__(self):
        self.model_path = "backend/models/fuel_prediction_model.pkl"
        self.model = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                print(f"✅ ML Model loaded from {self.model_path}")
            except Exception as e:
                print(f"❌ Failed to load ML model: {e}")
        else:
            print(f"⚠️ Model file not found at {self.model_path}")

    def predict(self, data: PredictionRequest):
        if not self.model:
            return {"error": "Model not loaded"}
        
        # Convert input to DataFrame (expected by pipeline)
        input_df = pd.DataFrame([data.dict()])
        
        try:
            fuel_pred = self.model.predict(input_df)[0]
            co2_pred = fuel_pred * 3.114 # Standard factor
            
            return {
                "predicted_fuel_consumption_tonnes": round(fuel_pred, 2),
                "predicted_co2_emissions_tonnes": round(co2_pred, 2),
                "model_used": "RandomForestRegressor_v1"
            }
        except Exception as e:
            return {"error": str(e)}

ml_predictor = MLPredictor()
