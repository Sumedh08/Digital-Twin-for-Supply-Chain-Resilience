"""
CarbonShip Emission Calculator Service
Calculates embedded carbon emissions for CBAM compliance

Data Sources:
- Manufacturing: IPCC Emission Factor Database (https://www.ipcc-nggip.iges.or.jp/EFDB/)
- Transport: GLEC Framework v3.0 (https://www.smartfreightcentre.org/en/glec-framework/)
- EU ETS Price: European Environment Agency
"""

import json
import os
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

# Load emission factors
EMISSION_FACTORS_PATH = os.path.join(
    os.path.dirname(__file__), 
    "..", 
    "data", 
    "emission_factors.json"
)

with open(EMISSION_FACTORS_PATH, "r") as f:
    EMISSION_FACTORS = json.load(f)


class ProductType(str, Enum):
    """CBAM product categories"""
    STEEL_HOT_ROLLED = "steel_hot_rolled"
    STEEL_COLD_ROLLED = "steel_cold_rolled"
    STEEL_PIPES = "steel_pipes"
    STEEL_WIRE = "steel_wire"
    ALUMINIUM_PRIMARY = "aluminium_primary"
    ALUMINIUM_SECONDARY = "aluminium_secondary"
    ALUMINIUM_PRODUCTS = "aluminium_products"
    CEMENT_CLINKER = "cement_clinker"
    CEMENT_PORTLAND = "cement_portland"
    AMMONIA = "ammonia"
    UREA = "urea"
    NITRIC_ACID = "nitric_acid"
    HYDROGEN_GREY = "hydrogen_grey"
    HYDROGEN_BLUE = "hydrogen_blue"


class TransportMode(str, Enum):
    """Transport modes with emission factors"""
    SEA_CONTAINER = "sea_container"
    SEA_BULK = "sea_bulk"
    SEA_TANKER = "sea_tanker"
    RAIL_ELECTRIC = "rail_electric"
    RAIL_DIESEL = "rail_diesel"
    ROAD_TRUCK = "road_truck"
    ROAD_TRUCK_INDIA = "road_truck_india"
    AIR_FREIGHT = "air_freight"


class RouteOption(str, Enum):
    """Pre-defined shipping routes"""
    MUMBAI_ROTTERDAM_SUEZ = "INMUN_NLRTM_SUEZ"
    MUMBAI_ROTTERDAM_IMEC = "INMUN_NLRTM_IMEC"
    MUMBAI_ROTTERDAM_CAPE = "INMUN_NLRTM_CAPE"
    MUMBAI_HAMBURG_SUEZ = "INMUN_DEHAM_SUEZ"
    CHENNAI_ROTTERDAM_SUEZ = "INMAA_NLRTM_SUEZ"


@dataclass
class EmissionBreakdown:
    """Detailed emission breakdown with Scope 1/2/3"""
    manufacturing_co2: float  # Scope 1: Direct manufacturing emissions (tonnes CO2)
    electricity_co2: float    # Scope 2: Indirect electricity emissions (tonnes CO2)
    transport_co2: float      # Scope 3: Transport emissions (tonnes CO2)
    port_handling_co2: float  # Scope 3: Port handling emissions (tonnes CO2)
    total_co2: float          # Total all scopes (tonnes CO2)
    cbam_tax_eur: float       # CBAM tax based on Scope 1 only (EUR)
    cbam_tax_inr: float       # INR (approximate)
    
    # Percentages
    manufacturing_pct: float
    electricity_pct: float
    transport_pct: float
    port_handling_pct: float
    
    # Metadata
    product_type: str
    weight_tonnes: float
    origin_country: str
    ship_type: str
    route: str
    methodology: str
    sources: List[str]


@dataclass
class RouteComparison:
    """Compare emissions across different routes"""
    route_name: str
    route_code: str
    total_co2: float
    transport_co2: float
    cbam_tax_eur: float
    transit_days: int
    distance_km: int
    carbon_intensity: float  # gCO2 per tonne-km


class EmissionCalculator:
    """
    Main calculator for CBAM embedded emissions
    """
    
    EUR_TO_INR = 90.0  # Approximate exchange rate
    
    def __init__(self):
        self.factors = EMISSION_FACTORS
    
    def get_manufacturing_factor(self, product_type: str) -> float:
        """Get manufacturing emission factor (tCO2/tonne)"""
        if product_type in self.factors["manufacturing"]:
            return self.factors["manufacturing"][product_type]["factor"]
        raise ValueError(f"Unknown product type: {product_type}")
    
    def get_transport_factor(self, mode: str) -> float:
        """Get transport emission factor (gCO2/tonne-km)"""
        if mode in self.factors["transport"]:
            return self.factors["transport"][mode]["factor"]
        raise ValueError(f"Unknown transport mode: {mode}")
    
    def get_electricity_grid_factor(self, country: str) -> float:
        """Get grid carbon intensity for a country (gCO2/kWh)"""
        country = country.lower()
        if country in self.factors.get("electricity", {}):
            if country == "_metadata":
                return 632  # Default to India
            return self.factors["electricity"][country]["factor"]
        return 632  # Default to India if unknown
    
    def get_electricity_per_tonne(self, product_type: str) -> float:
        """Get electricity consumption per tonne of product (MWh/tonne)"""
        return self.factors.get("electricity_per_tonne", {}).get(product_type, 0.5)
    
    def get_transport_mode_for_ship(self, ship_type: str) -> str:
        """Map ship type to transport mode for emission factor lookup"""
        ship_data = self.factors.get("ship_types", {}).get(ship_type)
        if ship_data:
            return ship_data["transport_mode"]
        return "sea_container"  # Default
    
    def get_port_handling_factor(self, port_code: str) -> float:
        """Get port handling emission factor (tCO2/tonne)"""
        port_code = port_code.lower()
        if port_code in self.factors["port_handling"]:
            return self.factors["port_handling"][port_code]["factor"]
        return self.factors["port_handling"]["default"]["factor"]
    
    def get_eu_ets_price(self) -> float:
        """Get current EU ETS carbon price (EUR/tonne CO2) - NON-BLOCKING"""
        try:
            from backend.services.ets_price_service import get_ets_price
            return get_ets_price()  # Returns cached price, never blocks
        except Exception:
            return self.factors.get("eu_ets", {}).get("current_price_eur", 68.35)
    
    def calculate_manufacturing_emissions(
        self, 
        product_type: str, 
        weight_tonnes: float
    ) -> float:
        """
        Calculate Scope 1 manufacturing emissions
        
        Args:
            product_type: Type of product (e.g., "steel_hot_rolled")
            weight_tonnes: Weight of goods in metric tonnes
            
        Returns:
            CO2 emissions in tonnes
        """
        factor = self.get_manufacturing_factor(product_type)
        return factor * weight_tonnes
    
    def calculate_electricity_emissions(
        self,
        product_type: str,
        weight_tonnes: float,
        origin_country: str = "india"
    ) -> float:
        """
        Calculate Scope 2 electricity emissions
        
        Formula: Weight * Electricity_per_tonne * Grid_Intensity
        
        Args:
            product_type: Type of product
            weight_tonnes: Weight of goods in metric tonnes
            origin_country: Country where manufacturing occurs
            
        Returns:
            CO2 emissions in tonnes
        """
        # MWh electricity consumed per tonne of product
        elec_per_tonne = self.get_electricity_per_tonne(product_type)
        # Grid carbon intensity in gCO2/kWh
        grid_intensity = self.get_electricity_grid_factor(origin_country)
        
        # Total: weight * MWh/tonne * 1000 kWh/MWh * gCO2/kWh / 1_000_000 g/tonne
        total_co2_tonnes = weight_tonnes * elec_per_tonne * grid_intensity / 1000
        return total_co2_tonnes
    
    def calculate_transport_emissions(
        self,
        weight_tonnes: float,
        route_code: Optional[str] = None,
        custom_segments: Optional[List[Dict]] = None,
        ship_type: Optional[str] = None
    ) -> float:
        """
        Calculate Scope 3 transport emissions
        
        Args:
            weight_tonnes: Weight of goods in metric tonnes
            route_code: Pre-defined route code (e.g., "INMUN_NLRTM_SUEZ")
            custom_segments: Custom route segments [{"mode": "sea_container", "distance_km": 5000}, ...]
            ship_type: Ship type to override the default transport mode (e.g., "bulk_carrier")
            
        Returns:
            CO2 emissions in tonnes
        """
        if route_code:
            if route_code not in self.factors["routes"]:
                raise ValueError(f"Unknown route: {route_code}")
            segments = self.factors["routes"][route_code]["segments"]
        elif custom_segments:
            segments = custom_segments
        else:
            raise ValueError("Must provide either route_code or custom_segments")
        
        # If ship_type is provided, override the sea transport mode in segments
        override_mode = None
        if ship_type:
            override_mode = self.get_transport_mode_for_ship(ship_type)
        
        total_co2_grams = 0
        for segment in segments:
            mode = segment["mode"]
            # Override sea segments with the selected ship type
            if override_mode and mode.startswith("sea_"):
                mode = override_mode
            distance_km = segment["distance_km"]
            factor = self.get_transport_factor(mode)
            # factor is gCO2/tonne-km
            segment_co2 = factor * weight_tonnes * distance_km
            total_co2_grams += segment_co2
        
        # Convert grams to tonnes
        return total_co2_grams / 1_000_000
    
    def calculate_port_handling_emissions(
        self,
        weight_tonnes: float,
        origin_port: str = "default",
        destination_port: str = "default"
    ) -> float:
        """
        Calculate port handling emissions
        
        Args:
            weight_tonnes: Weight of goods in metric tonnes
            origin_port: Origin port code (e.g., "mundra", "jnpt")
            destination_port: Destination port code (e.g., "rotterdam", "hamburg")
            
        Returns:
            CO2 emissions in tonnes
        """
        origin_factor = self.get_port_handling_factor(origin_port)
        dest_factor = self.get_port_handling_factor(destination_port)
        
        return (origin_factor + dest_factor) * weight_tonnes
    
    def calculate_total_emissions(
        self,
        product_type: str,
        weight_tonnes: float,
        route_code: str,
        origin_port: str = "default",
        destination_port: str = "default",
        origin_country: str = "india",
        ship_type: str = "container_ship"
    ) -> EmissionBreakdown:
        """
        Calculate total embedded emissions across Scope 1, 2, and 3
        
        Args:
            product_type: Type of product
            weight_tonnes: Weight in tonnes
            route_code: Shipping route code
            origin_port: Origin port
            destination_port: Destination port
            origin_country: Country of manufacture (for Scope 2 grid intensity)
            ship_type: Type of ship (for transport emission factor)
            
        Returns:
            EmissionBreakdown with full details
        """
        # Scope 1: Manufacturing direct emissions
        manufacturing_co2 = self.calculate_manufacturing_emissions(
            product_type, weight_tonnes
        )
        
        # Scope 2: Electricity indirect emissions
        electricity_co2 = self.calculate_electricity_emissions(
            product_type, weight_tonnes, origin_country
        )
        
        # Scope 3: Transport emissions (using ship type)
        transport_co2 = self.calculate_transport_emissions(
            weight_tonnes, route_code, ship_type=ship_type
        )
        
        # Scope 3: Port handling emissions
        port_handling_co2 = self.calculate_port_handling_emissions(
            weight_tonnes, origin_port, destination_port
        )
        
        total_co2 = manufacturing_co2 + electricity_co2 + transport_co2 + port_handling_co2
        
        # CBAM Tax: Currently based on Scope 1 (manufacturing direct emissions) only
        ets_price = self.get_eu_ets_price()
        cbam_tax_eur = manufacturing_co2 * ets_price
        cbam_tax_inr = cbam_tax_eur * self.EUR_TO_INR
        
        # Calculate percentages
        mfg_pct = (manufacturing_co2 / total_co2 * 100) if total_co2 > 0 else 0
        elec_pct = (electricity_co2 / total_co2 * 100) if total_co2 > 0 else 0
        trans_pct = (transport_co2 / total_co2 * 100) if total_co2 > 0 else 0
        port_pct = (port_handling_co2 / total_co2 * 100) if total_co2 > 0 else 0
        
        # Get route name
        route_name = self.factors["routes"].get(route_code, {}).get("name", route_code)
        
        # Get ship type name
        ship_name = self.factors.get("ship_types", {}).get(ship_type, {}).get("name", ship_type)
        
        # Get country name
        country_data = self.factors.get("electricity", {}).get(origin_country.lower(), {})
        country_name = country_data.get("country_name", origin_country) if isinstance(country_data, dict) else origin_country
        
        return EmissionBreakdown(
            manufacturing_co2=round(manufacturing_co2, 3),
            electricity_co2=round(electricity_co2, 3),
            transport_co2=round(transport_co2, 3),
            port_handling_co2=round(port_handling_co2, 3),
            total_co2=round(total_co2, 3),
            cbam_tax_eur=round(cbam_tax_eur, 2),
            cbam_tax_inr=round(cbam_tax_inr, 2),
            manufacturing_pct=round(mfg_pct, 1),
            electricity_pct=round(elec_pct, 1),
            transport_pct=round(trans_pct, 1),
            port_handling_pct=round(port_pct, 1),
            product_type=product_type,
            weight_tonnes=weight_tonnes,
            origin_country=country_name,
            ship_type=ship_name,
            route=route_name,
            methodology="CBAM Default Values (Scope 1) + IEA Grid Intensity (Scope 2) + GLEC Framework v3.0 (Scope 3)",
            sources=[
                "IPCC Emission Factor Database (Scope 1)",
                "IEA Emission Factors 2024 / Ember (Scope 2)",
                "GLEC Framework v3.0 / Clean Cargo 2024 (Scope 3)",
                "European Environment Agency EU ETS"
            ]
        )
    
    def compare_routes(
        self,
        product_type: str,
        weight_tonnes: float,
        origin_port: str = "mundra",
        destination_port: str = "rotterdam"
    ) -> List[RouteComparison]:
        """
        Compare emissions across different shipping routes
        
        Args:
            product_type: Type of product
            weight_tonnes: Weight in tonnes
            origin_port: Origin port
            destination_port: Destination port
            
        Returns:
            List of RouteComparison objects sorted by lowest emissions
        """
        # Routes to compare (Mumbai to Rotterdam variants)
        routes_to_compare = [
            ("INMUN_NLRTM_SUEZ", 18),   # Suez: ~18 days
            ("INMUN_NLRTM_IMEC", 14),   # IMEC: ~14 days
            ("INMUN_NLRTM_CAPE", 28),   # Cape: ~28 days
        ]
        
        results = []
        ets_price = self.get_eu_ets_price()
        
        for route_code, transit_days in routes_to_compare:
            route_info = self.factors["routes"].get(route_code)
            if not route_info:
                continue
            
            transport_co2 = self.calculate_transport_emissions(
                weight_tonnes, route_code
            )
            
            # Add manufacturing (same for all routes)
            manufacturing_co2 = self.calculate_manufacturing_emissions(
                product_type, weight_tonnes
            )
            
            # Add port handling
            port_co2 = self.calculate_port_handling_emissions(
                weight_tonnes, origin_port, destination_port
            )
            
            total_co2 = manufacturing_co2 + transport_co2 + port_co2
            distance_km = route_info["distance_km"]
            
            results.append(RouteComparison(
                route_name=route_info["name"],
                route_code=route_code,
                total_co2=round(total_co2, 3),
                transport_co2=round(transport_co2, 3),
                cbam_tax_eur=round(total_co2 * ets_price, 2),
                transit_days=transit_days,
                distance_km=distance_km,
                carbon_intensity=round((transport_co2 * 1_000_000) / (weight_tonnes * distance_km), 2)
            ))
        
        # Sort by lowest emissions
        results.sort(key=lambda x: x.total_co2)
        
        return results
    
    def get_product_types(self) -> Dict[str, Dict]:
        """Get all available product types with their CN codes"""
        return self.factors["manufacturing"]
    
    def get_cbam_sectors(self) -> Dict[str, Dict]:
        """Get CBAM sector definitions"""
        return self.factors["cbam_sectors"]
    
    def get_countries(self) -> Dict[str, Dict]:
        """Get available manufacturing origin countries with grid intensity"""
        countries = {}
        for key, val in self.factors.get("electricity", {}).items():
            if key == "_metadata":
                continue
            countries[key] = val
        return countries
    
    def get_ship_types(self) -> Dict[str, Dict]:
        """Get available ship types"""
        return self.factors.get("ship_types", {})


# Convenience function for quick calculations
def calculate_cbam_emissions(
    product_type: str,
    weight_tonnes: float,
    route: str = "INMUN_NLRTM_SUEZ"
) -> dict:
    """
    Quick function to calculate CBAM emissions
    
    Example:
        result = calculate_cbam_emissions("steel_hot_rolled", 100, "INMUN_NLRTM_SUEZ")
        print(f"Total CO2: {result['total_co2']} tonnes")
        print(f"CBAM Tax: €{result['cbam_tax_eur']}")
    """
    calc = EmissionCalculator()
    breakdown = calc.calculate_total_emissions(
        product_type=product_type,
        weight_tonnes=weight_tonnes,
        route_code=route
    )
    
    return {
        "product_type": breakdown.product_type,
        "weight_tonnes": breakdown.weight_tonnes,
        "route": breakdown.route,
        "manufacturing_co2": breakdown.manufacturing_co2,
        "transport_co2": breakdown.transport_co2,
        "port_handling_co2": breakdown.port_handling_co2,
        "total_co2": breakdown.total_co2,
        "cbam_tax_eur": breakdown.cbam_tax_eur,
        "cbam_tax_inr": breakdown.cbam_tax_inr,
        "breakdown_pct": {
            "manufacturing": breakdown.manufacturing_pct,
            "transport": breakdown.transport_pct,
            "port_handling": breakdown.port_handling_pct
        },
        "methodology": breakdown.methodology,
        "sources": breakdown.sources
    }


if __name__ == "__main__":
    # Demo calculation
    print("=" * 60)
    print("CARBONSHIP EMISSION CALCULATOR DEMO")
    print("=" * 60)
    
    calc = EmissionCalculator()
    
    # Example: 100 tonnes of hot-rolled steel from Mumbai to Rotterdam
    result = calc.calculate_total_emissions(
        product_type="steel_hot_rolled",
        weight_tonnes=100,
        route_code="INMUN_NLRTM_SUEZ",
        origin_port="mundra",
        destination_port="rotterdam"
    )
    
    print(f"\nProduct: {result.product_type}")
    print(f"Weight: {result.weight_tonnes} tonnes")
    print(f"Route: {result.route}")
    print(f"\n--- EMISSION BREAKDOWN ---")
    print(f"Manufacturing: {result.manufacturing_co2} tCO2 ({result.manufacturing_pct}%)")
    print(f"Transport: {result.transport_co2} tCO2 ({result.transport_pct}%)")
    print(f"Port Handling: {result.port_handling_co2} tCO2 ({result.port_handling_pct}%)")
    print(f"\nTOTAL: {result.total_co2} tCO2")
    print(f"\n--- CBAM TAX ---")
    print(f"EU ETS Price: €{calc.get_eu_ets_price()}/tonne")
    print(f"CBAM Tax: €{result.cbam_tax_eur}")
    print(f"CBAM Tax: ₹{result.cbam_tax_inr}")
    
    print("\n" + "=" * 60)
    print("ROUTE COMPARISON")
    print("=" * 60)
    
    routes = calc.compare_routes(
        product_type="steel_hot_rolled",
        weight_tonnes=100
    )
    
    for i, route in enumerate(routes, 1):
        savings = routes[-1].cbam_tax_eur - route.cbam_tax_eur if i == 1 else 0
        print(f"\n{i}. {route.route_name}")
        print(f"   Distance: {route.distance_km:,} km")
        print(f"   Transit: {route.transit_days} days")
        print(f"   Transport CO2: {route.transport_co2} t")
        print(f"   CBAM Tax: €{route.cbam_tax_eur}")
        if savings > 0:
            print(f"   ✅ SAVES €{savings:.2f} vs worst route")
