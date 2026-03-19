import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import os

# 1. Load Data
data_path = "backend/data/ship_fuel_dataset.csv"
if not os.path.exists(data_path):
    print("Dataset not found! Run generate_dataset.py first.")
    exit()

df = pd.read_csv(data_path)

# 2. Features & Target
X = df[['ship_type', 'distance_nm', 'speed_knots', 'draft_m', 'cargo_weight_tonnes', 'weather_impact_index']]
y = df['fuel_consumption_tonnes']

# 3. Preprocessing Pipeline
# Categorical columns need encoding
categorical_features = ['ship_type']
numerical_features = ['distance_nm', 'speed_knots', 'draft_m', 'cargo_weight_tonnes', 'weather_impact_index']

preprocessor = ColumnTransformer(
    transformers=[
        ('num', 'passthrough', numerical_features),
        ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
    ])

# 4. Model Pipeline (Random Forest is robust and "traditional")
model = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))
])

# 5. Train-Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 6. Train
print("Training Random Forest Model...")
model.fit(X_train, y_train)

# 7. Evaluate
predictions = model.predict(X_test)
mae = mean_absolute_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print(f"Model Trained Successfully!")
print(f"Mean Absolute Error: {mae:.2f} tonnes")
print(f"R² Score: {r2:.4f} (Accuracy)")

# 8. Save Model
model_dir = "backend/models"
os.makedirs(model_dir, exist_ok=True)
model_path = os.path.join(model_dir, "fuel_prediction_model.pkl")
joblib.dump(model, model_path)
print(f"Model saved to {model_path}")
