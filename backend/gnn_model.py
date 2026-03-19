import torch
import torch.nn as nn
import torch.nn.functional as F

class SimpleGCNLayer(nn.Module):
    def __init__(self, in_features, out_features):
        super(SimpleGCNLayer, self).__init__()
        self.linear = nn.Linear(in_features, out_features)

    def forward(self, x, adj):
        # Graph Convolution: A * X * W
        # 1. Aggregate neighbors (Matrix multiplication with Adjacency)
        # 2. Apply Linear Transformation
        out = torch.matmul(adj, x)
        out = self.linear(out)
        return out

class IMEC_GNN(nn.Module):
    def __init__(self):
        super(IMEC_GNN, self).__init__()
        # Input features: [Risk Level (0-1), Connectivity Score]
        self.gcn1 = SimpleGCNLayer(2, 4)
        self.gcn2 = SimpleGCNLayer(4, 1) # Output: Final Predicted Risk score

    def forward(self, x, adj):
        x = F.relu(self.gcn1(x, adj))
        x = torch.sigmoid(self.gcn2(x, adj)) # Output between 0 and 1
        return x

# --- GRAPH DEFINITION (IMEC CORRIDOR) ---
# Nodes: 0:Mumbai, 1:UAE, 2:Saudi, 3:Israel, 4:Greece, 5:Red Sea(Suez)
# Adjacency Matrix (1 = Connected)
# Mumbai -> UAE, Red Sea
# UAE -> Mumbai, Saudi
# Saudi -> UAE, Israel
# Israel -> Saudi, Greece
# Greece -> Israel, Red Sea
# Red Sea -> Mumbai, Greece

num_nodes = 6
adj_matrix = torch.tensor([
    [1, 1, 0, 0, 0, 1], # Mumbai
    [1, 1, 1, 0, 0, 0], # UAE
    [0, 1, 1, 1, 0, 0], # Saudi
    [0, 0, 1, 1, 1, 0], # Israel
    [0, 0, 0, 1, 1, 1], # Greece
    [1, 0, 0, 0, 1, 1]  # Red Sea
], dtype=torch.float32)

# Normalize Adjacency
row_sum = torch.sum(adj_matrix, dim=1)
d_inv_sqrt = torch.pow(row_sum, -0.5)
d_mat = torch.diag(d_inv_sqrt)
norm_adj = torch.matmul(torch.matmul(d_mat, adj_matrix), d_mat)

model = IMEC_GNN()

def predict_network_risk(heatwave, conflict, piracy, suez_blocked):
    """
    Uses GNN to predict how risks propagate through the network.
    """
    # Node Features: [Direct Risk, Hub Importance]
    # Mumbai: Low direct risk
    # UAE: Heatwave risk
    # Saudi: Heatwave + Conflict risk
    # Israel: Conflict risk
    # Greece: Low risk
    # Red Sea: Piracy + Blockage
    
    node_features = torch.tensor([
        [0.1, 1.0], # Mumbai
        [heatwave * 0.5, 0.8], # UAE
        [max(heatwave, conflict), 0.8], # Saudi
        [conflict, 0.7], # Israel
        [0.1, 0.9], # Greece
        [max(piracy, 1.0 if suez_blocked else 0.0), 0.6] # Red Sea
    ], dtype=torch.float32)
    
    with torch.no_grad():
        risk_scores = model(node_features, norm_adj)
        
    return risk_scores.squeeze().tolist()
