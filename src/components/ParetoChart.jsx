import React from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import { Target, Info } from 'lucide-react';

const COLORS = {
  'HFO': '#eab308',       // Yellow
  'VLSFO': '#f97316',     // Orange
  'LNG': '#3b82f6',       // Blue
  'Bio-LNG': '#22c55e',   // Green
  'Methanol': '#a855f7',  // Purple
  'GreenNH3': '#10b981',  // Emerald
};

const SHAPES = {
  'suez': 'circle',
  'imec': 'triangle',
  'cape': 'square'
};

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-gray-800 border border-gray-600 p-3 rounded-lg shadow-xl text-sm max-w-xs">
        <div className="font-bold text-white mb-1 border-b border-gray-700 pb-1">
          {data.route_description}
        </div>
        <div className="space-y-1 text-gray-300">
          <div><span className="text-gray-400">Fuel:</span> <span style={{ color: COLORS[data.fuel_type] || '#fff' }}>{data.fuel_type}</span></div>
          <div><span className="text-gray-400">Speed:</span> {data.speed_knots} knots</div>
          <div><span className="text-gray-400">Cost:</span> €{data.total_cost_eur.toLocaleString()}</div>
          <div><span className="text-gray-400">Carbon:</span> {data.carbon_wtw_tco2.toFixed(1)} tCO₂</div>
          <div><span className="text-gray-400">Time:</span> {data.transit_days.toFixed(1)} days</div>
          <div><span className="text-gray-400">Risk:</span> {(data.risk_score * 100).toFixed(0)}%</div>
          
          <div className="mt-2 pt-2 border-t border-gray-700">
            <span className="text-xs font-semibold px-2 py-1 bg-white/10 rounded block text-center">
              {data.trade_off_label}
            </span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

/**
 * Renders the exact NSGA-II-lite Pareto front returned by the backend.
 * X-axis: Total Cost (EUR)
 * Y-axis: Carbon WtW (tCO2)
 */
function ParetoChart({ data, recommendation }) {
  if (!data || data.length === 0) return null;

  return (
    <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-4 mt-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-md font-bold text-white flex items-center gap-2">
          <Target size={18} className="text-purple-400" />
          Pareto-Optimal Frontier (Cost vs Carbon)
        </h3>
        <div className="group relative">
          <Info size={16} className="text-gray-500 hover:text-gray-300 cursor-help" />
          <div className="absolute right-0 w-64 p-2 bg-gray-900 text-xs text-gray-300 rounded shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
            Displays only the non-dominated solutions. Every point here minimizes a trade-off between Cost, Carbon, Time, and Risk.
          </div>
        </div>
      </div>

      <div className="h-64 w-full text-xs">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
            {/* Dark theme grid */}
            
            <XAxis 
              type="number" 
              dataKey="total_cost_eur" 
              name="Cost" 
              unit="€" 
              tick={{fill: '#9ca3af', fontSize: 10}}
              tickFormatter={(val) => `€${Math.round(val/1000)}k`}
              domain={['dataMin - 5000', 'dataMax + 5000']}
              stroke="#4b5563"
            />
            <YAxis 
              type="number" 
              dataKey="carbon_wtw_tco2" 
              name="Carbon" 
              unit="t" 
              tick={{fill: '#9ca3af', fontSize: 10}}
              domain={['dataMin - 100', 'dataMax + 100']}
              stroke="#4b5563"
            />
            <Tooltip content={<CustomTooltip />} cursor={{strokeDasharray: '3 3', stroke: '#4b5563'}} />
            
            <Scatter name="Pareto Front" data={data}>
              {data.map((entry, index) => {
                const isRecommended = recommendation && 
                  entry.route === recommendation.route && 
                  entry.fuel_type === recommendation.fuel_type &&
                  entry.speed_knots === recommendation.speed_knots;
                  
                return (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={COLORS[entry.fuel_type] || '#8884d8'} 
                    stroke={isRecommended ? '#fff' : 'none'}
                    strokeWidth={isRecommended ? 2 : 0}
                    style={{ filter: isRecommended ? 'drop-shadow(0 0 4px rgba(255,255,255,0.5))' : 'none' }}
                  />
                );
              })}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center justify-center gap-4 mt-2 text-xs text-gray-400">
        <div className="flex gap-3">
          {Object.entries(COLORS).map(([fuel, color]) => (
            data.some(d => d.fuel_type === fuel) && (
              <div key={fuel} className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }}></div>
                <span>{fuel}</span>
              </div>
            )
          ))}
        </div>
      </div>
    </div>
  );
}

export default ParetoChart;
