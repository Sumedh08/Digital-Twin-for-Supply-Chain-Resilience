import React, { useState, useEffect } from 'react';
import { AlertTriangle, Shield, Globe, Activity, RefreshCw } from 'lucide-react';

const AISentinel = () => {
    const [riskData, setRiskData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    useEffect(() => {
        fetchRiskAnalysis(false);
    }, []);

    const fetchRiskAnalysis = async (force = false) => {
        if (force) setRefreshing(true);
        try {
            const url = force
                ? 'http://localhost:8000/ai/sentinel?force=true'
                : 'http://localhost:8000/ai/sentinel';
            const response = await fetch(url);
            const data = await response.json();
            setRiskData(data);
        } catch (error) {
            console.error('Error fetching AI risk:', error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    if (loading) {
        return (
            <div className="bg-gray-800/50 backdrop-blur-md p-6 rounded-xl border border-gray-700 animate-pulse">
                <div className="h-6 bg-gray-700 rounded w-1/3 mb-4"></div>
                <div className="h-20 bg-gray-700 rounded w-full"></div>
            </div>
        );
    }

    const getRiskColor = (level) => {
        switch (level) {
            case 'CRITICAL': return 'text-red-500 border-red-500/50 bg-red-500/10';
            case 'HIGH': return 'text-orange-500 border-orange-500/50 bg-orange-500/10';
            case 'MEDIUM': return 'text-yellow-500 border-yellow-500/50 bg-yellow-500/10';
            default: return 'text-green-500 border-green-500/50 bg-green-500/10';
        }
    };

    return (
        <div className="bg-gray-800/50 backdrop-blur-md p-6 rounded-xl border border-gray-700 shadow-xl">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Shield className="w-6 h-6 text-blue-400" />
                    <h2 className="text-xl font-bold text-white">Supply Chain Sentinel</h2>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => fetchRiskAnalysis(true)}
                        disabled={refreshing}
                        className="p-1.5 hover:bg-white/10 rounded-lg transition-colors disabled:opacity-50"
                        title="Refresh Analysis"
                    >
                        <RefreshCw className={`w-4 h-4 text-gray-400 hover:text-white ${refreshing ? 'animate-spin' : ''}`} />
                    </button>
                    <div className="flex items-center gap-2 text-xs text-gray-400">
                        <Activity className="w-4 h-4 animate-pulse text-green-400" />
                        <span>Gemma 3 12B</span>
                    </div>
                </div>
            </div>

            {riskData && (
                <div className="space-y-4">
                    <div className={`p-4 rounded-lg border ${getRiskColor(riskData.risk_level)} flex items-start gap-3`}>
                        <AlertTriangle className="w-6 h-6 shrink-0 mt-1" />
                        <div>
                            <div className="flex items-center justify-between mb-1">
                                <h3 className="font-bold text-lg">RISK LEVEL: {riskData.risk_level}</h3>
                                <span className="text-sm font-mono opacity-80">Score: {riskData.risk_score}/100</span>
                            </div>
                            <p className="text-sm opacity-90 leading-relaxed">{riskData.summary}</p>
                        </div>
                    </div>

                    <div className="bg-gray-900/50 p-4 rounded-lg border border-gray-700">
                        <h4 className="text-sm font-semibold text-gray-300 mb-2 flex items-center gap-2">
                            <Globe className="w-4 h-4" />
                            AI Recommendation
                        </h4>
                        <p className="text-gray-400 text-sm italic">"{riskData.recommendation}"</p>
                    </div>

                    <div className="text-right">
                        <span className="text-xs text-gray-600">Source: {riskData.source} • Updated: {new Date(riskData.timestamp).toLocaleTimeString()}</span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AISentinel;
