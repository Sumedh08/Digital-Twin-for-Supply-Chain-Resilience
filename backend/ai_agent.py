import os
import numpy as np
from stable_baselines3 import PPO
from .env import LogisticsEnv

MODEL_PATH = "backend/ppo_imec_model"

def train_agent():
    """Trains the PPO agent if model doesn't exist"""
    print("Training RL Agent...")
    env = LogisticsEnv()
    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=10000)
    model.save(MODEL_PATH)
    print("Model Saved!")
    return model

def get_agent_decision(heatwave, conflict, piracy, suez_blocked):
    """
    Returns the AI's chosen action (0 or 1)
    """
    # Load decision model or train if missing
    if os.path.exists(MODEL_PATH + ".zip"):
        model = PPO.load(MODEL_PATH)
    else:
        model = train_agent()
        
    obs = np.array([heatwave, conflict, piracy, 1.0 if suez_blocked else 0.0], dtype=np.float32)
    action, _ = model.predict(obs, deterministic=True)
    
    return int(action)
