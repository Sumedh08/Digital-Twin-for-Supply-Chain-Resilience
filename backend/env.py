import gymnasium as gym
from gymnasium import spaces
import numpy as np

class LogisticsEnv(gym.Env):
    """
    Custom Environment that follows gymnasium interface.
    The agent must choose between Route A (Suez) and Route B (IMEC).
    """
    
    def __init__(self):
        super(LogisticsEnv, self).__init__()
        # ACTION SPACE: 0 = Suez, 1 = IMEC
        self.action_space = spaces.Discrete(2)
        
        # OBSERVATION SPACE: [heatwave, conflict, piracy, suez_blocked]
        # All normalized 0.0 to 1.0 (suez_blocked is 0 or 1)
        self.observation_space = spaces.Box(low=0, high=1, shape=(4,), dtype=np.float32)
        
        self.state = None

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        # Randomize risk factors for training
        self.state = np.array([
            np.random.rand(), # heatwave
            np.random.rand(), # conflict
            np.random.rand(), # piracy
            np.random.choice([0.0, 1.0], p=[0.9, 0.1]) # suez_blocked (10% chance)
        ], dtype=np.float32)
        return self.state, {}

    def step(self, action):
        heatwave, conflict, piracy, suez_blocked = self.state
        
        # CALCULATE COSTS (Simplified Simulation Logic)
        
        # 1. IMEC COST directly depends on Heat & Conflict
        # Base cost = 12 days. Max penalty = +15 days.
        imec_penalty = (heatwave * 5) + (conflict * 20)
        imec_cost = 12 + imec_penalty
        
        # 2. SUEZ COST directly depends on Piracy & Blockage
        # Base cost = 18 days. Blockage = +30 days. Piracy = +10 days.
        suez_penalty = (piracy * 10) + (suez_blocked * 30)
        suez_cost = 18 + suez_penalty
        
        # REWARD
        # Agent wants MINIMUM cost.
        # If action 0 (Suez): Reward = -suez_cost
        # If action 1 (IMEC): Reward = -imec_cost
        if action == 0:
            reward = -suez_cost
            chosen_cost = suez_cost
        else:
            reward = -imec_cost
            chosen_cost = imec_cost
            
        # Done after 1 step (Contextual Bandit style)
        terminated = True
        truncated = False
        
        info = {
            "imec_cost": imec_cost, 
            "suez_cost": suez_cost, 
            "optimal": "IMEC" if imec_cost < suez_cost else "SUEZ"
        }
        
        return self.state, reward, terminated, truncated, info
