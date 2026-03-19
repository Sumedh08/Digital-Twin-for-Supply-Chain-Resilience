import React from 'react';
import { Factory, Ship, Anchor, PieChart } from 'lucide-react';

/**
 * EmissionBreakdown Component
 * Visual breakdown of emissions by category with animated donut chart
 */
const EmissionBreakdown = ({ data }) => {
    if (!data) return null;

    const {
        manufacturing_co2 = 0,
        transport_co2 = 0,
        port_handling_co2 = 0,
        total_co2 = 0
    } = data;

    // Calculate percentages
    const mfgPct = total_co2 > 0 ? (manufacturing_co2 / total_co2 * 100) : 0;
    const transPct = total_co2 > 0 ? (transport_co2 / total_co2 * 100) : 0;
    const portPct = total_co2 > 0 ? (port_handling_co2 / total_co2 * 100) : 0;

    // SVG Donut Chart
    const size = 180;
    const strokeWidth = 25;
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;

    // Calculate stroke-dasharray for each segment
    const mfgDash = (mfgPct / 100) * circumference;
    const transDash = (transPct / 100) * circumference;
    const portDash = (portPct / 100) * circumference;

    // Offsets for positioning each segment
    const mfgOffset = 0;
    const transOffset = mfgDash;
    const portOffset = mfgDash + transDash;

    const categories = [
        {
            name: 'Manufacturing',
            value: manufacturing_co2,
            pct: mfgPct,
            color: '#ef4444',
            icon: Factory
        },
        {
            name: 'Transport',
            value: transport_co2,
            pct: transPct,
            color: '#3b82f6',
            icon: Ship
        },
        {
            name: 'Port Handling',
            value: port_handling_co2,
            pct: portPct,
            color: '#22c55e',
            icon: Anchor
        }
    ];

    return (
        <div className="emission-breakdown" style={{ background: 'rgba(255, 255, 255, 0.05)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '12px', padding: '16px', marginTop: '16px' }}>
            <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '16px', fontWeight: '600', color: 'white', marginBottom: '16px' }}>
                <PieChart size={18} />
                Emission Breakdown
            </h4>

            <div className="breakdown-chart-container" style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
                {/* Donut Chart */}
                <div style={{ position: 'relative', width: size, height: size }}>
                    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="donut-chart">
                        <circle
                            cx={size / 2}
                            cy={size / 2}
                            r={radius}
                            fill="none"
                            stroke="rgba(255,255,255,0.1)"
                            strokeWidth={strokeWidth}
                        />

                        {/* Manufacturing segment */}
                        <circle
                            cx={size / 2}
                            cy={size / 2}
                            r={radius}
                            fill="none"
                            stroke="#ef4444"
                            strokeWidth={strokeWidth}
                            strokeDasharray={`${mfgDash} ${circumference - mfgDash}`}
                            strokeDashoffset={circumference * 0.25}
                            className="segment segment-mfg"
                            style={{ transform: 'rotate(-90deg)', transformOrigin: 'center', transition: 'stroke-dasharray 1s ease-out' }}
                        />

                        {/* Transport segment */}
                        <circle
                            cx={size / 2}
                            cy={size / 2}
                            r={radius}
                            fill="none"
                            stroke="#3b82f6"
                            strokeWidth={strokeWidth}
                            strokeDasharray={`${transDash} ${circumference - transDash}`}
                            strokeDashoffset={circumference * 0.25 - mfgDash}
                            className="segment segment-trans"
                            style={{ transform: 'rotate(-90deg)', transformOrigin: 'center', transition: 'stroke-dasharray 1s ease-out' }}
                        />

                        {/* Port Handling segment */}
                        <circle
                            cx={size / 2}
                            cy={size / 2}
                            r={radius}
                            fill="none"
                            stroke="#22c55e"
                            strokeWidth={strokeWidth}
                            strokeDasharray={`${portDash} ${circumference - portDash}`}
                            strokeDashoffset={circumference * 0.25 - mfgDash - transDash}
                            className="segment segment-port"
                            style={{ transform: 'rotate(-90deg)', transformOrigin: 'center', transition: 'stroke-dasharray 1s ease-out' }}
                        />

                        {/* Center text */}
                        <text x={size / 2} y={size / 2 - 10} textAnchor="middle" className="total-label" style={{ fill: '#9ca3af', fontSize: '12px' }}>
                            Total
                        </text>
                        <text x={size / 2} y={size / 2 + 15} textAnchor="middle" className="total-value" style={{ fill: 'white', fontSize: '24px', fontWeight: 'bold' }}>
                            {total_co2.toFixed(1)}
                        </text>
                        <text x={size / 2} y={size / 2 + 35} textAnchor="middle" className="total-unit" style={{ fill: '#6b7280', fontSize: '12px' }}>
                            tCO₂
                        </text>
                    </svg>
                </div>

                {/* Legend */}
                <div className="breakdown-legend" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {categories.map((cat) => (
                        <div key={cat.name} className="legend-item" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <div className="legend-color" style={{ width: '4px', height: '32px', borderRadius: '4px', backgroundColor: cat.color }} />
                            <div className="legend-info" style={{ flex: 1 }}>
                                <div className="legend-header" style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#d1d5db', fontSize: '13px', marginBottom: '2px' }}>
                                    <cat.icon size={14} />
                                    <span className="legend-name">{cat.name}</span>
                                </div>
                                <div className="legend-values" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                                    <span className="legend-value" style={{ color: 'white', fontWeight: '600', fontSize: '14px' }}>{cat.value.toFixed(2)} tCO₂</span>
                                    <span className="legend-pct" style={{ color: '#9ca3af', fontSize: '12px' }}>({cat.pct.toFixed(1)}%)</span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="breakdown-insight" style={{ marginTop: '16px', padding: '12px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '8px', fontSize: '13px', color: '#d1d5db', lineHeight: '1.5' }}>
                {mfgPct > 80 && (
                    <p className="insight-text" style={{ marginBottom: transPct > 20 ? '8px' : '0' }}>
                        💡 <strong>Manufacturing dominates</strong> your carbon footprint.
                        Consider switching to recycled materials or green suppliers to reduce CBAM costs.
                    </p>
                )}
                {transPct > 20 && (
                    <p className="insight-text" style={{ margin: 0 }}>
                        🚢 <strong>Transport emissions are significant.</strong>
                        The IMEC corridor could help reduce your shipping carbon footprint.
                    </p>
                )}
            </div>
        </div>
    );
};

export default EmissionBreakdown;
