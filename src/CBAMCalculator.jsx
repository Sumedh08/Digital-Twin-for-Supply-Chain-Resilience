import React, { useState, useEffect } from 'react';
import {
    Calculator,
    Ship,
    Factory,
    TrendingDown,
    Euro,
    Leaf,
    ChevronDown,
    BarChart3,
    Route,
    RefreshCw,
    FileDown,
    Globe,
    Zap,
    Anchor
} from 'lucide-react';

import { API_BASE } from './config';

function CBAMCalculator({ onRouteSelect }) {
    // State for form inputs
    const [productType, setProductType] = useState('steel_hot_rolled');
    const [weight, setWeight] = useState(100);
    const [route, setRoute] = useState('INMUN_NLRTM_SUEZ');
    const [originCountry, setOriginCountry] = useState('india');
    const [shipType, setShipType] = useState('container_ship');

    // State for data from API
    const [products, setProducts] = useState([]);
    const [routes, setRoutes] = useState([]);
    const [countries, setCountries] = useState([]);
    const [shipTypes, setShipTypes] = useState([]);
    const [etsPrice, setEtsPrice] = useState(null);

    // State for results
    const [result, setResult] = useState(null);
    const [comparison, setComparison] = useState(null);
    const [loading, setLoading] = useState(false);
    const [showComparison, setShowComparison] = useState(false);

    // Fetch all reference data on mount
    useEffect(() => {
        fetchProducts();
        fetchRoutes();
        fetchEtsPrice();
        fetchCountries();
        fetchShipTypes();
    }, []);

    const fetchProducts = async () => {
        try {
            const res = await fetch(`${API_BASE}/cbam/products`);
            const data = await res.json();
            if (data.success) {
                setProducts(data.products);
            }
        } catch (err) {
            setProducts([
                { id: 'steel_hot_rolled', emission_factor: 1.85, unit: 'tCO2/tonne' },
                { id: 'steel_cold_rolled', emission_factor: 2.10, unit: 'tCO2/tonne' },
                { id: 'aluminium_primary', emission_factor: 14.5, unit: 'tCO2/tonne' },
                { id: 'aluminium_products', emission_factor: 8.0, unit: 'tCO2/tonne' },
                { id: 'cement_clinker', emission_factor: 0.85, unit: 'tCO2/tonne' },
                { id: 'ammonia', emission_factor: 1.80, unit: 'tCO2/tonne' },
                { id: 'urea', emission_factor: 0.73, unit: 'tCO2/tonne' },
            ]);
        }
    };

    const fetchRoutes = async () => {
        try {
            const res = await fetch(`${API_BASE}/cbam/routes`);
            const data = await res.json();
            if (data.success) {
                setRoutes(data.routes);
            }
        } catch (err) {
            setRoutes([
                { code: 'INMUN_NLRTM_SUEZ', name: 'Mumbai -> Rotterdam (Suez Canal)', distance_km: 11735 },
                { code: 'INMUN_NLRTM_IMEC', name: 'Mumbai -> Rotterdam (IMEC Corridor)', distance_km: 10742 },
                { code: 'INMUN_NLRTM_CAPE', name: 'Mumbai -> Rotterdam (Cape of Good Hope)', distance_km: 19910 },
            ]);
        }
    };

    const fetchCountries = async () => {
        try {
            const res = await fetch(`${API_BASE}/cbam/countries`);
            const data = await res.json();
            if (data.success) {
                setCountries(data.countries);
            }
        } catch (err) {
            setCountries([
                { id: 'india', name: 'India', grid_intensity_gco2_kwh: 632 },
                { id: 'china', name: 'China', grid_intensity_gco2_kwh: 544 },
                { id: 'vietnam', name: 'Vietnam', grid_intensity_gco2_kwh: 460 },
                { id: 'turkey', name: 'Turkey', grid_intensity_gco2_kwh: 384 },
                { id: 'south_korea', name: 'South Korea', grid_intensity_gco2_kwh: 378 },
            ]);
        }
    };

    const fetchShipTypes = async () => {
        try {
            const res = await fetch(`${API_BASE}/cbam/ship-types`);
            const data = await res.json();
            if (data.success) {
                setShipTypes(data.ship_types);
            }
        } catch (err) {
            setShipTypes([
                { id: 'container_ship', name: 'Container Ship', emission_factor_gco2_tkm: 16.14 },
                { id: 'bulk_carrier', name: 'Bulk Carrier', emission_factor_gco2_tkm: 4.0 },
                { id: 'oil_tanker', name: 'Oil Tanker', emission_factor_gco2_tkm: 5.11 },
                { id: 'roro_cargo', name: 'Ro-Ro Cargo', emission_factor_gco2_tkm: 21.3 },
                { id: 'general_cargo', name: 'General Cargo', emission_factor_gco2_tkm: 12.2 },
            ]);
        }
    };

    const fetchEtsPrice = async () => {
        try {
            const res = await fetch(`${API_BASE}/cbam/ets-price`);
            const data = await res.json();
            if (data.success) {
                setEtsPrice(data.price_eur);
            }
        } catch (err) {
            setEtsPrice(68.35);
        }
    };

    const calculateEmissions = async () => {
        setLoading(true);
        setShowComparison(false);
        try {
            const res = await fetch(`${API_BASE}/cbam/calculate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    product_type: productType,
                    weight_tonnes: parseFloat(weight),
                    route: route,
                    origin_port: 'mundra',
                    destination_port: 'rotterdam',
                    origin_country: originCountry,
                    ship_type: shipType
                })
            });
            const data = await res.json();
            if (data.success) {
                setResult(data.data);
            }
        } catch (err) {
            // Fallback calculation using local factors
            const factor = products.find(p => p.id === productType)?.emission_factor || 1.85;
            const mfgCO2 = factor * weight;
            const elecCO2 = weight * 0.58 * 632 / 1000; // Default: India steel
            const shipFactor = shipTypes.find(s => s.id === shipType)?.emission_factor_gco2_tkm || 16.14;
            const routeDistance = routes.find(r => r.code === route)?.distance_km || 11735;
            const transportCO2 = shipFactor * weight * routeDistance / 1_000_000;
            const portCO2 = 0.027 * weight;
            const totalCO2 = mfgCO2 + elecCO2 + transportCO2 + portCO2;

            setResult({
                product_type: productType,
                weight_tonnes: weight,
                origin_country: countries.find(c => c.id === originCountry)?.name || originCountry,
                ship_type: shipTypes.find(s => s.id === shipType)?.name || shipType,
                route: routes.find(r => r.code === route)?.name || route,
                emissions: {
                    manufacturing_co2: mfgCO2.toFixed(3),
                    electricity_co2: elecCO2.toFixed(3),
                    transport_co2: transportCO2.toFixed(3),
                    port_handling_co2: portCO2.toFixed(3),
                    total_co2: totalCO2.toFixed(3)
                },
                scope_breakdown: {
                    scope_1_manufacturing: mfgCO2.toFixed(3),
                    scope_2_electricity: elecCO2.toFixed(3),
                    scope_3_transport: (transportCO2 + portCO2).toFixed(3)
                },
                breakdown_percentage: {
                    manufacturing: ((mfgCO2 / totalCO2) * 100).toFixed(1),
                    electricity: ((elecCO2 / totalCO2) * 100).toFixed(1),
                    transport: ((transportCO2 / totalCO2) * 100).toFixed(1),
                    port_handling: ((portCO2 / totalCO2) * 100).toFixed(1)
                },
                cbam_tax: {
                    eur: (mfgCO2 * etsPrice).toFixed(2),
                    inr: (mfgCO2 * etsPrice * 90).toFixed(2),
                    ets_price_eur: etsPrice,
                    note: "CBAM tax applies to Scope 1 (direct manufacturing) emissions only"
                }
            });
        }
        setLoading(false);
    };

    const compareRoutes = async () => {
        setLoading(true);
        setShowComparison(true);
        try {
            const res = await fetch(`${API_BASE}/cbam/compare-routes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    product_type: productType,
                    weight_tonnes: parseFloat(weight),
                    origin_port: 'mundra',
                    destination_port: 'rotterdam',
                    origin_country: originCountry,
                    ship_type: shipType
                })
            });
            const data = await res.json();
            if (data.success) {
                setComparison(data);
                if (onRouteSelect) {
                    onRouteSelect(data.routes);
                }
            }
        } catch (err) {
            setComparison({
                routes: [
                    { rank: 1, route_name: 'Suez Canal', cbam_tax_eur: 17550, transit_days: 18, is_greenest: true },
                    { rank: 2, route_name: 'IMEC Corridor', cbam_tax_eur: 17725, transit_days: 14, is_greenest: false },
                    { rank: 3, route_name: 'Cape of Good Hope', cbam_tax_eur: 18662, transit_days: 28, is_greenest: false },
                ],
                recommendation: { best_route: 'Suez Canal', savings_eur: 1112 }
            });
        }
        setLoading(false);
    };

    const formatCurrency = (val, currency = '€') => {
        return `${currency}${parseFloat(val).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
    };

    const formatProductName = (id) => {
        return id.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    };

    return (
        <div className="h-full overflow-y-auto p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-green-500/20 rounded-lg">
                    <Leaf className="text-green-400" size={24} />
                </div>
                <div>
                    <h2 className="text-xl font-bold text-white">Carbon Calculator</h2>
                    <p className="text-xs text-gray-400">Full Scope 1 / 2 / 3 Emission Analysis</p>
                </div>
            </div>

            {/* EU ETS Price Badge */}
            <div className="flex items-center justify-between p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                <div className="flex items-center gap-2">
                    <Euro size={16} className="text-blue-400" />
                    <span className="text-sm text-gray-300">EU ETS Carbon Price</span>
                </div>
                <span className="text-lg font-bold text-blue-400">
                    {etsPrice ? `€${etsPrice}/tonne` : 'Fetching live price...'}
                </span>
            </div>

            {/* Input Form */}
            <div className="space-y-4">
                {/* Product Type */}
                <div>
                    <label className="block text-xs text-gray-400 mb-2 uppercase tracking-wider">
                        Product Type
                    </label>
                    <div className="relative">
                        <select
                            value={productType}
                            onChange={(e) => setProductType(e.target.value)}
                            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 text-white appearance-none cursor-pointer hover:border-gray-500 focus:border-green-500 focus:outline-none transition-colors"
                        >
                            {products.map(p => (
                                <option key={p.id} value={p.id}>
                                    {formatProductName(p.id)} ({p.emission_factor} {p.unit})
                                </option>
                            ))}
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={20} />
                    </div>
                </div>

                {/* Origin Country */}
                <div>
                    <label className="block text-xs text-gray-400 mb-2 uppercase tracking-wider">
                        <Globe size={12} className="inline mr-1" />
                        Origin Country (Scope 2 Grid)
                    </label>
                    <div className="relative">
                        <select
                            value={originCountry}
                            onChange={(e) => setOriginCountry(e.target.value)}
                            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 text-white appearance-none cursor-pointer hover:border-gray-500 focus:border-yellow-500 focus:outline-none transition-colors"
                        >
                            {countries.map(c => (
                                <option key={c.id} value={c.id}>
                                    {c.name} ({c.grid_intensity_gco2_kwh} gCO₂/kWh)
                                </option>
                            ))}
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={20} />
                    </div>
                </div>

                {/* Weight */}
                <div>
                    <label className="block text-xs text-gray-400 mb-2 uppercase tracking-wider">
                        Weight (Tonnes)
                    </label>
                    <div className="relative">
                        <input
                            type="number"
                            value={weight}
                            onChange={(e) => setWeight(e.target.value)}
                            min="1"
                            max="100000"
                            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 text-white focus:border-green-500 focus:outline-none transition-colors"
                        />
                        <Factory className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                    </div>
                </div>

                {/* Ship Type */}
                <div>
                    <label className="block text-xs text-gray-400 mb-2 uppercase tracking-wider">
                        <Anchor size={12} className="inline mr-1" />
                        Ship Type (Scope 3)
                    </label>
                    <div className="relative">
                        <select
                            value={shipType}
                            onChange={(e) => setShipType(e.target.value)}
                            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 text-white appearance-none cursor-pointer hover:border-gray-500 focus:border-cyan-500 focus:outline-none transition-colors"
                        >
                            {shipTypes.map(s => (
                                <option key={s.id} value={s.id}>
                                    {s.name} ({s.emission_factor_gco2_tkm} gCO₂/t-km)
                                </option>
                            ))}
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={20} />
                    </div>
                </div>

                {/* Route */}
                <div>
                    <label className="block text-xs text-gray-400 mb-2 uppercase tracking-wider">
                        Shipping Route
                    </label>
                    <div className="relative">
                        <select
                            value={route}
                            onChange={(e) => setRoute(e.target.value)}
                            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 text-white appearance-none cursor-pointer hover:border-gray-500 focus:border-green-500 focus:outline-none transition-colors"
                        >
                            {routes.map(r => (
                                <option key={r.code} value={r.code}>
                                    {r.name}
                                </option>
                            ))}
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={20} />
                    </div>
                </div>
            </div>

            {/* Action Buttons */}
            <div className="grid grid-cols-2 gap-3">
                <button
                    onClick={calculateEmissions}
                    disabled={loading}
                    className="py-3 bg-gradient-to-r from-green-600 to-emerald-600 rounded-lg font-semibold hover:from-green-500 hover:to-emerald-500 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                >
                    {loading ? <RefreshCw size={16} className="animate-spin" /> : <Calculator size={16} />}
                    Calculate
                </button>

                <button
                    onClick={compareRoutes}
                    disabled={loading}
                    className="py-3 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg font-semibold hover:from-blue-500 hover:to-indigo-500 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                >
                    {loading ? <RefreshCw size={16} className="animate-spin" /> : <Route size={16} />}
                    Compare
                </button>
            </div>

            {/* Results */}
            {result && !showComparison && (
                <div className="mt-6 p-4 bg-gray-800/50 border border-gray-700 rounded-xl space-y-4 animate-in fade-in duration-300">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <BarChart3 size={18} className="text-green-400" />
                        Emission Breakdown
                    </h3>

                    {/* Total CO2 */}
                    <div className="text-center p-4 bg-gradient-to-r from-green-500/20 to-emerald-500/20 border border-green-500/30 rounded-lg">
                        <div className="text-3xl font-bold text-green-400">
                            {parseFloat(result.emissions.total_co2).toLocaleString()} tCO₂
                        </div>
                        <div className="text-xs text-gray-400 mt-1">Total Embedded Emissions (All Scopes)</div>
                    </div>

                    {/* Scope Summary Cards */}
                    {result.scope_breakdown && (
                        <div className="grid grid-cols-3 gap-2">
                            <div className="p-2 bg-orange-500/10 border border-orange-500/30 rounded-lg text-center">
                                <div className="text-xs text-gray-400">Scope 1</div>
                                <div className="text-sm font-bold text-orange-400">
                                    {parseFloat(result.scope_breakdown.scope_1_manufacturing).toLocaleString()} t
                                </div>
                                <div className="text-[10px] text-gray-500">Manufacturing</div>
                            </div>
                            <div className="p-2 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-center">
                                <div className="text-xs text-gray-400">Scope 2</div>
                                <div className="text-sm font-bold text-yellow-400">
                                    {parseFloat(result.scope_breakdown.scope_2_electricity).toLocaleString()} t
                                </div>
                                <div className="text-[10px] text-gray-500">Electricity</div>
                            </div>
                            <div className="p-2 bg-blue-500/10 border border-blue-500/30 rounded-lg text-center">
                                <div className="text-xs text-gray-400">Scope 3</div>
                                <div className="text-sm font-bold text-blue-400">
                                    {parseFloat(result.scope_breakdown.scope_3_transport).toLocaleString()} t
                                </div>
                                <div className="text-[10px] text-gray-500">Transport</div>
                            </div>
                        </div>
                    )}

                    {/* Breakdown Bars */}
                    <div className="space-y-3">
                        {/* Manufacturing (Scope 1) */}
                        <div>
                            <div className="flex justify-between text-xs mb-1">
                                <span className="text-gray-400">⚙️ Manufacturing (Scope 1)</span>
                                <span className="text-white">{result.emissions.manufacturing_co2} tCO₂ ({result.breakdown_percentage.manufacturing}%)</span>
                            </div>
                            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-orange-500 rounded-full transition-all duration-500"
                                    style={{ width: `${result.breakdown_percentage.manufacturing}%` }}
                                />
                            </div>
                        </div>

                        {/* Electricity (Scope 2) */}
                        <div>
                            <div className="flex justify-between text-xs mb-1">
                                <span className="text-gray-400">⚡ Electricity (Scope 2)</span>
                                <span className="text-white">{result.emissions.electricity_co2} tCO₂ ({result.breakdown_percentage.electricity}%)</span>
                            </div>
                            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-yellow-500 rounded-full transition-all duration-500"
                                    style={{ width: `${result.breakdown_percentage.electricity}%` }}
                                />
                            </div>
                        </div>

                        {/* Transport (Scope 3) */}
                        <div>
                            <div className="flex justify-between text-xs mb-1">
                                <span className="text-gray-400">🚢 Transport (Scope 3)</span>
                                <span className="text-white">{result.emissions.transport_co2} tCO₂ ({result.breakdown_percentage.transport}%)</span>
                            </div>
                            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-blue-500 rounded-full transition-all duration-500"
                                    style={{ width: `${result.breakdown_percentage.transport}%` }}
                                />
                            </div>
                        </div>

                        {/* Port Handling (Scope 3) */}
                        <div>
                            <div className="flex justify-between text-xs mb-1">
                                <span className="text-gray-400">🏗️ Port Handling (Scope 3)</span>
                                <span className="text-white">{result.emissions.port_handling_co2} tCO₂ ({result.breakdown_percentage.port_handling}%)</span>
                            </div>
                            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-purple-500 rounded-full transition-all duration-500"
                                    style={{ width: `${result.breakdown_percentage.port_handling}%` }}
                                />
                            </div>
                        </div>
                    </div>

                    {/* CBAM Tax - Scope 1 Only */}
                    <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                        <div className="flex justify-between items-center">
                            <div>
                                <div className="text-2xl font-bold text-red-400">
                                    {formatCurrency(result.cbam_tax.eur)}
                                </div>
                                <div className="text-xs text-gray-400">CBAM Tax (Scope 1 Only) @ €{result.cbam_tax.ets_price_eur}/t</div>
                            </div>
                            <div className="text-right">
                                <div className="text-xl font-bold text-yellow-400">
                                    {formatCurrency(result.cbam_tax.inr, '₹')}
                                </div>
                                <div className="text-xs text-gray-400">INR Equivalent</div>
                            </div>
                        </div>
                        <div className="text-[10px] text-gray-500 mt-2 italic">
                            {result.cbam_tax.note}
                        </div>
                    </div>

                    {/* Data Sources */}
                    {result.sources && (
                        <div className="text-[10px] text-gray-500 space-y-0.5 pt-2 border-t border-gray-700">
                            <div className="font-semibold text-gray-400">Data Sources:</div>
                            {result.sources.map((s, i) => (
                                <div key={i}>• {s}</div>
                            ))}
                        </div>
                    )}

                    {/* Download Report Button */}
                    <button
                        onClick={() => {
                            const url = `${API_BASE}/cbam/generate-report`;
                            fetch(url, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    product_type: productType,
                                    weight_tonnes: parseFloat(weight),
                                    route: route,
                                    origin_port: 'mundra',
                                    destination_port: 'rotterdam',
                                    exporter_name: 'Export Company',
                                    exporter_address: 'Mumbai, India',
                                    exporter_gstin: 'XXXXXXXXXXXXX'
                                })
                            })
                                .then(res => res.blob())
                                .then(blob => {
                                    const url = window.URL.createObjectURL(blob);
                                    const a = document.createElement('a');
                                    a.href = url;
                                    a.download = `CBAM_Report_${new Date().toISOString().slice(0, 10)}.pdf`;
                                    document.body.appendChild(a);
                                    a.click();
                                    a.remove();
                                    window.URL.revokeObjectURL(url);
                                })
                                .catch(err => alert('Report generation failed. Is the backend running?'));
                        }}
                        className="w-full mt-4 py-3 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg font-semibold hover:from-purple-500 hover:to-pink-500 transition-all flex items-center justify-center gap-2"
                    >
                        <FileDown size={18} />
                        Download PDF Report
                    </button>
                </div>
            )}

            {/* Route Comparison */}
            {comparison && showComparison && (
                <div className="mt-6 p-4 bg-gray-800/50 border border-gray-700 rounded-xl space-y-4 animate-in fade-in duration-300">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <Ship size={18} className="text-blue-400" />
                        Route Comparison
                    </h3>

                    {/* Recommendation */}
                    <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg flex items-center gap-3">
                        <TrendingDown className="text-green-400" size={24} />
                        <div>
                            <div className="text-sm font-semibold text-green-400">
                                Recommended: {comparison.recommendation.best_route}
                            </div>
                            <div className="text-xs text-gray-400">
                                Saves {formatCurrency(comparison.recommendation.savings_eur)} vs worst option
                            </div>
                        </div>
                    </div>

                    {/* Routes List */}
                    <div className="space-y-2">
                        {comparison.routes.map((r, i) => (
                            <div
                                key={i}
                                className={`p-3 rounded-lg border transition-all cursor-pointer hover:bg-white/5 ${r.is_greenest
                                    ? 'bg-green-500/10 border-green-500/50'
                                    : 'bg-gray-700/30 border-gray-600'
                                    }`}
                                onClick={() => {
                                    setRoute(r.route_code);
                                    setShowComparison(false);
                                }}
                            >
                                <div className="flex justify-between items-center">
                                    <div className="flex items-center gap-2">
                                        <span className={`text-lg font-bold ${r.is_greenest ? 'text-green-400' : 'text-gray-400'}`}>
                                            #{r.rank}
                                        </span>
                                        <div>
                                            <div className="text-sm text-white">{r.route_name}</div>
                                            <div className="text-xs text-gray-400">{r.transit_days} days transit</div>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <div className={`text-lg font-bold ${r.is_greenest ? 'text-green-400' : 'text-white'}`}>
                                            {formatCurrency(r.cbam_tax_eur)}
                                        </div>
                                        {r.is_greenest && (
                                            <span className="text-xs text-green-400 flex items-center gap-1">
                                                <Leaf size={12} /> Greenest
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    <button
                        onClick={() => setShowComparison(false)}
                        className="w-full py-2 text-sm text-gray-400 hover:text-white transition-colors"
                    >
                        ← Back to Calculator
                    </button>
                </div>
            )}
        </div>
    );
}

export default CBAMCalculator;
