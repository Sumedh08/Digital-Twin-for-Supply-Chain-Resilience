import React, { useState, useEffect } from 'react';
import { CloudRain, Wind, Waves, Thermometer, AlertTriangle, RefreshCw } from 'lucide-react';
import { API_BASE } from '../config';

function WeatherPanel({ routeCode, routeName, autoFetch = false }) {
  const [weatherData, setWeatherData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Derive a short route code for the backend endpoint
  const getShortRoute = (code) => {
    if (!code) return 'suez';
    if (code.includes('IMEC')) return 'imec';
    if (code.includes('CAPE')) return 'cape';
    return 'suez'; // Default
  };

  const fetchWeather = async () => {
    if (!routeCode) return;
    setLoading(true);
    setError(null);
    try {
      const shortRoute = getShortRoute(routeCode);
      const res = await fetch(`${API_BASE}/weather/route/${shortRoute}`);
      const data = await res.json();
      if (data.success) {
        setWeatherData(data.weather);
      } else {
        setError('Weather data unavailable.');
      }
    } catch (err) {
      setError('Failed to load marine weather.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (autoFetch && routeCode) {
      fetchWeather();
    }
  }, [routeCode, autoFetch]);

  if (!weatherData && !loading && !error && !autoFetch) {
    return (
      <div className="p-4 border border-gray-700/50 bg-gray-800/30 rounded-xl flex items-center justify-between">
        <div className="flex items-center gap-3">
          <CloudRain className="text-blue-400" size={24} />
          <div>
            <div className="text-sm font-semibold text-white">Marine Weather</div>
            <div className="text-xs text-gray-400">Fetch real-time Open-Meteo data for {routeName || 'this route'}.</div>
          </div>
        </div>
        <button onClick={fetchWeather} className="px-3 py-1.5 bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 rounded text-xs font-semibold">
          Load Weather
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-4 border border-gray-700/50 bg-gray-800/30 rounded-xl flex items-center justify-center gap-2 text-gray-400 text-sm">
        <RefreshCw size={16} className="animate-spin text-blue-400" /> Fetching live marine conditions...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 border border-red-900/50 bg-red-900/10 rounded-xl text-red-400 text-sm flex gap-2">
        <AlertTriangle size={16} /> {error}
      </div>
    );
  }

  if (!weatherData) return null;

  const isSevere = weatherData.current_conditions?.wave_height_max_m > 4.0 || weatherData.current_conditions?.wind_speed_max_kn > 35;

  return (
    <div className="p-4 border border-gray-700/80 bg-gradient-to-br from-gray-800/80 to-gray-900/80 rounded-xl space-y-3 shadow-lg">
      <div className="flex items-center justify-between border-b border-gray-700/50 pb-2">
        <div className="flex items-center gap-2">
          <CloudRain size={18} className={isSevere ? "text-orange-400" : "text-blue-400"} />
          <h3 className="text-sm font-bold text-white">Live Marine Conditions</h3>
        </div>
        {weatherData.is_climatology_fallback ? (
          <span className="text-[10px] text-yellow-500 bg-yellow-500/10 px-1.5 py-0.5 rounded border border-yellow-500/20">Climatology Fallback</span>
        ) : (
          <span className="text-[10px] text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded border border-green-500/20">Live Open-Meteo API</span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="bg-black/40 p-2 rounded flex flex-col items-center justify-center border border-white/5">
          <Wind size={16} className="text-gray-400 mb-1" />
          <div className="text-lg font-bold text-white">{weatherData.current_conditions?.wind_speed_max_kn.toFixed(1)} <span className="text-xs font-normal text-gray-500">kn</span></div>
          <div className="text-[10px] text-gray-500 uppercase">Max Wind</div>
        </div>
        <div className="bg-black/40 p-2 rounded flex flex-col items-center justify-center border border-white/5">
          <Waves size={16} className="text-cyan-400 mb-1" />
          <div className="text-lg font-bold text-white">{weatherData.current_conditions?.wave_height_max_m.toFixed(1)} <span className="text-xs font-normal text-gray-500">m</span></div>
          <div className="text-[10px] text-gray-500 uppercase">Max Wave</div>
        </div>
        <div className="bg-black/40 p-2 rounded flex flex-col items-center justify-center border border-white/5">
          <Thermometer size={16} className="text-red-400 mb-1" />
          <div className="text-lg font-bold flex text-white">
            {weatherData.speed_penalty_pct > 0 ? `-${(weatherData.speed_penalty_pct * 100).toFixed(0)}%` : '0%'}
          </div>
          <div className="text-[10px] text-gray-500 uppercase text-center leading-tight mt-1">Speed Penalty</div>
        </div>
      </div>
      
      {weatherData.speed_penalty_pct > 0.05 && (
        <div className="text-xs text-orange-400 bg-orange-400/10 p-2 rounded flex items-start gap-2 border border-orange-400/20">
          <AlertTriangle size={14} className="shrink-0 mt-0.5" />
          <div>High seas detected across the route. Expect significant speed reduction (+{ (weatherData.speed_penalty_pct * 100).toFixed(1) }% penalty) and increased fuel burn.</div>
        </div>
      )}
    </div>
  );
}

export default WeatherPanel;
