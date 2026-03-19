# 🌍 CarbonShip - AI-Powered CBAM Compliance Platform

> **Enterprise-Grade Digital Twin for Indian Steel & Aluminium Exporters**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com)
[![Blockchain](https://img.shields.io/badge/Blockchain-CarbonChain-purple.svg)](#)
[![AI](https://img.shields.io/badge/AI-Gemma%203%2012B-green.svg)](#)

---

## 🎯 Executive Summary

CarbonShip is an **AI-powered SaaS platform** that helps large Indian exporters (Tata Steel, JSW, Vedanta) comply with the EU's **Carbon Border Adjustment Mechanism (CBAM)**.

### 💰 The Problem
- EU CBAM tax becomes **100% enforceable on Jan 1, 2026**
- India exports **$12+ billion** of steel/aluminium to EU annually
- Non-compliance = **€85+/tonne tax** + shipment delays + loss of European market

### 🚀 Our Solution
A **Command Center** for Compliance:

| Feature | Description |
|---------|-------------|
| **🧮 CBAM Calculator** | Physics-based emission calculation using IPCC factors |
| **🌐 Live Vessel Tracking** | Real-time AIS data from 50+ ships on India-EU routes |
| **📊 ETS Price Feed** | Live EU carbon price with 7-day charts |
| **⛓️ Blockchain Ledger** | Smart Contract for immutable tax verification |
| **🤖 AI Sentinel** | Gemma 3 12B for geopolitical risk analysis |
| **⚖️ Legal Advisor** | CBAM regulation Q&A chatbot |
| **🗺️ Route Simulator** | IMEC vs Suez comparison with AI recommendation |

---

## 🖥️ Screenshots

### Dashboard
- 3D Globe with live vessel positions
- Real-time ETS carbon price widget
- CBAM emission calculator

### AI Insights Modal
- Supply Chain Sentinel (Risk Analysis)
- Smart Document Parser
- Legal Advisor Chatbot
- **CarbonChain Blockchain Ledger**

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite, Tailwind CSS, react-globe.gl |
| **Backend** | FastAPI (Python 3.11+) |
| **AI - LLM** | Google Gemma 3 12B (via Generative AI SDK) |
| **AI - GNN** | PyTorch (Supply Chain Risk Prediction) |
| **AI - RL** | Stable-Baselines3 PPO (Route Optimization) |
| **AI - ML** | Random Forest (Fuel Consumption Prediction) |
| **Blockchain** | CarbonChain (Private PoW with Oracle) |
| **Data** | Live AIS (AISStream.io), EU ETS, IPCC |

---

## 📁 Project Structure

```
carbonship/
├── backend/
│   ├── services/
│   │   ├── smart_contract.py     # Blockchain + Oracle + Smart Contract
│   │   ├── emission_calculator.py # CBAM calculation engine
│   │   ├── ai_sentinel.py        # Gemma AI risk analysis
│   │   ├── legal_advisor.py      # CBAM Q&A chatbot
│   │   ├── live_ais_service.py   # Real-time vessel tracking
│   │   └── ets_price_service.py  # EU ETS price feed
│   ├── main.py                   # FastAPI endpoints
│   └── gnn_model.py              # Graph Neural Network
├── src/
│   ├── components/
│   │   ├── BlockchainLedger.jsx  # Blockchain visualizer
│   │   ├── AISentinel.jsx        # Risk analysis widget
│   │   ├── VesselTracker.jsx     # Live ship list
│   │   └── LiveETSPrice.jsx      # Carbon price widget
│   ├── App.jsx                   # Main dashboard
│   ├── CBAMCalculator.jsx        # Emission calculator
│   └── GlobeComponent.jsx        # 3D Globe
└── README.md
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Backend
pip install -r requirements.txt

# Frontend
npm install
```

### 2. Configure Environment

```bash
# Create .env file
echo "GOOGLE_API_KEY=your_gemini_api_key" > .env
echo "AISSTREAM_API_KEY=your_aisstream_key" >> .env
```

### 3. Run the Backend

```bash
python -m uvicorn backend.main:app --reload
```

### 4. Run the Frontend

```bash
npm run dev
```

### 5. Open in Browser

```
http://localhost:5173
```

---

## 📡 API Endpoints

### CBAM Compliance
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/cbam/calculate` | POST | Calculate emissions for shipment |
| `/cbam/compare-routes` | POST | Compare routes by carbon |
| `/cbam/generate-report` | POST | Generate PDF compliance report |

### Blockchain
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/blockchain/execute` | POST | Execute Smart Contract |
| `/blockchain/chain` | GET | View full blockchain |
| `/blockchain/oracle` | GET | Get Oracle data (ETS price) |

### AI Intelligence
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ai/sentinel` | GET | Geopolitical risk analysis |
| `/ai/legal` | POST | Ask CBAM legal questions |

### Live Data
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/live/ais` | GET | Real-time vessel positions |
| `/ets/live-price` | GET | Current EU ETS price |

---

## 📊 Data Sources

| Data Type | Source | Free? |
|-----------|--------|-------|
| Manufacturing Factors | IPCC EFDB | ✅ |
| Transport Factors | GLEC Framework v3.0 | ✅ |
| Vessel Positions | AISStream.io | ✅ |
| EU ETS Price | Simulated (Real API: Ember) | ✅ |
| CBAM Regulations | EUR-Lex | ✅ |

---

## ✅ Features Completed

- [x] CBAM Emission Calculator
- [x] PDF Report Generator
- [x] 3D Globe Visualization
- [x] Live Vessel Tracking (AIS WebSocket)
- [x] EU ETS Price Widget
- [x] AI Risk Sentinel (Gemma 3 12B)
- [x] Legal Advisor Chatbot
- [x] Route Simulator (IMEC vs Suez)
- [x] **Blockchain Smart Contract**
- [x] **Block Explorer UI**
- [x] User Authentication

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

## 👥 Team

- **Sumedh** - Full Stack Developer

---

*Built with ❤️ for Indian Exporters*
