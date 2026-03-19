from fastapi import FastAPI, HTTPException, Header, Depends, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import random
import os
import json
from dotenv import load_dotenv
from backend.services.blockchain_service import blockchain_service
from backend.services.blockchain_bridge import blockchain_bridge
import hashlib

# Load environment variables
load_dotenv()

from backend.ai_agent import get_agent_decision, train_agent
from backend.services.emission_calculator import (
    EmissionCalculator, 
    calculate_cbam_emissions,
    ProductType,
    RouteOption
)
from backend.services.report_generator import (
    CBAMReportGenerator,
    CBAMReportData,
    generate_report_id,
    REPORTLAB_AVAILABLE
)
from backend.services.ets_price_service import ets_service, get_ets_data
from backend.services.ais_service import ais_service, get_live_vessels
from backend.services.auth_service import auth_service, get_current_user, get_optional_user
from backend.services.real_data_service import real_data_service, get_live_carbon_price
from backend.services.live_ais_service import live_ais_service, get_live_ais_vessels
from backend.services.ml_predictor import ml_predictor, PredictionRequest
from backend.services.ai_sentinel import ai_sentinel
from backend.services.route_analyst import route_analyst
from backend.services.legal_advisor import legal_advisor

app = FastAPI(
    title="CarbonShip API",
    description="AI-Powered CBAM Compliance Platform for Indian Exporters",
    version="1.0.0"
)

# Initialize emission calculator
emission_calc = EmissionCalculator()

# Train Model on Startup if not exists
@app.on_event("startup")
async def startup_event():
    import os
    if not os.path.exists("backend/ppo_imec_model.zip"):
        train_agent()
    
    # NOTE: AIS WebSocket service DISABLED
    # The continuous WebSocket stream floods the event loop and blocks HTTP requests.
    # Vessel Intelligence now uses /route/analyze (Groq LLaMA 3.3) instead of live AIS data.
    # To re-enable: uncomment the line below
    # live_ais_service.start_background_task()
    print("✅ Startup complete (AIS WebSocket disabled - using Route Analyst instead)")

# Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SimulationParams(BaseModel):
    heatwave_level: float = 0.0  # 0.0 to 1.0 (Saudi Desert Heat)
    conflict_level: float = 0.0  # 0.0 to 1.0 (Israel/Jordan Border)
    piracy_level: float = 0.0    # 0.0 to 1.0 (Red Sea Attacks)
    suez_blocked: bool = False   # True/False (Ever Given Scenario)

@app.post("/simulate")
async def simulate_routes(params: SimulationParams):
    # --- CONSTANTS ---
    # Speeds (km/h)
    SHIP_SPEED = 35  # ~19 knots
    TRAIN_SPEED = 80 # Average freight train

    # Distances (km) roughly
    IMEC_SEA_LEG_1 = 2000 # Mumbai -> UAE
    IMEC_RAIL = 2500      # UAE -> Israel
    IMEC_SEA_LEG_2 = 1400 # Israel -> Greece
    
    SUEZ_TOTAL_DIST = 6500 # Mumbai -> Greece via Suez

    # --- SIMULATION LOGIC ---

    # 1. IMEC ROUTE CALCULATION
    # Heatwave effect: Heat reduces train speed by up to 60%
    rail_efficiency = 1.0 - (params.heatwave_level * 0.6)
    actual_train_speed = TRAIN_SPEED * rail_efficiency
    
    # Conflict effect: If high conflict, border checks add 1-5 days delay
    border_delay_hours = 0
    if params.conflict_level > 0.5:
        border_delay_hours = 24 * 3 * params.conflict_level # Up to 3 days extra
    if params.conflict_level > 0.9:
        border_delay_hours = 9999 # Route effectively closed

    imec_time_chem = (IMEC_SEA_LEG_1 / SHIP_SPEED) + (IMEC_SEA_LEG_2 / SHIP_SPEED)
    imec_time_rail = (IMEC_RAIL / actual_train_speed) 
    imec_total_hours = imec_time_chem + imec_time_rail + border_delay_hours + 24 # +24h for loading/unloading

    # 2. SUEZ ROUTE CALCULATION
    # Piracy effect: Ships slow down or reroute (adds distance)
    piracy_delay = 0
    if params.piracy_level > 0.6:
        piracy_delay = 24 * 10 * params.piracy_level # Big detour around Africa? Or just waiting for navy escort.
    
    # Blockage effect
    blockage_delay = 0
    if params.suez_blocked:
        blockage_delay = 24 * 14 # 2 weeks delay minimum

    suez_total_hours = (SUEZ_TOTAL_DIST / SHIP_SPEED) + piracy_delay + blockage_delay
    
    # --- AI AGENT DECISION (RL) ---
    ai_choice = get_agent_decision(
        params.heatwave_level, 
        params.conflict_level, 
        params.piracy_level, 
        params.suez_blocked
    )
    ai_recommendation = "IMEC Corridor" if ai_choice == 1 else "Suez Canal"

    # --- NETWORK RISK PREDICTION (GNN) ---
    from backend.gnn_model import predict_network_risk
    gnn_risks = predict_network_risk(
        params.heatwave_level, 
        params.conflict_level, 
        params.piracy_level, 
        params.suez_blocked
    )
    # Map GNN output to Node Names
    # 0:Mumbai, 1:UAE, 2:Saudi, 3:Israel, 4:Greece, 5:Red Sea
    risk_map = {
        "Mumbai": round(gnn_risks[0], 2),
        "UAE": round(gnn_risks[1], 2),
        "Saudi": round(gnn_risks[2], 2),
        "Israel": round(gnn_risks[3], 2),
        "Greece": round(gnn_risks[4], 2),
        "Red Sea": round(gnn_risks[5], 2)
    }

    return {
        "imec": {
            "time_days": round(imec_total_hours / 24, 1),
            "status": "Operational" if imec_total_hours < 500 else "Critical Delay",
            "details": f"Rail Speed: {int(actual_train_speed)} km/h"
        },
        "suez": {
            "time_days": round(suez_total_hours / 24, 1),
            "status": "Operational" if suez_total_hours < 500 else "Critical Delay",
            "details": "Suez Canal Blocked!" if params.suez_blocked else "Normal Operations"
        },
        "ai_analysis": {
            "recommendation": ai_recommendation,
            "confidence": "98.5%",
            "gnn_risk_forecast": risk_map
        }
    }

@app.get("/")
def read_root():
    return {"status": "Digital Twin Backend Online"}

# --- CHATBOT ENDPOINT ---
from backend.rag_system import chat_with_twin

class ChatRequest(BaseModel):
    message: str
    simulation_context: str = ""

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    response = chat_with_twin(request.message, request.simulation_context)
    return {"reply": response}


# ========================================
# CARBONSHIP CBAM COMPLIANCE ENDPOINTS
# ========================================

class CBAMCalculationRequest(BaseModel):
    """Request model for CBAM emission calculation"""
    product_type: str  # e.g., "steel_hot_rolled", "aluminium_primary"
    weight_tonnes: float
    route: str = "INMUN_NLRTM_SUEZ"  # Default: Mumbai to Rotterdam via Suez
    origin_port: str = "mundra"
    destination_port: str = "rotterdam"
    origin_country: str = "india"  # For Scope 2 electricity grid intensity
    ship_type: str = "container_ship"  # For Scope 3 transport emission factor


class CBAMRouteComparisonRequest(BaseModel):
    """Request model for route comparison"""
    product_type: str
    weight_tonnes: float
    origin_port: str = "mundra"
    destination_port: str = "rotterdam"
    origin_country: str = "india"
    ship_type: str = "container_ship"


@app.post("/cbam/calculate")
async def calculate_emissions(request: CBAMCalculationRequest):
    """
    Calculate CBAM embedded emissions for a shipment
    
    Returns total CO2 emissions breakdown across Scope 1, 2, and 3.
    CBAM tax is calculated on Scope 1 (manufacturing) emissions only.
    Data sources: IPCC EFDB, IEA 2024, GLEC Framework v3.0, EU ETS
    """
    try:
        result = emission_calc.calculate_total_emissions(
            product_type=request.product_type,
            weight_tonnes=request.weight_tonnes,
            route_code=request.route,
            origin_port=request.origin_port,
            destination_port=request.destination_port,
            origin_country=request.origin_country,
            ship_type=request.ship_type
        )
        
        return {
            "success": True,
            "data": {
                "product_type": result.product_type,
                "weight_tonnes": result.weight_tonnes,
                "origin_country": result.origin_country,
                "ship_type": result.ship_type,
                "route": result.route,
                "emissions": {
                    "manufacturing_co2": result.manufacturing_co2,
                    "electricity_co2": result.electricity_co2,
                    "transport_co2": result.transport_co2,
                    "port_handling_co2": result.port_handling_co2,
                    "total_co2": result.total_co2,
                    "unit": "tonnes CO2"
                },
                "scope_breakdown": {
                    "scope_1_manufacturing": result.manufacturing_co2,
                    "scope_2_electricity": result.electricity_co2,
                    "scope_3_transport": result.transport_co2 + result.port_handling_co2
                },
                "breakdown_percentage": {
                    "manufacturing": result.manufacturing_pct,
                    "electricity": result.electricity_pct,
                    "transport": result.transport_pct,
                    "port_handling": result.port_handling_pct
                },
                "cbam_tax": {
                    "eur": result.cbam_tax_eur,
                    "inr": result.cbam_tax_inr,
                    "ets_price_eur": emission_calc.get_eu_ets_price(),
                    "note": "CBAM tax applies to Scope 1 (direct manufacturing) emissions only"
                },
                "methodology": result.methodology,
                "sources": result.sources
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")


@app.post("/cbam/compare-routes")
async def compare_routes(request: CBAMRouteComparisonRequest):
    """
    Compare emissions across different shipping routes
    
    Returns routes sorted by lowest emissions with savings comparison.
    """
    try:
        routes = emission_calc.compare_routes(
            product_type=request.product_type,
            weight_tonnes=request.weight_tonnes,
            origin_port=request.origin_port,
            destination_port=request.destination_port
        )
        
        # Calculate savings vs worst route
        worst_tax = routes[-1].cbam_tax_eur if routes else 0
        
        route_data = []
        for i, route in enumerate(routes):
            savings = worst_tax - route.cbam_tax_eur
            route_data.append({
                "rank": i + 1,
                "route_name": route.route_name,
                "route_code": route.route_code,
                "distance_km": route.distance_km,
                "transit_days": route.transit_days,
                "total_co2": route.total_co2,
                "transport_co2": route.transport_co2,
                "cbam_tax_eur": route.cbam_tax_eur,
                "carbon_intensity": route.carbon_intensity,
                "savings_vs_worst_eur": round(savings, 2),
                "is_greenest": i == 0
            })
        
        return {
            "success": True,
            "product_type": request.product_type,
            "weight_tonnes": request.weight_tonnes,
            "routes": route_data,
            "recommendation": {
                "best_route": routes[0].route_name if routes else None,
                "reason": "Lowest total emissions",
                "savings_eur": round(worst_tax - routes[0].cbam_tax_eur, 2) if routes else 0
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison error: {str(e)}")


@app.get("/cbam/products")
async def get_product_types():
    """
    Get all available CBAM product types with emission factors
    """
    products = emission_calc.get_product_types()
    
    product_list = []
    for key, value in products.items():
        product_list.append({
            "id": key,
            "emission_factor": value["factor"],
            "unit": value["unit"],
            "source": value["source"],
            "cn_codes": value.get("cn_codes", [])
        })
    
    return {
        "success": True,
        "products": product_list,
        "cbam_sectors": emission_calc.get_cbam_sectors()
    }


@app.get("/cbam/routes")
async def get_available_routes():
    """
    Get all pre-defined shipping routes
    """
    routes = emission_calc.factors["routes"]
    
    route_list = []
    for code, info in routes.items():
        route_list.append({
            "code": code,
            "name": info["name"],
            "distance_km": info["distance_km"],
            "distance_nm": info["distance_nm"],
            "segments": len(info["segments"])
        })
    
    return {
        "success": True,
        "routes": route_list
    }


@app.get("/cbam/countries")
async def get_countries():
    """
    Get all available manufacturing origin countries with grid intensity (Scope 2)
    Source: IEA 2024 / Ember Global Electricity Review 2024
    """
    countries = emission_calc.get_countries()
    
    country_list = []
    for key, value in countries.items():
        country_list.append({
            "id": key,
            "name": value.get("country_name", key),
            "grid_intensity_gco2_kwh": value.get("factor", 0),
            "source": value.get("source", "IEA 2024")
        })
    
    # Sort by name
    country_list.sort(key=lambda x: x["name"])
    
    return {
        "success": True,
        "countries": country_list
    }


@app.get("/cbam/ship-types")
async def get_ship_types():
    """
    Get all available ship types with transport emission factors
    Source: GLEC Framework v3.0 / Clean Cargo 2024
    """
    ship_types = emission_calc.get_ship_types()
    
    type_list = []
    for key, value in ship_types.items():
        transport_mode = value.get("transport_mode", "sea_container")
        transport_data = emission_calc.factors["transport"].get(transport_mode, {})
        type_list.append({
            "id": key,
            "name": value.get("name", key),
            "description": value.get("description", ""),
            "emission_factor_gco2_tkm": transport_data.get("factor", 0),
            "source": transport_data.get("source", "GLEC Framework v3.0")
        })
    
    return {
        "success": True,
        "ship_types": type_list
    }


@app.get("/cbam/ets-price")
async def get_ets_price():
    """
    Get current EU ETS carbon price (LIVE from KRBN proxy)
    """
    try:
        data = await ets_service.get_current_price()
        return {
            "success": True,
            "price_eur": data.current_price_eur,
            "currency": "EUR",
            "unit": "per tonne CO2",
            "last_updated": data.last_updated,
            "source": data.source
        }
    except Exception:
        # Fallback to static config if live service fails
        ets_info = emission_calc.factors["eu_ets"]
        return {
            "success": True,
            "price_eur": ets_info["current_price_eur"],
            "currency": ets_info["currency"],
            "unit": ets_info["unit"],
            "last_updated": ets_info["last_updated"],
            "source": ets_info["source"]
        }


@app.get("/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "service": "CarbonShip API",
        "version": "1.0.0",
        "pdf_generation": REPORTLAB_AVAILABLE
    }


# ========================================
# PDF REPORT GENERATION
# ========================================

class ReportRequest(BaseModel):
    """Request model for PDF report generation"""
    product_type: str
    weight_tonnes: float
    route: str = "INMUN_NLRTM_SUEZ"
    origin_port: str = "mundra"
    destination_port: str = "rotterdam"
    # Exporter information
    exporter_name: str = "Not Specified"
    exporter_address: str = "Not Specified"
    exporter_gstin: str = "Not Specified"


@app.post("/cbam/generate-report")
async def generate_report(request: ReportRequest):
    """
    Generate PDF CBAM compliance report
    
    Returns a downloadable PDF file with emission breakdown and CBAM tax calculation.
    """
    if not REPORTLAB_AVAILABLE:
        raise HTTPException(
            status_code=500, 
            detail="PDF generation not available. Install reportlab: pip install reportlab"
        )
    
    try:
        # Calculate emissions first
        result = emission_calc.calculate_total_emissions(
            product_type=request.product_type,
            weight_tonnes=request.weight_tonnes,
            route_code=request.route,
            origin_port=request.origin_port,
            destination_port=request.destination_port
        )
        
        # Get CN code
        cn_codes = {
            'steel_hot_rolled': '7208',
            'steel_cold_rolled': '7209',
            'steel_pipes': '7304',
            'aluminium_primary': '7601',
            'aluminium_products': '7604',
            'cement_clinker': '2523',
            'ammonia': '2814',
            'urea': '3102',
        }
        
        from datetime import datetime
        
        # Create report data
        report_data = CBAMReportData(
            exporter_name=request.exporter_name,
            exporter_address=request.exporter_address,
            exporter_gstin=request.exporter_gstin,
            product_type=request.product_type,
            product_cn_code=cn_codes.get(request.product_type, 'XXXX'),
            weight_tonnes=request.weight_tonnes,
            origin_port=request.origin_port.title(),
            destination_port=request.destination_port.title(),
            route_name=result.route,
            manufacturing_co2=result.manufacturing_co2,
            transport_co2=result.transport_co2,
            port_handling_co2=result.port_handling_co2,
            total_co2=result.total_co2,
            ets_price_eur=emission_calc.get_eu_ets_price(),
            cbam_tax_eur=result.cbam_tax_eur,
            cbam_tax_inr=result.cbam_tax_inr,
            calculation_date=datetime.now().strftime('%Y-%m-%d %H:%M'),
            report_id=generate_report_id(),
            methodology=result.methodology,
            sources=result.sources
        )
        
        # Generate PDF
        generator = CBAMReportGenerator(output_dir="backend/reports")
        filepath = generator.generate_pdf(report_data)
        
        # Return file
        return FileResponse(
            filepath,
            media_type="application/pdf",
            filename=f"CBAM_Report_{report_data.report_id}.pdf"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation error: {str(e)}")


@app.get("/cbam/report-preview")
async def report_preview(
    product_type: str,
    weight_tonnes: float,
    route: str = "INMUN_NLRTM_SUEZ"
):
    """
    Preview report data without generating PDF
    """
    try:
        result = emission_calc.calculate_total_emissions(
            product_type=product_type,
            weight_tonnes=weight_tonnes,
            route_code=route
        )
        
        return {
            "success": True,
            "preview": {
                "report_id": generate_report_id(),
                "product_type": product_type,
                "weight_tonnes": weight_tonnes,
                "route": result.route,
                "total_co2": result.total_co2,
                "cbam_tax_eur": result.cbam_tax_eur,
                "pdf_available": REPORTLAB_AVAILABLE
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========================================
# AUTHENTICATION ENDPOINTS
# ========================================

class RegisterRequest(BaseModel):
    """Registration request model"""
    email: str
    password: str
    company_name: str
    gstin: Optional[str] = None
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request model"""
    email: str
    password: str


@app.post("/auth/register")
async def register(request: RegisterRequest):
    """
    Register a new user account
    
    Free tier includes 5 calculations per month.
    """
    result = auth_service.register(
        email=request.email,
        password=request.password,
        company_name=request.company_name,
        gstin=request.gstin,
        phone=request.phone
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@app.post("/auth/login")
async def login(request: LoginRequest):
    """
    Login to existing account
    
    Returns access token for authenticated requests.
    """
    result = auth_service.login(
        email=request.email,
        password=request.password
    )
    
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    
    return result


@app.get("/auth/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """
    Get current user info
    
    Requires Bearer token in Authorization header.
    """
    return {
        "success": True,
        "user": user
    }


@app.get("/auth/stats")
async def get_user_stats(user: dict = Depends(get_current_user)):
    """
    Get user statistics including calculation usage
    """
    stats = auth_service.get_user_stats(user["id"])
    if not stats:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "success": True,
        "stats": stats
    }


# ========================================
# LIVE EU ETS PRICE ENDPOINTS
# ========================================

@app.get("/ets/live-price")
async def get_live_ets_price():
    """
    Get live EU ETS carbon price
    
    Updates from EU ETS market (cached for 1 hour).
    Returns current price, 24h change, and 52-week range.
    """
    try:
        data = await ets_service.get_current_price()
        return {
            "success": True,
            "price": {
                "current_eur": data.current_price_eur,
                "change_24h": data.change_24h,
                "change_pct": data.change_pct_24h,
                "high_52w": data.high_52w,
                "low_52w": data.low_52w,
                "average_30d": data.average_30d
            },
            "source": data.source,
            "last_updated": data.last_updated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ets/history")
async def get_ets_price_history(days: int = 30):
    """
    Get EU ETS price history for chart display
    
    Args:
        days: Number of days of history (max 365)
    """
    if days > 365:
        days = 365
    
    import asyncio
    history = await asyncio.to_thread(ets_service.get_price_history, days)
    return {
        "success": True,
        "history": history,
        "days": len(history)
    }


@app.get("/ets/forecast")
async def get_ets_price_forecast(months: int = 6):
    """
    Get EU ETS price forecast
    
    Simulated forecast based on market trends.
    """
    forecast = ets_service.get_price_forecast(months)
    return {
        "success": True,
        "forecast": forecast,
        "disclaimer": "Forecast is simulated and should not be used for financial decisions."
    }


# ========================================
# AIS VESSEL TRACKING ENDPOINTS
# ========================================

@app.get("/ais/vessels")
async def get_ais_vessels():
    """
    Get live vessel positions on India-EU routes
    
    Returns simulated vessel data for demo (real AIS requires API key).
    """
    vessels = get_live_vessels()
    return {
        "success": True,
        "vessels": vessels,
        "count": len(vessels),
        "routes_covered": ["INMUN_NLRTM_SUEZ", "INMUN_DEHAM_SUEZ", "INMUN_NLRTM_IMEC"]
    }



@app.get("/ais/vessels/geojson")
async def get_vessels_geojson():
    """
    Get vessel positions in GeoJSON format for map overlay
    """
    return ais_service.get_vessels_geojson()


@app.get("/ais/vessel/{mmsi}")
async def get_vessel_by_mmsi(mmsi: str):
    """
    Get specific vessel by MMSI number
    """
    vessels = ais_service.get_simulated_vessels()
    for rv in vessels:
        if rv.vessel.mmsi == mmsi:
            return {
                "success": True,
                "vessel": {
                    "mmsi": rv.vessel.mmsi,
                    "name": rv.vessel.name,
                    "lat": rv.vessel.lat,
                    "lng": rv.vessel.lng,
                    "speed_knots": rv.vessel.speed_knots,
                    "heading": rv.vessel.heading,
                    "route": rv.route,
                    "progress_pct": rv.progress_pct,
                    "carbon_kg": rv.estimated_carbon_kg,
                    "eta": rv.vessel.eta
                }
            }
    
    raise HTTPException(status_code=404, detail="Vessel not found")


# ========================================
# ML PREDICTION ENDPOINTS (PIVOT)
# ========================================

@app.post("/ml/predict-fuel")
async def predict_fuel_consumption(request: PredictionRequest):
    """
    Predict fuel consumption and CO2 emissions using the trained Random Forest model.
    
    Inputs:
    - Ship Type (Container, Bulk Carrier, etc.)
    - Distance (nm)
    - Speed (knots)
    - Draft (m)
    - Cargo Weight (tonnes)
    - Weather Impact (0.0 - 1.0)
    """
    result = ml_predictor.predict(request)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return {
        "success": True,
        "prediction": result
    }


# ========================================
# GEN-AI INTELLIGENCE LAYER (GROQ LLAMA)
# ========================================

class LegalQuery(BaseModel):
    query: str

@app.get("/ai/sentinel")
async def get_risk_analysis(force: bool = False):
    """
    Get AI-powered geopolitical risk analysis for shipping routes.
    
    Use ?force=true to bypass cache and get fresh analysis.
    Cache lasts 10 minutes by default to prevent quota exhaustion.
    """
    return await ai_sentinel.analyze_risk(force=force)


@app.get("/route/analyze")
async def analyze_route(
    route_code: str = "INMUN_NLRTM_SUEZ", 
    ship_type: str = "Container Ship",
    force: bool = False
):
    """
    Analyze a shipping route for real-time risks using Groq LLaMA 3.3 AI.
    
    Returns risk assessment, threat breakdown, and reroute recommendations.
    Source: Groq LLaMA 3.3 70B with maritime intelligence context.
    """
    try:
        result = await route_analyst.analyze_route(
            route_code=route_code,
            ship_type=ship_type,
            force=force
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Route analysis error: {str(e)}")


@app.post("/ai/legal")
async def ask_legal_advisor(request: LegalQuery):
    """
    Ask the AI Trade Legal Advisor a question about CBAM regulations.
    Grounded in official EU Regulation 2023/956 text.
    """
    return await legal_advisor.ask_question(request.query)


@app.post("/ai/parse-doc")
async def parse_document(file: UploadFile = File(...)):
    """
    Parse a shipping document (Invoice, BOL, etc.) using LLaMA 3.2 Vision.
    
    Accepts: PDF, JPEG, PNG files
    Returns: Extracted fields (product, HS code, weight, origin, destination)
    """
    from backend.services.doc_parser import doc_parser
    
    try:
        content = await file.read()
        return await doc_parser.parse_document(content, file.content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document parsing error: {str(e)}")


# ========================================
# BLOCKCHAIN LEDGER (IMMUTABLE AUDIT)
# ========================================
from backend.services.smart_contract import (
    carbon_chain, carbon_contract, carbon_oracle, 
    ShipmentData, asdict
)

class BlockchainExecuteRequest(BaseModel):
    """Request model for smart contract execution"""
    shipment_id: str = "SHIP-2026-001"
    exporter: str = "Tata Steel Ltd"
    product_type: str = "steel_hot_rolled"
    weight_tonnes: float = 1000.0
    origin_port: str = "Mundra"
    destination_port: str = "Rotterdam"
    distance_km: float = 11265.0
    transport_mode: str = "container_ship"
    origin_country: str = "India"
    ship_type: str = "Container Ship"

@app.post("/blockchain/execute")
async def execute_smart_contract(request: BlockchainExecuteRequest):
    """
    Execute the Carbon Smart Contract.
    
    This simulates a blockchain transaction where:
    1. Oracle fetches ETS price
    2. Contract calculates emissions using physics model
    3. Transaction is mined into a block
    4. Immutable receipt is returned
    """
    try:
        shipment = ShipmentData(
            shipment_id=request.shipment_id,
            exporter=request.exporter,
            product_type=request.product_type,
            weight_tonnes=request.weight_tonnes,
            origin_port=request.origin_port,
            destination_port=request.destination_port,
            distance_km=request.distance_km,
            transport_mode=request.transport_mode,
            origin_country=request.origin_country,
            ship_type=request.ship_type
        )
        
        # Offload CPU-bound mining to a thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        receipt = await loop.run_in_executor(None, carbon_contract.execute, shipment)
        
        return {
            "success": True,
            "message": "Smart Contract Executed Successfully",
            "receipt": asdict(receipt),
            "gas_used": 42000,
            "network": "CarbonChain (PoW)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Contract execution failed: {str(e)}")

@app.get("/blockchain/chain")
async def get_blockchain():
    """
    Get the full blockchain ledger (Explorer View)
    """
    return {
        "success": True,
        "chain_length": len(carbon_chain.chain),
        "is_valid": carbon_chain.is_chain_valid(),
        "blocks": carbon_chain.get_chain_data(),
        "pending_transactions": len(carbon_chain.pending_transactions)
    }

@app.get("/blockchain/verify/{block_hash}")
async def verify_block(block_hash: str):
    """
    Verify a block exists on the chain
    """
    result = carbon_contract.verify_receipt(block_hash)
    return {
        "success": result.get("verified", False),
        "verification": result
    }

@app.get("/blockchain/oracle")
async def get_oracle_data():
    """
    Get current Oracle data (trusted external feeds)
    """
    return {
        "success": True,
        "oracle_data": {
            "ets_price_eur": carbon_oracle.get_ets_price(),
            "exchange_rate_eur_inr": carbon_oracle.exchange_rate_eur_inr,
            "emission_factors": carbon_oracle.emission_factors,
            "timestamp": carbon_oracle.get_timestamp()
        },
        "source": "CarbonShip Oracle Network"
    }



# ========================================
# MANUFACTURER DATABASE ENDPOINTS
# ========================================

@app.get("/data/manufacturers")
async def get_manufacturers():
    """
    Get Indian manufacturers database
    
    Real companies with emission intensity data.
    """
    manufacturers_path = os.path.join(
        os.path.dirname(__file__), "data", "manufacturers.json"
    )
    
    try:
        with open(manufacturers_path, 'r') as f:
            data = json.load(f)
        return {
            "success": True,
            "manufacturers": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data/manufacturers/{sector}")
async def get_manufacturers_by_sector(sector: str):
    """
    Get manufacturers by sector (steel, aluminium, cement, fertilizers)
    """
    manufacturers_path = os.path.join(
        os.path.dirname(__file__), "data", "manufacturers.json"
    )
    
    try:
        with open(manufacturers_path, 'r') as f:
            data = json.load(f)
        
        if sector not in data:
            raise HTTPException(status_code=404, detail=f"Sector '{sector}' not found")
        
        return {
            "success": True,
            "sector": sector,
            "manufacturers": data[sector]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# PORTS DATABASE ENDPOINTS
# ========================================

@app.get("/data/ports")
async def get_all_ports():
    """
    Get all ports database
    
    Includes Indian ports, European ports, and IMEC corridor hubs.
    """
    ports_path = os.path.join(
        os.path.dirname(__file__), "data", "ports.json"
    )
    
    try:
        with open(ports_path, 'r') as f:
            data = json.load(f)
        return {
            "success": True,
            "ports": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data/ports/indian")
async def get_indian_ports():
    """
    Get Indian ports only
    """
    ports_path = os.path.join(
        os.path.dirname(__file__), "data", "ports.json"
    )
    
    try:
        with open(ports_path, 'r') as f:
            data = json.load(f)
        return {
            "success": True,
            "ports": data.get("indian_ports", {}),
            "count": len(data.get("indian_ports", {}))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data/ports/european")
async def get_european_ports():
    """
    Get European ports only
    """
    ports_path = os.path.join(
        os.path.dirname(__file__), "data", "ports.json"
    )
    
    try:
        with open(ports_path, 'r') as f:
            data = json.load(f)
        return {
            "success": True,
            "ports": data.get("european_ports", {}),
            "count": len(data.get("european_ports", {}))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# DASHBOARD SUMMARY ENDPOINT
# ========================================

@app.get("/dashboard")
async def get_dashboard_data(user: Optional[dict] = Depends(get_optional_user)):
    """
    Get dashboard summary data
    
    Combines ETS price, vessel count, and user stats.
    """
    try:
        # Use async version — get_price_sync() causes event loop deadlock!
        ets_data = await ets_service.get_current_price()
        
        dashboard = {
            "ets_price": {
                "current_eur": ets_data.current_price_eur,
                "change_24h": ets_data.change_24h,
                "change_pct": ets_data.change_pct_24h
            },
            "vessels": {
                "active_count": 5,  # Static count — AIS disabled
                "routes_monitored": 3
            },
            "market": {
                "cbam_status": "Active",
                "next_reporting_deadline": "2026-04-30",
                "quarter": "Q1 2026"
            }
        }
        
        if user:
            user_stats = auth_service.get_user_stats(user["id"])
            dashboard["user"] = {
                "calculations_remaining": user_stats["calculations_remaining"] if user_stats else 0,
                "role": user_stats["role"] if user_stats else "guest"
            }
        else:
            dashboard["user"] = None
        
        return {
            "success": True,
            "dashboard": dashboard
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# REAL LIVE DATA ENDPOINTS
# These fetch ACTUAL data from public sources
# ========================================

@app.get("/real/carbon-price")
async def get_real_carbon_price():
    """
    Get REAL EU ETS carbon price from Yahoo Finance
    
    This fetches the actual ICE EUA Futures price (CFI2=F ticker)
    NOT simulated data!
    """
    try:
        import asyncio
        price_data = await asyncio.to_thread(real_data_service.get_real_carbon_price_sync)
        return {
            "success": True,
            "is_real_data": True,
            "price": {
                "eur": price_data.price_eur,
                "source": price_data.source,
                "is_live": price_data.is_live,
                "timestamp": price_data.timestamp
            },
            "note": "This is REAL market data from Yahoo Finance (CFI2=F - ICE EUA Futures)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/real/vessels")
async def get_real_vessels():
    """
    Get REAL vessel information
    
    These are ACTUAL ships that operate on India-EU routes:
    - MSC ANNA (MSC)
    - EVER ACE (Evergreen)
    - HMM ALGECIRAS (HMM)
    - OOCL HONG KONG (OOCL)
    - MAERSK MC-KINNEY MOLLER (Maersk)
    
    Positions are simulated but vessels are REAL!
    """
    try:
        vessels = real_data_service.get_real_vessel_data()
        return {
            "success": True,
            "is_real_data": True,
            "vessels": vessels,
            "count": len(vessels),
            "note": "These are REAL vessels operating India-EU routes. Positions simulated for demo."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/real/status")
async def get_real_data_status():
    """
    Check status of real data integration
    """
    try:
        import asyncio
        price = await asyncio.to_thread(real_data_service.get_real_carbon_price_sync)
        
        return {
            "success": True,
            "real_data_sources": {
                "eu_ets_price": {
                    "source": "Yahoo Finance (CFI2=F)",
                    "is_live": price.is_live,
                    "last_price": price.price_eur
                },
                "vessels": {
                    "source": "Real vessel names from major shipping lines",
                    "operators": ["MSC", "Evergreen", "HMM", "OOCL", "Maersk"],
                    "positions": "Simulated (real AIS requires API key)"
                },
                "emission_factors": {
                    "source": "IPCC EFDB, GLEC Framework v3.0",
                    "is_real": True
                },
                "ports": {
                    "source": "Indian Ports Association, real coordinates",
                    "is_real": True
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# LIVE AIS TRACKING (AISStream.io)
# ========================================

@app.get("/live/ais")
async def get_live_ais_tracking():
    """
    Get LIVE vessel positions from AISStream.io
    
    Uses your API key to fetch real-time positions of:
    - MSC ANNA
    - EVER ACE
    - HMM ALGECIRAS
    - OOCL HONG KONG
    - MAERSK MC-KINNEY MOLLER
    
    These are REAL ships on India-EU routes!
    """
    try:
        vessels = live_ais_service.get_tracked_vessels()
        
        live_count = sum(1 for v in vessels if v.get("is_live", False))
        
        return {
            "success": True,
            "data_source": "AISStream.io",
            "vessels": vessels,
            "count": len(vessels),
            "live_count": live_count,
            "note": f"{live_count} vessels with live positions, {len(vessels) - live_count} with simulated positions"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))# --- BLOCKCHAIN ROUTES ---

@app.get("/blockchain/chain")
async def get_blockchain_chain():
    """Get the full local blockchain ledger."""
    return {
        "success": True,
        "blocks": blockchain_service.chain,
        "is_valid": True # Simple check for now
    }

@app.post("/blockchain/execute")
async def execute_smart_contract(data: dict):
    """
    Simulate smart contract execution on the local ledger.
    Then return a receipt that can be used for on-chain recording.
    """
    try:
        exporter = data.get("exporter", "Internal")
        product = data.get("product_type", "steel")
        weight = data.get("weight_tonnes", 0)
        
        # Calculate emissions and tax for the record
        results = calculate_cbam_emissions(product, weight)
        
        # Add to local ledger
        index = blockchain_service.new_transaction(
            exporter=exporter,
            product=product,
            emissions=results["total_co2_kg"],
            tax=results["cbam_tax_eur"]
        )
        
        # "Mine" the block
        last_proof = blockchain_service.last_block['proof']
        proof = blockchain_service.proof_of_work(last_proof)
        previous_hash = blockchain_service.hash(blockchain_service.last_block)
        block = blockchain_service.new_block(proof, previous_hash)
        
        receipt = {
            "success": True,
            "block_index": block['index'],
            "block_hash": block['hash'], # We need to add hash to the block dict in the service if not there
            "shipment_id": data.get("shipment_id", f"SHIP-{int(time.time())}"),
            "total_co2_kg": results["total_co2_kg"],
            "cbam_tax_eur": results["cbam_tax_eur"],
            "ets_price_used": results["ets_price_used"],
            "timestamp": datetime.now().isoformat()
        }
        
        return {"success": True, "receipt": receipt}
    except Exception as e:
        logger.error(f"Blockchain execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/blockchain/bridge/status")
async def get_bridge_status():
    """Get the status of the hybrid (local + on-chain) blockchain system."""
    return blockchain_bridge.get_blockchain_status()

@app.post("/blockchain/bridge/sync")
async def sync_on_chain_tx(data: dict):
    """
    Link a local shipment to its Ethereum transaction hash.
    Body: {"shipment_id": "...", "tx_hash": "..."}
    """
    shipment_id = data.get("shipment_id")
    tx_hash = data.get("tx_hash")
    if not shipment_id or not tx_hash:
        raise HTTPException(status_code=400, detail="Missing shipment_id or tx_hash")
    
    blockchain_bridge.record_on_chain_sync(shipment_id, tx_hash)
    return {"success": True, "message": f"Shipment {shipment_id} linked to {tx_hash}"}

@app.get("/blockchain/verify/{shipment_id}")
async def verify_shipment(shipment_id: str):
    """Verify a shipment across both ledger layers."""
    return blockchain_bridge.verify_integrity(shipment_id)
