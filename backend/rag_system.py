"""
CarbonShip RAG Chatbot - CBAM Compliance Advisor
Provides answers about EU CBAM regulations, carbon calculations, and compliance

NOTE: Simplified version without langchain dependencies for easier deployment.
Can be upgraded to full RAG with FAISS + LLM later.
"""

import os
from typing import Optional

# CBAM KNOWLEDGE BASE
CBAM_CONTEXT = """
## EU Carbon Border Adjustment Mechanism (CBAM)

### Overview
CBAM is the EU's carbon tariff on imports of carbon-intensive goods. It aims to prevent "carbon leakage" - 
where companies relocate production to countries with weaker climate policies.

### Key Dates
- October 2023: Transitional phase begins (reporting only)
- January 2026: Full implementation (financial obligations)
- 2027-2034: Gradual phase-in matching EU ETS free allocation phase-out

### Covered Products (CN Codes)
1. **Iron & Steel** (Chapter 72-73): Hot-rolled, cold-rolled, pipes, wire
2. **Aluminium** (Chapter 76): Primary, secondary, products
3. **Cement** (2523): Clinker, Portland cement
4. **Fertilizers** (Chapter 28, 31): Ammonia, urea, nitric acid
5. **Hydrogen** (2804): Grey, blue, green hydrogen
6. **Electricity** (2716): Electric power imports

### Embedded Emissions
CBAM covers:
- **Direct emissions**: From manufacturing process
- **Indirect emissions**: From electricity used (for some products)
- **Transport emissions**: Currently NOT included in CBAM scope

### Calculation Method
1. Determine product CN code
2. Apply default emission factor OR use actual verified data
3. Multiply by EU ETS carbon price (~€85/tonne CO2)
4. Purchase CBAM certificates

### Verification Requirements
- From 2026: Emissions must be verified by EU-accredited verifiers
- India has NO accredited verifiers yet - major challenge for exporters
- FICCI and CII are training verification bodies

### Key Emission Factors (IPCC Default Values)
- Hot-rolled steel: 1.85 tCO2/tonne
- Primary aluminium: 14.5 tCO2/tonne
- Cement clinker: 0.85 tCO2/tonne
- Ammonia: 1.80 tCO2/tonne

### Impact on India
- $12 billion in CBAM-affected exports annually
- Steel exports already declined 24.4% in FY 2024-25
- SMEs most affected due to lack of carbon accounting systems
"""

ROUTE_CONTEXT = """
## Shipping Routes: India to EU

### Route 1: Suez Canal
- Distance: Mumbai → Rotterdam = 11,735 km (6,337 nm)
- Transit time: 18-21 days
- Transport emissions: ~16 gCO2/tonne-km
- Risks: Red Sea piracy, Suez blockage, Yemen conflict

### Route 2: IMEC Corridor (Planned)
- Distance: Mumbai → Rotterdam = 10,742 km
- Transit time: 14-16 days (40% faster)
- Transport emissions: Lower due to rail component (~23 gCO2/tonne-km for electric rail)
- Status: Under development

### Route 3: Cape of Good Hope
- Distance: Mumbai → Rotterdam = 19,910 km
- Transit time: 28-35 days
- Transport emissions: Highest due to distance
- Use case: When Suez is blocked or high-risk
"""


class CBAMChatbot:
    """
    Rule-based CBAM compliance chatbot
    Can be upgraded to full RAG with LLM integration
    """
    
    def __init__(self):
        self.context = CBAM_CONTEXT + "\n\n" + ROUTE_CONTEXT
        print("CarbonShip CBAM Advisor initialized (Rule-based mode)")
    
    def query(self, user_input: str, simulation_context: Optional[str] = None) -> str:
        """
        Answer user questions about CBAM compliance
        
        Args:
            user_input: User's question
            simulation_context: Current calculation context
            
        Returns:
            Answer string
        """
        user_input = user_input.lower().strip()
        
        # CBAM-specific queries
        if "what is cbam" in user_input or "cbam mean" in user_input:
            return """**CBAM (Carbon Border Adjustment Mechanism)** is the EU's carbon tariff on imports.

🎯 **Purpose**: Prevent "carbon leakage" by ensuring imported goods pay the same carbon price as EU-produced goods.

📅 **Key Dates**:
- January 2026: Full implementation begins
- Quarterly reporting required
- Financial obligations start

📦 **Covered Products**: Steel, Aluminium, Cement, Fertilizers, Hydrogen, Electricity

💰 **Current Price**: ~€85 per tonne CO2"""

        elif "deadline" in user_input or "due date" in user_input or "when" in user_input:
            return """📅 **CBAM Deadlines**:

• **January 1, 2026**: Full CBAM starts - financial obligations begin
• **Quarterly Reports**: Due 30 days after each quarter ends
  - Q1 (Jan-Mar): Due April 30
  - Q2 (Apr-Jun): Due July 31
  - Q3 (Jul-Sep): Due October 31
  - Q4 (Oct-Dec): Due January 31
• **Verification**: Required for all emissions data from 2026"""

        elif "steel" in user_input:
            return """🔩 **Steel under CBAM**:

**Emission Factors** (IPCC defaults):
- Hot-rolled steel: **1.85 tCO2/tonne**
- Cold-rolled steel: **2.10 tCO2/tonne**
- Steel pipes: **1.95 tCO2/tonne**
- Steel wire: **1.90 tCO2/tonne**

**CN Codes**: 7208-7212, 7217, 7223, 7304-7306

**Example**: 100 tonnes hot-rolled steel = 185 tCO2 = **€15,725 CBAM tax**"""

        elif "aluminium" in user_input or "aluminum" in user_input:
            return """🪶 **Aluminium under CBAM**:

**Emission Factors** (IPCC defaults):
- Primary aluminium: **14.5 tCO2/tonne** (very high!)
- Secondary (recycled): **0.5 tCO2/tonne**
- Mixed products: ~**8.0 tCO2/tonne**

**CN Codes**: 7601-7607

**Example**: 100 tonnes primary aluminium = 1,450 tCO2 = **€123,250 CBAM tax** 
⚠️ This is why aluminium exporters are most impacted!"""

        elif "cement" in user_input:
            return """🏗️ **Cement under CBAM**:

**Emission Factors** (IPCC defaults):
- Cement clinker: **0.85 tCO2/tonne**
- Portland cement: **0.65 tCO2/tonne** (blended)

**CN Code**: 2523

**Example**: 100 tonnes clinker = 85 tCO2 = **€7,225 CBAM tax**"""

        elif "fertilizer" in user_input or "ammonia" in user_input or "urea" in user_input:
            return """🌾 **Fertilizers under CBAM**:

**Emission Factors** (IPCC defaults):
- Ammonia: **1.80 tCO2/tonne**
- Urea: **0.73 tCO2/tonne**
- Nitric acid: **2.50 tCO2/tonne**

**CN Codes**: 2808, 2814, 3102

**Example**: 100 tonnes ammonia = 180 tCO2 = **€15,300 CBAM tax**"""

        elif "price" in user_input or "ets" in user_input or "carbon price" in user_input:
            return """💶 **EU ETS Carbon Price**:

Current price: **€85/tonne CO2** (January 2026)

**Historical Range**: €50-100 over past 2 years

**CBAM uses EU ETS price** to calculate tax on imports.

**Forecast**: Expected to rise to €100-120 by 2030 as free allocations phase out."""

        elif "calculate" in user_input or "how to" in user_input:
            return """🧮 **How to Calculate CBAM Tax**:

**Formula**:
`CBAM Tax = (Embedded CO2 × EU ETS Price) - Carbon Tax Paid in Origin Country`

**Steps**:
1. **Identify product** CN code
2. **Get emission factor** (use IPCC default or actual verified data)
3. **Multiply** by weight in tonnes
4. **Add transport emissions** (optional)
5. **Multiply** by EU ETS price (€85/tonne)
6. **Subtract** any carbon tax already paid in India

**Example**: 
100 tonnes steel × 1.85 tCO2/t × €85 = **€15,725**"""

        elif "verify" in user_input or "audit" in user_input or "verification" in user_input:
            return """✅ **CBAM Verification Requirements**:

From 2026, all emissions data must be verified by **EU-accredited verifiers**.

**Challenge for India**:
- NO EU-accredited verifiers in India yet
- Must use international verification bodies (expensive)
- FICCI and CII are training Indian verifiers

**Documents Needed**:
1. Production process description
2. Energy consumption data
3. Raw material sources
4. Electricity mix certificates
5. Previous audit reports"""

        elif "route" in user_input or "suez" in user_input or "imec" in user_input:
            return """🚢 **Shipping Routes Comparison**:

**1. Suez Canal** (Traditional):
- Distance: 11,735 km
- Time: 18 days
- Transport CO2: ~18.8 tCO2 per 100 tonnes

**2. IMEC Corridor** (New):
- Distance: 10,742 km
- Time: 14 days (faster!)
- Transport CO2: ~20.8 tCO2 (rail has higher emissions)

**3. Cape of Good Hope**:
- Distance: 19,910 km
- Time: 28 days
- Transport CO2: ~31.9 tCO2 (longest)

⚡ **Note**: Transport emissions are NOT currently in CBAM scope, but may be added later."""

        elif "india" in user_input or "impact" in user_input or "exporter" in user_input:
            return """🇮🇳 **CBAM Impact on India**:

**Affected Exports**: $12+ billion annually
- Steel: $8.2 billion
- Aluminium: $2.1 billion
- Fertilizers: $1.8 billion
- Cement: $150 million

**Already Happening**:
- Steel exports to EU down **24.4%** in FY 2024-25
- 100% of SMEs lack carbon calculation tools
- EU buyers demanding carbon data from suppliers

**What to Do**:
1. Start calculating emissions NOW
2. Get verification-ready documentation
3. Consider greener production methods
4. Use CarbonShip to prepare compliance reports"""

        elif "help" in user_input or "can you" in user_input:
            return """👋 **I'm your CBAM Compliance Advisor!**

I can help you with:

📊 **Calculations**: Steel, aluminium, cement, fertilizer emissions
📅 **Deadlines**: When reports are due
💶 **Pricing**: Current EU ETS carbon prices
✅ **Verification**: What documents you need
🚢 **Routes**: Compare Suez vs IMEC shipping options
🇮🇳 **India Impact**: How CBAM affects Indian exporters

**Try asking**:
- "What is CBAM?"
- "Calculate steel emissions"
- "When is the deadline?"
- "Compare shipping routes"
"""

        # Default response
        return """🌿 **CarbonShip CBAM Advisor**

I can answer questions about:
- CBAM regulations and deadlines
- Emission factors for steel, aluminium, cement, fertilizers
- EU ETS carbon prices
- Verification requirements
- Shipping route comparisons

**Try asking**: "What is CBAM?" or "How do I calculate steel emissions?"
"""


# Singleton instance
chatbot = CBAMChatbot()


def chat_with_twin(message: str, sim_data: str = "") -> str:
    """
    Main chat function called by the API
    
    Args:
        message: User's message
        sim_data: Current simulation context
        
    Returns:
        Chatbot response
    """
    return chatbot.query(message, sim_data)


if __name__ == "__main__":
    # Test the chatbot
    print("=" * 50)
    print("CBAM CHATBOT TEST")
    print("=" * 50)
    
    test_questions = [
        "What is CBAM?",
        "How do I calculate steel emissions?",
        "What is the current carbon price?",
        "Compare shipping routes",
    ]
    
    for q in test_questions:
        print(f"\n❓ {q}")
        print(f"💬 {chat_with_twin(q)[:200]}...")
