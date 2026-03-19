# 🌍 CARBONSHIP: COMPLETE BUSINESS & IMPLEMENTATION PLAN
## *AI-Powered CBAM Compliance Platform for Indian Exporters*

**Version:** Final 1.0  
**Date:** January 16, 2026  
**Author:** Sumedh  
**Repository:** Digital-Twin-for-Supply-Chain-Resilience

---

# PART 1: EXECUTIVE SUMMARY

## 1.1 The Problem

The European Union's **Carbon Border Adjustment Mechanism (CBAM)** became fully operational on **January 1, 2026**. This regulation requires ALL exporters of steel, aluminium, cement, fertilizers, and hydrogen to:
- Calculate and report embedded carbon emissions for every shipment
- Get emissions data verified by EU-accredited third parties
- Pay carbon taxes based on EU ETS prices (~€85/tonne CO2)

**The Crisis for Indian Exporters:**
- India exports **$12+ billion** of CBAM-affected goods to EU annually
- **100% of SME exporters** lack tools to calculate carbon footprints
- Steel/aluminium exports to EU already **declined 24.4% in FY 2024-25**
- Non-compliance means **higher taxes, shipment delays, or rejection at EU borders**

## 1.2 The Solution

**CarbonShip** is an AI-powered SaaS platform that helps Indian exporters:
1. **Calculate** embedded carbon emissions using authoritative emission factors
2. **Generate** EU-compliant CBAM reports automatically
3. **Compare** shipping routes by carbon footprint (Suez vs IMEC)
4. **Optimize** costs by finding greener, cheaper alternatives
5. **Consult** an AI advisor for CBAM compliance questions

## 1.3 Why This Will Succeed

| Factor | Evidence |
|--------|----------|
| **Timing** | CBAM is LIVE now (Jan 2026). Not "coming soon." |
| **Mandatory** | Compliance is legally required, not optional. |
| **Large Market** | 4,000+ Indian exporters in CBAM sectors |
| **No Competition** | No India-focused CBAM tool exists for SMEs |
| **Revenue from Day 1** | SaaS subscription model |

---

# PART 2: MARKET ANALYSIS

## 2.1 Target Market Size

| Sector | India's EU Exports | CBAM Tax Exposure | # of Exporters |
|--------|-------------------|-------------------|----------------|
| Iron & Steel | $8.2 Billion | ~$1.6 Billion | 2,500+ |
| Aluminium | $2.1 Billion | ~$420 Million | 800+ |
| Cement | $150 Million | ~$30 Million | 200+ |
| Fertilizers | $1.8 Billion | ~$360 Million | 500+ |
| **TOTAL** | **$12.25 Billion** | **$2.4+ Billion** | **4,000+** |

## 2.2 Customer Pain Points

1. **No Tools:** SMEs use Excel spreadsheets or nothing at all
2. **Complex Regulations:** 500+ pages of EU CBAM rules, in legalese
3. **Verification Burden:** Must get third-party audits (costly, confusing)
4. **Time Pressure:** Quarterly reports due, penalties for lateness
5. **Cost Uncertainty:** Don't know how much CBAM tax they'll owe

## 2.3 Competitive Landscape

| Competitor | Focus | Why We Win |
|------------|-------|------------|
| Persefoni | US Enterprise | Too expensive ($50k+), not India-focused |
| Watershed | Scope 3 Reporting | No CBAM-specific features |
| CA Firms | Manual Consulting | Slow, expensive, no tech platform |
| **CarbonShip** | Indian SME Exporters | Affordable, localized, AI-powered |

---

# PART 3: PRODUCT FEATURES

## 3.1 Core Features (MVP - 6 Weeks)

### Feature 1: Emission Calculator
**User Input:** Product type, weight, origin port, destination port, transport mode
**Output:** Total CO2e (tonnes), breakdown by manufacturing/transport/handling, CBAM tax estimate

### Feature 2: CBAM Report Generator
**Output:** EU-compliant PDF/XML with all required fields:
- Product CN code
- Embedded emissions
- Calculation methodology
- Verification status

### Feature 3: Green Route Comparator (3D Globe)
**Visualization:** Interactive globe showing:
- Route A (Suez Canal): CO2, cost, time
- Route B (IMEC Rail): CO2, cost, time
- Recommendation with savings calculation

### Feature 4: RAG Compliance Advisor
**Chatbot:** Answer any CBAM question using EU official documents as knowledge base.

### Feature 5: Verification Checklist
**Tool:** Document checklist for third-party audit preparation.

## 3.2 Advanced Features (Phase 2 - Months 3-6)

| Feature | Description |
|---------|-------------|
| Supply Chain Mapping | GNN-powered supplier carbon analysis |
| Carbon Price Forecasting | Predict EU ETS prices using ML |
| Trade Finance Integration | Connect carbon scores to loan rates |
| WhatsApp Bot | Quick calculations via chat |
| Tally Integration | Auto-pull invoice data from accounting software |
| EU Buyer Portal | Let importers access exporter carbon data |

---

# PART 4: TECHNICAL ARCHITECTURE

## 4.1 System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React + Vite)                 │
│  Dashboard │ Globe Visualization │ Report Generator │ Chat  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                       │
│  /api/calculate │ /api/reports │ /api/routes │ /api/chat    │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   AI LAYER      │ │   DATA LAYER    │ │   STORAGE       │
│ • GNN (PyTorch) │ │ • Emission DB   │ │ • PostgreSQL    │
│ • RL (SB3)      │ │ • Distance API  │ │ • Redis Cache   │
│ • RAG (LangChain)│ │ • Price API    │ │ • FAISS Vectors │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## 4.2 Tech Stack

| Layer | Technology | Justification |
|-------|------------|---------------|
| Frontend | React 18 + Vite + Tailwind | Existing codebase |
| 3D Visualization | react-globe.gl | Existing codebase |
| Backend | FastAPI (Python 3.11+) | Existing codebase |
| AI - GNN | PyTorch | Existing codebase |
| AI - RL | Stable-Baselines3 | Existing codebase |
| AI - RAG | LangChain + HuggingFace | Existing codebase |
| Database | SQLite (MVP) → PostgreSQL | Free, scalable |
| Vector Store | FAISS | Free, local |
| LLM | Mistral-7B (HuggingFace) | Free tier |

## 4.3 AI/ML Components

### Graph Neural Network (GNN)
**Purpose:** Model carbon flow through supply chain nodes
**Nodes:** Factories, Ports, Ships, Destinations
**Output:** Carbon contribution per node, risk propagation

### Reinforcement Learning (RL)
**Purpose:** Optimize route allocation to minimize (Cost + Carbon Tax)
**Action Space:** % allocation across routes (Suez, IMEC, Cape, Air)
**Reward:** Negative of total cost (minimize)

### RAG Chatbot
**Knowledge Base:** EU CBAM regulations, FICCI guidance, industry reports
**LLM:** Mistral-7B via HuggingFace (free tier)
**Vector Store:** FAISS (local, free)

---

# PART 5: DATA SOURCES (ALL FREE & VERIFIED)

## 5.1 Manufacturing Emission Factors

| Source | URL | Cost |
|--------|-----|------|
| **IPCC Emission Factor Database** | https://www.ipcc-nggip.iges.or.jp/EFDB/ | ✅ FREE |
| **UK BEIS/Defra GHG Factors** | gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors | ✅ FREE |

**Hardcoded Values (from IPCC):**
```python
MANUFACTURING_EMISSION_FACTORS = {
    "steel_hot_rolled": 1.85,      # tCO2/tonne
    "steel_cold_rolled": 2.10,
    "aluminium_primary": 14.5,
    "aluminium_secondary": 0.5,
    "cement_clinker": 0.85,
    "ammonia": 1.80,
    "urea": 0.73,
}
```

## 5.2 Transport Emission Factors

| Source | URL | Cost |
|--------|-----|------|
| **GLEC Framework v3.0** | https://www.smartfreightcentre.org/en/glec-framework/ | ✅ FREE PDF |

**Hardcoded Values (from GLEC):**
```python
TRANSPORT_EMISSION_FACTORS = {
    "sea_container": 16.0,    # gCO2/tonne-km
    "sea_bulk": 8.0,
    "rail_electric": 23.0,
    "rail_diesel": 35.0,
    "road_truck": 80.0,
    "air_freight": 560.0,
}
```

## 5.3 Sea Route Distances

| Source | URL | Cost |
|--------|-----|------|
| **Dataloy Distances API** | https://api.dataloy-systems.com/ | ✅ FREE (25 routes/month) |
| **Distance Tools API** | https://distance.tools/ | ✅ FREE (100 calls/month) |

**Hardcoded Fallback:**
```python
PORT_DISTANCES_NM = {
    ("INMUN", "NLRTM"): 6337,   # Mumbai → Rotterdam (Suez)
    ("INMUN", "DEHAM"): 6100,   # Mumbai → Hamburg
    ("INMUN", "AEJEA"): 1020,   # Mumbai → Jebel Ali (UAE)
    ("AEJEA", "ILASH"): 2800,   # Jebel Ali → Ashdod (IMEC)
    ("ILASH", "GRPIR"): 1400,   # Ashdod → Piraeus
}
```

## 5.4 EU ETS Carbon Prices

| Source | URL | Cost |
|--------|-----|------|
| **Apitalks EU ETS API** | https://api.store/ | ✅ FREE |
| **EEA Data Viewer** | https://www.eea.europa.eu/data-and-maps/dashboards/emissions-trading-viewer-1 | ✅ FREE |

**Current Price:** €85/tonne CO2 (January 2026)

## 5.5 Real-Time Data (Optional Enhancements)

| Data Type | Source | Cost |
|-----------|--------|------|
| Vessel Tracking | AISStream.io | ✅ FREE WebSocket |
| Geopolitical Events | GDELT Project | ✅ 100% FREE |
| Weather | OpenWeatherMap | ✅ FREE (1000 calls/day) |

## 5.6 CBAM Knowledge Base (For RAG)

| Document | Source | Cost |
|----------|--------|------|
| EU CBAM Regulation | EUR-Lex (European Law) | ✅ FREE PDF |
| Implementation Rules | EC Taxation & Customs | ✅ FREE PDF |
| FICCI CBAM Guide | FICCI India | ✅ FREE PDF |

---

# PART 6: IMPLEMENTATION ROADMAP

## 6.1 Phase 1: MVP (Weeks 1-6)

| Week | Task | Deliverable |
|------|------|-------------|
| 1 | Set up emission factors database | `backend/data/emission_factors.json` |
| 1 | Create emission calculator API | `backend/services/emission_calculator.py` |
| 2 | Build basic calculation UI | React form + results display |
| 2 | Create CBAM report template | PDF generator with EU format |
| 3 | Refactor Globe for route comparison | Carbon overlay on routes |
| 3 | Add route optimization logic | Compare Suez vs IMEC |
| 4 | Ingest CBAM docs for RAG | FAISS vector store |
| 4 | Update chatbot for CBAM | Rebrand from "IMEC Advisor" |
| 5 | User authentication | Login/signup with JWT |
| 5 | Dashboard with shipment history | SQLite database |
| 6 | Testing and bug fixes | End-to-end testing |
| 6 | **MVP LAUNCH** | Deploy to Vercel + Render |

## 6.2 Phase 2: Growth Features (Months 2-4)

| Month | Feature |
|-------|---------|
| 2 | Supply chain carbon mapping (GNN visualization) |
| 2 | Verification checklist and gap analysis |
| 3 | WhatsApp bot for quick calculations |
| 3 | Tally accounting integration |
| 4 | EU buyer portal (two-sided marketplace) |
| 4 | Carbon price forecasting |

## 6.3 Phase 3: Enterprise & Expansion (Months 5-12)

| Month | Feature |
|-------|---------|
| 5-6 | Trade finance integration (bank APIs) |
| 7-8 | UK CBAM support (new regulation) |
| 9-10 | API for freight forwarders (B2B) |
| 11-12 | Mobile app + international expansion |

---

# PART 7: BUSINESS MODEL

## 7.1 Pricing Tiers

| Plan | Price | Features | Target |
|------|-------|----------|--------|
| **Free** | ₹0 | 5 calculations/month | Trial users |
| **Starter** | ₹4,999/month | 50 calculations, reports, email support | Small SMEs |
| **Professional** | ₹24,999/month | Unlimited, route optimizer, Tally integration | Mid-size |
| **Enterprise** | ₹1,00,000+/month | API access, custom integrations, SLA | Large exporters |

## 7.2 Additional Revenue Streams

| Stream | Model | Potential |
|--------|-------|-----------|
| Verification Referrals | Commission from audit partners | ₹5-10k/referral |
| Carbon Credits | Transaction fee on offsets | 5-10% |
| Trade Finance | Revenue share with banks | 0.1% of loan |
| Premium Data | Industry benchmarks subscription | ₹50k+/year |

## 7.3 Revenue Projections

| Year | Customers | ARR |
|------|-----------|-----|
| Year 1 | 200 | ₹1.2 Crore |
| Year 2 | 1,000 | ₹8 Crore |
| Year 3 | 5,000 | ₹40 Crore |

---

# PART 8: GO-TO-MARKET STRATEGY

## 8.1 Phase 1: Awareness (Months 1-3)

**Channel 1: Industry Associations**
- Partner with FICCI, CII, EEPC India
- Co-host "CBAM Compliance Workshops"
- Get endorsement and member access

**Channel 2: Content Marketing**
- Free "CBAM Calculator" tool as lead magnet
- Weekly "CBAM Digest" newsletter
- LinkedIn thought leadership
- YouTube explainers in Hindi/English

## 8.2 Phase 2: Acquisition (Months 4-6)

**Channel 3: Direct Sales**
- Target top 100 steel/aluminium exporters
- Offer 30-day free pilot programs
- Collect testimonials and case studies

**Channel 4: Partner Referrals**
- Partner with freight forwarders (DHL, Allcargo)
- Revenue share on referrals

## 8.3 Phase 3: Scale (Months 7-12)

**Channel 5: Enterprise Sales**
- Dedicated sales team
- Government empanelment (GeM portal)

**Channel 6: International**
- Expand to UK CBAM compliance
- Target Southeast Asian exporters

---

# PART 9: FUNDRAISING STRATEGY

## 9.1 Funding Stages

| Stage | Amount | Timeline | Use of Funds |
|-------|--------|----------|--------------|
| Pre-Seed | ₹20-50 Lakh | Now | MVP, 3-person team |
| Seed | ₹1-2 Crore | Month 6 | Launch, 10-person team |
| Series A | ₹15-25 Crore | Month 18 | Scale, international |

## 9.2 Target Investors

**Incubators:**
- Y Combinator
- Antler India
- Techstars Sustainability

**VC Funds (India):**
- Blume Ventures
- Kalaari Capital
- Lightspeed India
- Omnivore

**VC Funds (Global Climate):**
- Congruent Ventures
- Lowercarbon Capital

## 9.3 Pitch Summary

> "The EU just activated the world's first Carbon Border Tax. Indian exporters are losing millions because they can't calculate their carbon footprint. We built the 'TurboTax for CBAM' — upload your shipment, get your EU-compliant carbon report in 5 minutes. We use AI to also show you how to reduce your tax by switching to greener routes like IMEC Rail."

---

# PART 10: RISK ANALYSIS

## 10.1 Technical Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| API rate limits | Medium | Cache data, use multiple sources |
| LLM hallucinations | High | Strict RAG grounding, show citations |
| Data accuracy issues | Medium | Use only official sources (IPCC, EU) |

## 10.2 Business Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Slow government adoption | High | Start with private sector |
| Competitor emerges | Medium | Move fast, lock in relationships |
| Policy changes | Low | CBAM is long-term EU priority |

## 10.3 Ethical Considerations

- **Data Sensitivity:** Use only public data
- **Accuracy Disclaimer:** AI recommendations are advisory
- **Transparency:** Show all calculation sources

---

# PART 11: ACADEMIC CITATIONS

```
IPCC. (2019). 2019 Refinement to the 2006 IPCC Guidelines for National 
Greenhouse Gas Inventories. https://www.ipcc-nggip.iges.or.jp/public/2019rf/

Smart Freight Centre. (2023). Global Logistics Emissions Council Framework 
v3.0. https://www.smartfreightcentre.org/en/glec-framework/

European Commission. (2023). Regulation (EU) 2023/956 - Carbon Border 
Adjustment Mechanism. https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R0956

IMO. (2020). Fourth IMO GHG Study 2020. 
https://www.imo.org/en/OurWork/Environment/Pages/Fourth-IMO-Greenhouse-Gas-Study-2020.aspx

European Environment Agency. (2024). EU ETS Data Viewer. 
https://www.eea.europa.eu/data-and-maps/dashboards/emissions-trading-viewer-1
```

---

# PART 12: CONCLUSION

**CarbonShip** transforms the existing Digital Twin capstone project into a commercially viable, socially impactful SaaS platform.

**What We Keep:**
- 3D Globe visualization (react-globe.gl)
- GNN risk prediction (PyTorch)
- RL route optimization (Stable-Baselines3)
- RAG chatbot (LangChain)
- FastAPI backend + React frontend

**What We Add:**
- Real emission factors from IPCC/GLEC (FREE)
- CBAM compliance focus (urgent market need)
- Clear business model (SaaS revenue)
- Go-to-market strategy (industry partnerships)

**Total Cost to Build MVP: ₹0** (all data and tools are free)

**Expected Outcome:** A platform that helps Indian exporters save millions in CBAM taxes while reducing global carbon emissions.

---

*Document created: January 16, 2026*
*Next Step: Begin implementation of emission calculator service*
