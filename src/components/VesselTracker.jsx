import React, { useState, useEffect } from 'react';
import {
    Ship,
    AlertTriangle,
    Shield,
    Cloud,
    Clock,
    Navigation,
    MapPin,
    RefreshCw,
    ChevronDown,
    Anchor,
    ArrowRight,
    Route
} from 'lucide-react';

import { API_BASE } from '../config';

const ROUTES = [
    { code: 'INMUN_NLRTM_SUEZ', name: 'Mumbai → Rotterdam (Suez Canal)', distance: '6,337 nm', days: '~18 days' },
    { code: 'INMUN_NLRTM_CAPE', name: 'Mumbai → Rotterdam (Cape of Good Hope)', distance: '10,750 nm', days: '~28 days' },
    { code: 'INMUN_NLRTM_IMEC', name: 'Mumbai → Rotterdam (IMEC Corridor)', distance: '5,800 nm', days: '~14 days' },
    { code: 'INMUN_DEHAM_SUEZ', name: 'Mumbai → Hamburg (Suez Canal)', distance: '6,100 nm', days: '~18 days' },
    { code: 'INMAA_NLRTM_SUEZ', name: 'Chennai → Rotterdam (Suez Canal)', distance: '8,100 nm', days: '~22 days' },
];

const SHIP_TYPES = [
    { id: 'Container Ship', name: 'Container Ship' },
    { id: 'Bulk Carrier', name: 'Bulk Carrier' },
    { id: 'Oil Tanker', name: 'Oil Tanker' },
    { id: 'Ro-Ro Cargo', name: 'Ro-Ro Cargo' },
    { id: 'General Cargo', name: 'General Cargo' },
];

const severityColor = {
    LOW: 'text-green-400',
    MEDIUM: 'text-yellow-400',
    HIGH: 'text-orange-400',
    CRITICAL: 'text-red-400',
};

const severityBg = {
    LOW: 'bg-green-500/10 border-green-500/30',
    MEDIUM: 'bg-yellow-500/10 border-yellow-500/30',
    HIGH: 'bg-orange-500/10 border-orange-500/30',
    CRITICAL: 'bg-red-500/10 border-red-500/30',
};

const categoryIcon = {
    SECURITY: '🛡️',
    WEATHER: '🌊',
    CONGESTION: '⚓',
    GEOPOLITICAL: '🌍',
};

function VesselTracker({ onVesselSelect }) {
    const [selectedRoute, setSelectedRoute] = useState('INMUN_NLRTM_SUEZ');
    const [selectedShipType, setSelectedShipType] = useState('Container Ship');
    const [analysis, setAnalysis] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const analyzeRoute = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(
                `${API_BASE}/route/analyze?route_code=${selectedRoute}&ship_type=${encodeURIComponent(selectedShipType)}`
            );
            const data = await res.json();
            if (data.success) {
                setAnalysis(data.data);
            } else {
                setError('Analysis failed');
            }
        } catch (err) {
            setError('Backend not reachable. Please start the server.');
        }
        setLoading(false);
    };

    const getRiskBadgeColor = (level) => {
        switch (level) {
            case 'LOW': return 'bg-green-500';
            case 'MEDIUM': return 'bg-yellow-500';
            case 'HIGH': return 'bg-orange-500';
            case 'CRITICAL': return 'bg-red-500';
            default: return 'bg-gray-500';
        }
    };

    return (
        <div className="h-full overflow-y-auto p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                    <Navigation className="text-blue-400" size={24} />
                </div>
                <div>
                    <h2 className="text-xl font-bold text-white">Vessel Intelligence</h2>
                    <p className="text-xs text-gray-400">AI-Powered Route Risk Analysis</p>
                </div>
            </div>

            {/* Route Selection */}
            <div className="space-y-4">
                <div>
                    <label className="block text-xs text-gray-400 mb-2 uppercase tracking-wider">
                        <Route size={12} className="inline mr-1" />
                        Trade Lane
                    </label>
                    <div className="relative">
                        <select
                            value={selectedRoute}
                            onChange={(e) => setSelectedRoute(e.target.value)}
                            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 text-white appearance-none cursor-pointer hover:border-gray-500 focus:border-blue-500 focus:outline-none transition-colors"
                        >
                            {ROUTES.map(r => (
                                <option key={r.code} value={r.code}>
                                    {r.name} ({r.distance})
                                </option>
                            ))}
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={20} />
                    </div>
                </div>

                <div>
                    <label className="block text-xs text-gray-400 mb-2 uppercase tracking-wider">
                        <Anchor size={12} className="inline mr-1" />
                        Ship Type
                    </label>
                    <div className="relative">
                        <select
                            value={selectedShipType}
                            onChange={(e) => setSelectedShipType(e.target.value)}
                            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 text-white appearance-none cursor-pointer hover:border-gray-500 focus:border-blue-500 focus:outline-none transition-colors"
                        >
                            {SHIP_TYPES.map(s => (
                                <option key={s.id} value={s.id}>{s.name}</option>
                            ))}
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={20} />
                    </div>
                </div>

                <button
                    onClick={analyzeRoute}
                    disabled={loading}
                    className="w-full py-3 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-lg font-semibold hover:from-blue-500 hover:to-cyan-500 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                >
                    {loading ? <RefreshCw size={16} className="animate-spin" /> : <Shield size={16} />}
                    {loading ? 'Analyzing...' : 'Analyze Route Risk'}
                </button>
            </div>

            {/* Error */}
            {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                    ⚠️ {error}
                </div>
            )}

            {/* Analysis Results */}
            {analysis && (
                <div className="space-y-4 animate-in fade-in duration-300">
                    {/* Risk Score Header */}
                    <div className={`p-4 rounded-xl border ${severityBg[analysis.analysis.risk_level]}`}>
                        <div className="flex items-center justify-between">
                            <div>
                                <div className="text-xs text-gray-400 uppercase">Overall Risk</div>
                                <div className={`text-3xl font-bold ${severityColor[analysis.analysis.risk_level]}`}>
                                    {analysis.analysis.overall_risk_score}/100
                                </div>
                            </div>
                            <div className={`px-3 py-1 rounded-full text-sm font-bold text-black ${getRiskBadgeColor(analysis.analysis.risk_level)}`}>
                                {analysis.analysis.risk_level}
                            </div>
                        </div>
                        <div className="mt-2 text-sm text-gray-300">{analysis.route_name}</div>
                        <div className="flex gap-4 mt-1 text-xs text-gray-400">
                            <span>📏 {analysis.distance_nm?.toLocaleString()} nm</span>
                            <span>⏱️ ~{analysis.typical_days} days</span>
                            <span>🚢 {analysis.ship_type}</span>
                        </div>
                    </div>

                    {/* Waypoints */}
                    {analysis.waypoints && (
                        <div className="p-3 bg-gray-800/50 border border-gray-700 rounded-lg">
                            <div className="text-xs text-gray-400 mb-2 font-semibold uppercase">Route Waypoints</div>
                            <div className="flex flex-wrap items-center gap-1 text-xs text-gray-300">
                                {analysis.waypoints.map((w, i) => (
                                    <React.Fragment key={i}>
                                        <span className="px-2 py-0.5 bg-gray-700 rounded">{w}</span>
                                        {i < analysis.waypoints.length - 1 && (
                                            <ArrowRight size={10} className="text-gray-500" />
                                        )}
                                    </React.Fragment>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Risk Breakdown */}
                    <div className="space-y-2">
                        <div className="text-xs text-gray-400 font-semibold uppercase">Risk Breakdown</div>
                        {analysis.analysis.risks?.map((risk, i) => (
                            <div key={i} className={`p-3 rounded-lg border ${severityBg[risk.severity]}`}>
                                <div className="flex items-center justify-between mb-1">
                                    <span className="text-sm font-semibold text-white">
                                        {categoryIcon[risk.category]} {risk.category}
                                    </span>
                                    <span className={`text-xs font-bold ${severityColor[risk.severity]}`}>
                                        {risk.severity}
                                    </span>
                                </div>
                                <div className="text-xs text-gray-400 mb-1">
                                    <MapPin size={10} className="inline mr-1" />
                                    {risk.zone}
                                </div>
                                <div className="text-xs text-gray-300">{risk.description}</div>
                            </div>
                        ))}
                    </div>

                    {/* Recommendation */}
                    <div className={`p-4 rounded-xl border ${analysis.analysis.should_reroute ? 'bg-red-500/10 border-red-500/30' : 'bg-green-500/10 border-green-500/30'}`}>
                        <div className="text-xs text-gray-400 mb-1 uppercase font-semibold">
                            {analysis.analysis.should_reroute ? '⚠️ Reroute Recommended' : '✅ Recommendation'}
                        </div>
                        <div className="text-sm text-gray-200">
                            {analysis.analysis.recommendation}
                        </div>

                        {/* Alternative Route */}
                        {analysis.analysis.should_reroute && analysis.alternative && (
                            <div className="mt-3 p-2 bg-gray-800/50 rounded-lg border border-gray-600">
                                <div className="text-xs text-gray-400">Alternative Route:</div>
                                <div className="text-sm text-white font-semibold">{analysis.alternative.name}</div>
                                <div className="flex gap-3 text-xs text-gray-400 mt-1">
                                    <span>📏 {analysis.alternative.distance_nm?.toLocaleString()} nm</span>
                                    <span>⏱️ ~{analysis.alternative.typical_days} days</span>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Source & Timestamp */}
                    <div className="text-[10px] text-gray-500 space-y-0.5 pt-2 border-t border-gray-700">
                        <div>Source: {analysis.source}</div>
                        <div>Updated: {new Date(analysis.timestamp).toLocaleString()}</div>
                        {analysis.cached && <div className="text-yellow-500">📦 Cached result (refreshes every 10 min)</div>}
                    </div>
                </div>
            )}
        </div>
    );
}

export default VesselTracker;
