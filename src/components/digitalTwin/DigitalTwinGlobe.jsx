import React, { useEffect, useMemo, useRef, useState } from 'react';
import Globe from 'react-globe.gl';

const EARTH_TEXTURE = '//unpkg.com/three-globe/example/img/earth-night.jpg';
const SPACE_TEXTURE = '//unpkg.com/three-globe/example/img/night-sky.png';

const NODE_COLORS = {
  supplier: '#ef8b45',
  plant: '#4cc9f0',
  port: '#5dd39e',
  transport: '#f7d154'
};

const LABEL_COLORS = {
  supplier: 'rgba(255, 196, 146, 0.92)',
  plant: 'rgba(141, 232, 255, 0.92)',
  port: 'rgba(160, 245, 198, 0.92)',
  transport: 'rgba(247, 209, 84, 0.86)'
};

function supportsWebGl() {
  try {
    const canvas = document.createElement('canvas');
    return Boolean(
      window.WebGLRenderingContext &&
        (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
    );
  } catch {
    return false;
  }
}

function hashJitter(id) {
  let hash = 0;
  for (let index = 0; index < id.length; index += 1) {
    hash = (hash * 31 + id.charCodeAt(index)) >>> 0;
  }
  const lat = (((hash % 1000) / 1000) - 0.5) * 0.12;
  const lon = ((((Math.floor(hash / 1000)) % 1000) / 1000) - 0.5) * 0.12;
  return { lat, lon };
}

function shortLabel(label) {
  return label
    .replace(/ Iron Ore Mine$/i, '')
    .replace(/ Steel Plant$/i, '')
    .replace(/ Dock Complex$/i, '')
    .replace(/ Dispatch (\d+)$/i, ' D$1')
    .replace(/ Integrated /i, ' ')
    .trim();
}

function spreadCluster(point, index, total) {
  if (total <= 1) {
    return { lat: point.lat, lon: point.lon };
  }

  const angle = (Math.PI * 2 * index) / total;
  const radius = point.type === 'transport' ? 0.24 : 0.12;
  return {
    lat: point.lat + Math.sin(angle) * radius,
    lon: point.lon + Math.cos(angle) * radius
  };
}

function colorForPoint(item) {
  const base = NODE_COLORS[item.type] || '#ffffff';
  if (item.selected) return '#ffffff';
  if (item.muted) return 'rgba(116, 143, 178, 0.45)';
  return base;
}

function GlobeFallback({ points, arcs, onSelectThing }) {
  return (
    <div
      style={{
        minHeight: 560,
        borderRadius: 24,
        border: '1px solid rgba(125, 211, 252, 0.14)',
        background: 'radial-gradient(circle at top, rgba(14, 116, 144, 0.2), rgba(2, 6, 23, 0.95) 68%)',
        padding: 24,
        display: 'grid',
        gap: 18,
        alignContent: 'start'
      }}
    >
      <div>
        <p className="twin-kicker" style={{ marginBottom: 6 }}>Spatial fallback</p>
        <h3 style={{ margin: 0, fontSize: '1.35rem', color: '#e0f2fe' }}>2D network view</h3>
        <p style={{ margin: '8px 0 0', color: '#94a3b8', lineHeight: 1.6 }}>
          WebGL is unavailable, so the digital twin is rendering a safe topology view instead of a blank screen.
        </p>
      </div>

      <div style={{ display: 'grid', gap: 10 }}>
        {points.length > 0 ? (
          points.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectThing?.(item.id)}
              style={{
                textAlign: 'left',
                borderRadius: 16,
                border: item.selected ? '1px solid rgba(255,255,255,0.38)' : '1px solid rgba(148, 163, 184, 0.15)',
                background: item.selected ? 'rgba(255,255,255,0.1)' : 'rgba(15, 23, 42, 0.78)',
                padding: '12px 14px',
                color: '#e2e8f0',
                cursor: 'pointer'
              }}
            >
              <strong style={{ display: 'block', marginBottom: 4 }}>{item.label}</strong>
              <span style={{ color: '#94a3b8', fontSize: 13 }}>
                {item.state || item.type} | {item.lat.toFixed(2)}, {item.lon.toFixed(2)}
              </span>
            </button>
          ))
        ) : (
          <div style={{ color: '#94a3b8' }}>Run a scenario to populate the twin network.</div>
        )}
      </div>

      {arcs.length > 0 && (
        <div style={{ borderTop: '1px solid rgba(148, 163, 184, 0.12)', paddingTop: 14 }}>
          <p className="twin-kicker" style={{ marginBottom: 8 }}>Active links</p>
          <div style={{ display: 'grid', gap: 8 }}>
            {arcs.map((arc) => (
              <div key={arc.id} style={{ color: '#cbd5e1', fontSize: 13 }}>
                {arc.label}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DigitalTwinGlobeInner({ overlay, selectedThingId, onSelectThing }) {
  const globeRef = useRef(null);
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 920, height: 760 });
  const [webglEnabled, setWebglEnabled] = useState(true);

  useEffect(() => {
    setWebglEnabled(supportsWebGl());
  }, []);

  useEffect(() => {
    function updateDimensions() {
      const width = containerRef.current?.clientWidth || 920;
      setDimensions({
        width: Math.max(320, width - 2),
        height: width < 640 ? 520 : 760
      });
    }

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  const points = useMemo(() => {
    const baseNodes = (overlay?.nodes || []).map((node) => ({
      ...node,
      shortLabel: node.shortLabel || shortLabel(node.label),
      selected: node.id === selectedThingId || node.selected
    }));
    const trucks = (overlay?.trucks || []).map((truck) => ({
      ...truck,
      type: 'transport',
      shortLabel: shortLabel(truck.label),
      selected: truck.id === selectedThingId
    }));
    const grouped = new Map();
    [...baseNodes, ...trucks].forEach((point) => {
      const key = `${point.type}:${point.lat.toFixed(2)}:${point.lon.toFixed(2)}`;
      if (!grouped.has(key)) {
        grouped.set(key, []);
      }
      grouped.get(key).push(point);
    });

    return [...baseNodes, ...trucks].map((point) => {
      const key = `${point.type}:${point.lat.toFixed(2)}:${point.lon.toFixed(2)}`;
      const cluster = grouped.get(key) || [point];
      const clusterIndex = cluster.findIndex((item) => item.id === point.id);
      const clusterOffset = spreadCluster(point, Math.max(clusterIndex, 0), cluster.length);
      const jitter = hashJitter(point.id);

      return {
        ...point,
        displayLat: clusterOffset.lat + jitter.lat,
        displayLon: clusterOffset.lon + jitter.lon
      };
    });
  }, [overlay, selectedThingId]);

  const arcs = useMemo(() => {
    const locationById = Object.fromEntries(points.map((item) => [item.id, item]));

    return (overlay?.edges || [])
      .map((edge) => {
        const start = locationById[edge.from];
        const end = locationById[edge.to];
        if (!start || !end) return null;
        return {
          ...edge,
          startLat: start.displayLat,
          startLng: start.displayLon,
          endLat: end.displayLat,
          endLng: end.displayLon,
          color: edge.kind === 'delivery' ? '#f7d154' : edge.kind === 'dispatch' ? '#4cc9f0' : '#ef8b45',
          altitude: edge.kind === 'delivery' ? 0.085 : edge.kind === 'dispatch' ? 0.055 : 0.04
        };
      })
      .filter(Boolean);
  }, [overlay, points]);

  const rings = useMemo(
    () =>
      points.filter((item) => item.selected || (!item.muted && item.type !== 'transport' && item.totalTco2 > 0)),
    [points]
  );

  const labels = useMemo(
    () =>
      points
        .filter((item) => item.selected || !item.muted || item.type === 'transport')
        .map((item) => ({
          ...item,
          labelText: item.shortLabel
        })),
    [points]
  );

  useEffect(() => {
    if (!globeRef.current) return;
    const focusedPoint =
      points.find((item) => item.selected && item.type !== 'transport') ||
      points.find((item) => item.type === 'plant' && item.selected) ||
      null;

    if (focusedPoint) {
      globeRef.current.pointOfView(
        { lat: focusedPoint.displayLat, lng: focusedPoint.displayLon, altitude: 0.9 },
        900
      );
      return;
    }

    // Default: center on India showing JNPT
    globeRef.current.pointOfView({ lat: 20.0, lng: 73.0, altitude: 1.3 }, 900);
  }, [points]);

  if (!overlay) {
    return (
      <GlobeFallback points={[]} arcs={[]} onSelectThing={onSelectThing} />
    );
  }

  if (!webglEnabled) {
    return <GlobeFallback points={points} arcs={arcs} onSelectThing={onSelectThing} />;
  }

  return (
    <div ref={containerRef} className="twin-globe-shell">
      <Globe
        ref={globeRef}
        width={dimensions.width}
        height={dimensions.height}
        animateIn={false}
        globeImageUrl={EARTH_TEXTURE}
        backgroundImageUrl={SPACE_TEXTURE}
        showAtmosphere
        atmosphereColor="#6dd3ff"
        atmosphereAltitude={0.11}
        labelsData={labels}
        labelLat={(item) => item.displayLat}
        labelLng={(item) => item.displayLon}
        labelText={(item) => item.labelText}
        labelSize={(item) => (item.selected ? 0.95 : item.type === 'transport' ? 0.42 : 0.58)}
        labelDotRadius={(item) => (item.type === 'transport' ? 0.18 : 0.22)}
        labelColor={(item) => (item.muted ? 'rgba(148, 163, 184, 0.46)' : LABEL_COLORS[item.type] || 'rgba(226, 232, 240, 0.9)')}
        labelResolution={2}
        pointsData={points}
        pointLat={(item) => item.displayLat}
        pointLng={(item) => item.displayLon}
        pointColor={(item) => colorForPoint(item)}
        pointAltitude={(item) => {
          if (item.selected) return 0.022;
          if (item.muted) return 0.006;
          return item.type === 'transport' ? 0.011 : item.overview ? 0.007 : 0.012;
        }}
        pointRadius={(item) => (item.selected ? 0.36 : item.type === 'transport' ? 0.17 : 0.28)}
        pointLabel={(item) => `
          <div style="padding:6px 8px;background:rgba(8,17,31,0.92);border:1px solid rgba(145,176,221,0.25);border-radius:10px;font-size:11px;">
            <strong>${item.shortLabel}</strong><br/>
            ${item.state || item.type}<br/>
            ${item.totalTco2?.toFixed?.(2) || '0.00'} tCO2
          </div>
        `}
        pointResolution={18}
        onPointClick={(item) => onSelectThing?.(item.id)}
        arcsData={arcs}
        arcStartLat={(item) => item.startLat}
        arcStartLng={(item) => item.startLng}
        arcEndLat={(item) => item.endLat}
        arcEndLng={(item) => item.endLng}
        arcColor={(item) => [item.color, item.color]}
        arcAltitude={(item) => item.altitude}
        arcDashLength={0.6}
        arcDashGap={0.2}
        arcDashAnimateTime={2200}
        arcStroke={0.36}
        arcLabel={(item) => item.label}
        ringsData={rings}
        ringLat={(item) => item.displayLat}
        ringLng={(item) => item.displayLon}
        ringColor={(item) => colorForPoint(item)}
        ringMaxRadius={(item) => (item.selected ? 2.4 : 1.55)}
        ringPropagationSpeed={1.2}
        ringRepeatPeriod={1350}
      />
    </div>
  );
}

const DigitalTwinGlobe = React.memo(DigitalTwinGlobeInner, (prev, next) => {
  return prev.overlay === next.overlay && prev.selectedThingId === next.selectedThingId;
});

export default DigitalTwinGlobe;
