import os
from groq import Groq
import re
import json

def predict_network_risk_deterministic(heatwave, conflict, piracy, suez_blocked):
    """Fallback deterministic logic."""
    risks = [10.0, 15.0, 20.0, 25.0, 10.0, 30.0]
    if suez_blocked:
        risks[5] += 60.0; risks[4] += 15.0; risks[0] += 10.0
    risks[5] += piracy * 50.0; risks[1] += piracy * 10.0
    risks[1] += conflict * 20.0; risks[2] += conflict * 40.0; risks[3] += conflict * 60.0; risks[4] += conflict * 5.0
    risks[1] += heatwave * 30.0; risks[2] += heatwave * 30.0
    
    return [round(min(r, 100.0) / 100.0, 4) for r in risks]

async def predict_network_risk(heatwave, conflict, piracy, suez_blocked):
    """
    Uses Groq Llama 3.3 to simulate a Graph Neural Network propagation.
    The AI acts as the weights of the GNN, predicting how geopolitical 
    stressors (heatwave, conflict, piracy) propagate from Mumbai to Greece.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return predict_network_risk_deterministic(heatwave, conflict, piracy, suez_blocked)
    
    try:
        client = Groq(api_key=api_key)
        prompt = f"""
        You are an AI-GNN Node Engine. Predict risk scores for a 6-node network (0-1-2-3-4-5) between Mumbai and Greece.
        Network Topology: Mumbai(0)-[Sea]-UAE(1)-[Land]-Saudi(2)-[Land]-Israel(3)-[Sea]-Greece(4), Port(5) is Suez/Red Sea connecting 0 to 4.
        
        INPUT PARAMETERS (0.0 to 1.0):
        - Heatwave Exposure: {heatwave}
        - Regional Conflict: {conflict}
        - Maritime Piracy: {piracy}
        - Suez Canal Blocked: {suez_blocked}
        
        TASK:
        Propagate these stressors through the nodes. Consider that Conflict in Israel (3) increases risk in Saudi (2) and Greece (4). Suez Blockage (5) spikes risk in 0 and 4.
        
        RETURN ONLY A JSON LIST OF 6 FLOATS (0.0 to 1.0) for indices [0 to 5]:
        Example: [0.12, 0.45, 0.78, 0.89, 0.23, 0.95]
        """
        
        print(f"🤖 Calling AI-GNN Prophet for risk propagation...")
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant", # Faster model for simulation
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "text"}
        )
        
        response_text = completion.choices[0].message.content
        match = re.search(r'\[.*\]', response_text)
        if match:
            scores = json.loads(match.group(0))
            if len(scores) == 6:
                return [round(float(s), 4) for s in scores]
                
        return predict_network_risk_deterministic(heatwave, conflict, piracy, suez_blocked)
        
    except Exception as e:
        print(f"Prophet AI Error: {e}")
        return predict_network_risk_deterministic(heatwave, conflict, piracy, suez_blocked)
