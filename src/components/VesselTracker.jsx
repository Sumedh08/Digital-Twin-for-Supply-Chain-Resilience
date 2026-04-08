import React, { useState } from 'react';
import {
  Anchor,
  ChevronDown,
  Gauge,
  MapPin,
  Navigation,
  Newspaper,
  RefreshCw,
  Route,
  Shield
} from 'lucide-react';

import { API_BASE } from '../config';

const ROUTES = [
  { code: 'INMUN_NLRTM_SUEZ', name: 'Mumbai -> Rotterdam (Suez Canal)', distance: '6,337 nm', days: '~18 days' },
  { code: 'INMUN_NLRTM_CAPE', name: 'Mumbai -> Rotterdam (Cape of Good Hope)', distance: '10,750 nm', days: '~28 days' },
  { code: 'INMUN_NLRTM_IMEC', name: 'Mumbai -> Rotterdam (IMEC Corridor)', distance: '5,800 nm', days: '~14 days' },
  { code: 'INMUN_DEHAM_SUEZ', name: 'Mumbai -> Hamburg (Suez Canal)', distance: '6,100 nm', days: '~18 days' },
  { code: 'INMAA_NLRTM_SUEZ', name: 'Chennai -> Rotterdam (Suez Canal)', distance: '8,100 nm', days: '~22 days' }
];

const SHIP_TYPES = [
  { id: 'Container Ship', name: 'Container Ship' },
  { id: 'Bulk Carrier', name: 'Bulk Carrier' },
  { id: 'Oil Tanker', name: 'Oil Tanker' },
  { id: 'Ro-Ro Cargo', name: 'Ro-Ro Cargo' },
  { id: 'General Cargo', name: 'General Cargo' }
];

const severityColor = {
  LOW: 'text-green-400',
  MEDIUM: 'text-yellow-400',
  HIGH: 'text-orange-400',
  CRITICAL: 'text-red-400'
};

const severityBg = {
  LOW: 'bg-green-500/10 border-green-500/30',
  MEDIUM: 'bg-yellow-500/10 border-yellow-500/30',
  HIGH: 'bg-orange-500/10 border-orange-500/30',
  CRITICAL: 'bg-red-500/10 border-red-500/30'
};

const categoryIcon = {
  SECURITY: 'Shield',
  WEATHER: 'Weather',
  CONGESTION: 'Ops',
  GEOPOLITICAL: 'Geo'
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
        onVesselSelect?.(data.data);
      } else {
        setError('Analysis failed');
      }
    } catch {
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

  const targetCount = analysis?.analysis?.target_reference_count || 10;
  const visibleHeadlines = analysis?.analysis?.scored_headlines?.slice(0, Math.max(10, targetCount)) || [];

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-blue-500/20 rounded-lg">
          <Navigation className="text-blue-400" size={24} />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">AI Sentinel</h2>
          <p className="text-xs text-gray-400">Route risk analysis with a strict 10-reference recency floor</p>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-xs text-gray-400 mb-2 uppercase tracking-wider">
            <Route size={12} className="inline mr-1" />
            Trade lane
          </label>
          <div className="relative">
            <select
              value={selectedRoute}
              onChange={(e) => setSelectedRoute(e.target.value)}
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 text-white appearance-none cursor-pointer hover:border-gray-500 focus:border-blue-500 focus:outline-none transition-colors"
            >
              {ROUTES.map((route) => (
                <option key={route.code} value={route.code}>
                  {route.name} ({route.distance})
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={20} />
          </div>
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-2 uppercase tracking-wider">
            <Anchor size={12} className="inline mr-1" />
            Ship type
          </label>
          <div className="relative">
            <select
              value={selectedShipType}
              onChange={(e) => setSelectedShipType(e.target.value)}
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 text-white appearance-none cursor-pointer hover:border-gray-500 focus:border-blue-500 focus:outline-none transition-colors"
            >
              {SHIP_TYPES.map((ship) => (
                <option key={ship.id} value={ship.id}>{ship.name}</option>
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
          {loading ? 'Analyzing...' : 'Analyze route risk'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {analysis && (
        <div className="space-y-4 animate-in fade-in duration-300">
          <div className={`p-4 rounded-xl border ${severityBg[analysis.analysis.risk_level]}`}>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-gray-400 uppercase">Overall risk</div>
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
              <span>{analysis.distance_nm?.toLocaleString()} nm</span>
              <span>~{analysis.typical_days} days</span>
              <span>{analysis.ship_type}</span>
            </div>
          </div>

          {analysis.waypoints && (
            <div className="p-3 bg-gray-800/50 border border-gray-700 rounded-lg">
              <div className="text-xs text-gray-400 mb-2 font-semibold uppercase">Route waypoints</div>
              <div className="flex flex-wrap items-center gap-1 text-xs text-gray-300">
                {analysis.waypoints.map((waypoint, index) => (
                  <React.Fragment key={waypoint}>
                    <span className="px-2 py-0.5 bg-gray-700 rounded">{waypoint}</span>
                    {index < analysis.waypoints.length - 1 && <span className="text-gray-500">/</span>}
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-2">
            <div className="text-xs text-gray-400 font-semibold uppercase">Risk breakdown</div>
            {analysis.analysis.risks?.map((risk, index) => (
              <div key={`${risk.category}-${index}`} className={`p-3 rounded-lg border ${severityBg[risk.severity]}`}>
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

          <div className="p-4 bg-gray-800/50 border border-gray-700 rounded-xl space-y-3">
            <div className="flex items-center gap-2 text-xs text-gray-400 font-semibold uppercase">
              <Gauge size={12} />
              News window
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-sm">
              <div className="rounded-lg border border-gray-700 bg-black/20 p-3">
                <div className="text-xs text-gray-500 uppercase mb-1">Qualified references</div>
                <div className="text-white font-semibold">{analysis.analysis.qualified_reference_count || 0}</div>
              </div>
              <div className="rounded-lg border border-gray-700 bg-black/20 p-3">
                <div className="text-xs text-gray-500 uppercase mb-1">Target</div>
                <div className="text-white font-semibold">{targetCount} articles</div>
              </div>
              <div className="rounded-lg border border-gray-700 bg-black/20 p-3">
                <div className="text-xs text-gray-500 uppercase mb-1">Shortfall</div>
                <div className="text-white font-semibold">{analysis.analysis.insufficient_reference_depth || 0}</div>
              </div>
              <div className="rounded-lg border border-gray-700 bg-black/20 p-3">
                <div className="text-xs text-gray-500 uppercase mb-1">Window start</div>
                <div className="text-white font-semibold">
                  {analysis.analysis.recency_model?.window_start_date || 'N/A'}
                </div>
              </div>
            </div>
            {analysis.analysis.collector_sources?.length > 0 && (
              <p className="text-xs text-gray-400 leading-relaxed">
                Collectors: {analysis.analysis.collector_sources.join(', ')}
              </p>
            )}
            {analysis.analysis.recency_model?.formula && (
              <p className="text-xs text-gray-400 leading-relaxed">
                {analysis.analysis.recency_model.formula}
              </p>
            )}
            {analysis.analysis.analysis_provisional && (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                This reading is provisional because the engine has not yet reached the 10-reference threshold. The score uses the available evidence, but confidence is intentionally held back until the shortfall is closed.
              </div>
            )}
          </div>

          {visibleHeadlines.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-gray-400 font-semibold uppercase">
                <Newspaper size={12} />
                Live news evidence
              </div>
              <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                {visibleHeadlines.map((headline, index) => (
                  <div key={`${headline.title}-${index}`} className="p-3 rounded-lg border border-gray-700 bg-gray-900/40">
                    <div className="flex items-start justify-between gap-3 mb-1">
                      <div className="text-sm text-white leading-snug">{headline.title}</div>
                      <div className="text-xs font-mono text-cyan-300 shrink-0">{headline.article_score}</div>
                    </div>
                    <div className="flex flex-wrap gap-2 text-[11px] text-gray-400">
                      <span>{new Date(headline.published_at).toLocaleDateString()}</span>
                      <span>{headline.category}</span>
                      <span>Relevance {headline.relevance_factor || headline.recency_factor}/3</span>
                      <span>Severity {headline.severity_factor}/10</span>
                      <span>{headline.query}</span>
                    </div>
                    {headline.link && (
                      <a
                        href={headline.link}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-block mt-2 text-xs text-blue-400 hover:text-blue-300"
                      >
                        Open source article
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className={`p-4 rounded-xl border ${analysis.analysis.should_reroute ? 'bg-red-500/10 border-red-500/30' : 'bg-green-500/10 border-green-500/30'}`}>
            <div className="text-xs text-gray-400 mb-1 uppercase font-semibold">
              {analysis.analysis.should_reroute ? 'Reroute recommended' : 'Recommendation'}
            </div>
            <div className="text-sm text-gray-200">
              {analysis.analysis.recommendation}
            </div>

            {analysis.analysis.should_reroute && analysis.alternative && (
              <div className="mt-3 p-2 bg-gray-800/50 rounded-lg border border-gray-600">
                <div className="text-xs text-gray-400">Alternative route</div>
                <div className="text-sm text-white font-semibold">{analysis.alternative.name}</div>
                <div className="flex gap-3 text-xs text-gray-400 mt-1">
                  <span>{analysis.alternative.distance_nm?.toLocaleString()} nm</span>
                  <span>~{analysis.alternative.typical_days} days</span>
                </div>
              </div>
            )}
          </div>

          <div className="text-[10px] text-gray-500 space-y-0.5 pt-2 border-t border-gray-700">
            <div>Source: {analysis.source}</div>
            <div>Updated: {new Date(analysis.timestamp).toLocaleString()}</div>
            {analysis.cached && <div className="text-yellow-500">Cached result (refreshes every 10 min)</div>}
          </div>
        </div>
      )}
    </div>
  );
}

export default VesselTracker;
