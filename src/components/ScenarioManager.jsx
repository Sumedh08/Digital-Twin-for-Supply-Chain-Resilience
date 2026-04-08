import React, { useState } from 'react';
import { Settings2, Play, Activity, AlertTriangle, Leaf, Factory, Layers } from 'lucide-react';
import { API_BASE } from '../config';

function ScenarioManager({ onScenarioComplete }) {
  const [activeTab, setActiveTab] = useState('scenarios'); // scenarios | twin
  const [loading, setLoading] = useState(false);
  const [twinState, setTwinState] = useState(null);
  
  // Example predefined scenarios
  const scenarios = [
    {
      id: 'baseline',
      name: 'Baseline Operations',
      icon: <Factory size={16} className="text-gray-400" />,
      desc: 'Standard HFO containers via Suez. $85/t ETS.',
      params: { fuel: 'HFO', etsBase: 85, suezBlocked: false }
    },
    {
      id: 'green_transition',
      name: 'Green Transition Policy',
      icon: <Leaf size={16} className="text-green-400" />,
      desc: 'Methanol fleet, high EU ETS price penalty ($150/t).',
      params: { fuel: 'Methanol', etsBase: 150, suezBlocked: false }
    },
    {
      id: 'red_sea_crisis',
      name: 'Red Sea Black Swan',
      icon: <AlertTriangle size={16} className="text-red-400" />,
      desc: 'Suez uninsurable. Reroute via Cape. High fuel burn.',
      params: { fuel: 'VLSFO', etsBase: 90, suezBlocked: true }
    }
  ];

  const fetchTwinState = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/twin/state`);
      const data = await res.json();
      if (data.success) {
        setTwinState(data.state);
      }
    } catch (e) {
      console.error("Failed to fetch twin state:", e);
    } finally {
      setLoading(false);
    }
  };

  const runTwinScenario = async (days) => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/twin/scenario`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ duration_days: days, dt_days: 1.0, initial_ets_price: 85.0 })
      });
      const data = await res.json();
      if (data.success) {
        setTwinState(data.simulation.final_state);
        if (onScenarioComplete) {
          onScenarioComplete('sd_simulation', data.simulation);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const runOptimizerScenario = async (scenario) => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/optimize/pareto`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cargo_weight_tonnes: 1000,
          ets_price_eur: scenario.params.etsBase,
          charter_rate_usd_per_day: 35000,
          suez_blocked: scenario.params.suezBlocked,
          exclude_fuels: scenario.params.fuel === 'Methanol' ? ['HFO', 'VLSFO'] : [] // Force green if requested
        })
      });
      const data = await res.json();
      if (data.success) {
        if (onScenarioComplete) {
          onScenarioComplete('pareto', data.optimization, scenario.name);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-800/60 border border-gray-700/50 rounded-xl overflow-hidden mb-6">
      {/* Header Tabs */}
      <div className="flex border-b border-gray-700/50">
        <button 
          onClick={() => setActiveTab('scenarios')}
          className={`px-4 py-3 text-sm font-medium flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'scenarios' ? 'border-purple-500 text-white bg-white/5' : 'border-transparent text-gray-400 hover:text-gray-300'}`}
        >
          <Settings2 size={16} /> Strategy Scenarios
        </button>
        <button 
          onClick={() => { setActiveTab('twin'); if(!twinState) fetchTwinState(); }}
          className={`px-4 py-3 text-sm font-medium flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'twin' ? 'border-blue-500 text-white bg-white/5' : 'border-transparent text-gray-400 hover:text-gray-300'}`}
        >
          <Layers size={16} /> Macro SD Twin
        </button>
      </div>

      <div className="p-4">
        {activeTab === 'scenarios' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {scenarios.map(sc => (
              <div key={sc.id} className="bg-gray-900/50 border border-gray-700 rounded-lg p-3 hover:border-gray-500 transition-all flex flex-col h-full">
                <div className="flex items-center gap-2 mb-2">
                  {sc.icon}
                  <span className="font-semibold text-sm text-gray-200">{sc.name}</span>
                </div>
                <p className="text-xs text-gray-400 flex-grow mb-3">{sc.desc}</p>
                <button 
                  disabled={loading}
                  onClick={() => runOptimizerScenario(sc)}
                  className="w-full py-1.5 flex justify-center items-center gap-1.5 bg-purple-600/20 text-purple-400 hover:bg-purple-600/30 border border-purple-500/30 rounded text-xs font-medium transition-colors disabled:opacity-50"
                >
                  <Play size={12} fill="currentColor" /> Analyze Trade-offs
                </button>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'twin' && (
          <div className="space-y-4">
            <p className="text-xs text-gray-400">
              Fleet-level System Dynamics. Explores macro-feedback between cumulative carbon emissions, regulatory ETS pricing, and green tech investment over time.
            </p>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="bg-gray-900/50 border border-gray-700 rounded p-3">
                <div className="text-xs text-gray-500 mb-1">Time (Days)</div>
                <div className="text-lg text-white font-mono">{twinState?.time_days?.toFixed(1) || '0.0'}</div>
              </div>
              <div className="bg-gray-900/50 border border-gray-700 rounded p-3">
                <div className="text-xs text-gray-500 mb-1">ETS Price</div>
                <div className="text-lg text-blue-400 font-mono">€{twinState?.ets_price_eur?.toFixed(2) || '85.00'}</div>
              </div>
              <div className="bg-gray-900/50 border border-gray-700 rounded p-3">
                <div className="text-xs text-gray-500 mb-1">Carbon Pool</div>
                <div className="text-lg text-red-400 font-mono">{twinState?.carbon_pool_tco2?.toLocaleString(undefined, {maximumFractionDigits:0}) || '0'} t</div>
              </div>
              <div className="bg-gray-900/50 border border-gray-700 rounded p-3">
                <div className="text-xs text-gray-500 mb-1">Green Invst.</div>
                <div className="text-lg text-green-400 font-mono">{( (twinState?.green_investment_level || 0.05) * 100).toFixed(1)}%</div>
              </div>
            </div>

            <div className="flex gap-3">
              <button 
                disabled={loading}
                onClick={() => runTwinScenario(30)}
                className="px-4 py-2 bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 border border-blue-500/30 rounded text-sm font-medium transition-colors flex items-center gap-2"
              >
                <Activity size={14} /> +30 Days
              </button>
              <button 
                disabled={loading}
                onClick={() => runTwinScenario(90)}
                className="px-4 py-2 bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 border border-blue-500/30 rounded text-sm font-medium transition-colors flex items-center gap-2"
              >
                <Activity size={14} /> +90 Days
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ScenarioManager;
