import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Euro, RefreshCw, Clock } from 'lucide-react';

import { API_BASE } from '../config';

/**
 * LiveETSPrice Component
 * Displays real-time EU ETS carbon price with sparkline and change indicators
 */
const LiveETSPrice = ({ compact = false }) => {
    const [priceData, setPriceData] = useState(null);
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [lastUpdate, setLastUpdate] = useState(null);

    const fetchPrice = async () => {
        try {
            setLoading(true);
            const response = await fetch(`${API_BASE}/ets/live-price`);
            const data = await response.json();
            if (data.success) {
                setPriceData(data.price);
                setLastUpdate(new Date().toLocaleTimeString());
            }
        } catch (err) {
            setError('Failed to fetch ETS price');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const fetchHistory = async () => {
        try {
            const response = await fetch(`${API_BASE}/ets/history?days=7`);
            const data = await response.json();
            if (data.success) {
                setHistory(data.history);
            }
        } catch (err) {
            console.error('Failed to fetch price history:', err);
        }
    };

    useEffect(() => {
        fetchPrice();
        fetchHistory();

        // Refresh every 5 minutes
        const interval = setInterval(() => {
            fetchPrice();
            fetchHistory();
        }, 5 * 60 * 1000);

        return () => clearInterval(interval);
    }, []);

    // Simple sparkline SVG
    const renderSparkline = () => {
        if (history.length < 2) return null;

        const prices = history.map(h => h.price);
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);
        const range = maxPrice - minPrice || 1;

        const width = 100;
        const height = 30;
        const points = prices.map((price, i) => {
            const x = (i / (prices.length - 1)) * width;
            const y = height - ((price - minPrice) / range) * height;
            return `${x},${y}`;
        }).join(' ');

        const isPositive = priceData?.change_24h >= 0;
        const color = isPositive ? '#22c55e' : '#ef4444';

        return (
            <svg width={width} height={height} className="sparkline">
                <polyline
                    fill="none"
                    stroke={color}
                    strokeWidth="2"
                    points={points}
                />
            </svg>
        );
    };

    if (loading && !priceData) {
        return (
            <div className="ets-price-card loading">
                <RefreshCw className="animate-spin" size={20} />
                <span>Loading ETS price...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="ets-price-card error">
                <span>{error}</span>
                <button onClick={fetchPrice}>Retry</button>
            </div>
        );
    }

    const isPositive = priceData?.change_24h >= 0;

    if (compact) {
        return (
            <div className="ets-price-compact">
                <Euro size={16} />
                <span className="price">{priceData?.current_eur?.toFixed(2)}</span>
                <span className={`change ${isPositive ? 'positive' : 'negative'}`}>
                    {isPositive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                    {Math.abs(priceData?.change_pct || 0).toFixed(1)}%
                </span>
            </div>
        );
    }

    return (
        <div className="ets-price-card" style={{ background: 'rgba(255, 255, 255, 0.05)', backdropFilter: 'blur(20px)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '16px', padding: '24px', minWidth: '280px' }}>
            <div className="ets-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', fontWeight: '500', color: '#9ca3af' }}>
                    <Euro size={20} />
                    EU ETS Carbon Price
                </h3>
                <button
                    onClick={fetchPrice}
                    className="refresh-btn"
                    title="Refresh"
                    style={{ background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer', padding: '4px' }}
                >
                    <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                </button>
            </div>

            <div className="ets-body" style={{ marginBottom: '16px' }}>
                <div className="current-price" style={{ display: 'flex', alignItems: 'baseline', marginBottom: '8px' }}>
                    <span className="currency" style={{ fontSize: '24px', fontWeight: '600', color: '#34d399', marginRight: '2px' }}>€</span>
                    <span className="value" style={{ fontSize: '40px', fontWeight: '700', color: '#f9fafb' }}>{priceData?.current_eur?.toFixed(2)}</span>
                    <span className="unit" style={{ fontSize: '14px', color: '#6b7280', marginLeft: '8px' }}>/tonne CO₂</span>
                </div>

                <div className={`price-change ${isPositive ? 'positive' : 'negative'}`} style={{
                    display: 'flex', alignItems: 'center', gap: '4px', fontSize: '14px', padding: '4px 8px', borderRadius: '9999px', width: 'fit-content',
                    background: isPositive ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                    color: isPositive ? '#22c55e' : '#ef4444'
                }}>
                    {isPositive ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                    <span>
                        {isPositive ? '+' : ''}€{priceData?.change_24h?.toFixed(2)}
                        ({isPositive ? '+' : ''}{priceData?.change_pct?.toFixed(1)}%)
                    </span>
                    <span className="period" style={{ color: '#6b7280', marginLeft: '4px' }}>24h</span>
                </div>

                <div className="sparkline-container" style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    {renderSparkline()}
                    <span className="sparkline-label" style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>7-day trend</span>
                </div>
            </div>

            <div className="ets-footer" style={{ display: 'flex', justifyContent: 'space-between', paddingTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <div className="stat" style={{ textAlign: 'center' }}>
                    <span className="label" style={{ display: 'block', fontSize: '12px', color: '#6b7280' }}>52W Low</span>
                    <span className="value" style={{ fontSize: '14px', fontWeight: '600', color: '#9ca3af' }}>€{priceData?.low_52w?.toFixed(0)}</span>
                </div>
                <div className="stat" style={{ textAlign: 'center' }}>
                    <span className="label" style={{ display: 'block', fontSize: '12px', color: '#6b7280' }}>30D Avg</span>
                    <span className="value" style={{ fontSize: '14px', fontWeight: '600', color: '#9ca3af' }}>€{priceData?.average_30d?.toFixed(0)}</span>
                </div>
                <div className="stat" style={{ textAlign: 'center' }}>
                    <span className="label" style={{ display: 'block', fontSize: '12px', color: '#6b7280' }}>52W High</span>
                    <span className="value" style={{ fontSize: '14px', fontWeight: '600', color: '#9ca3af' }}>€{priceData?.high_52w?.toFixed(0)}</span>
                </div>
            </div>

            <div className="last-update" style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: '#6b7280', marginTop: '8px' }}>
                <Clock size={12} />
                <span>Updated: {lastUpdate}</span>
            </div>
        </div>
    );
};

export default LiveETSPrice;
