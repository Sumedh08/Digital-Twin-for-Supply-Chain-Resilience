import React, { useEffect, useRef, useState } from 'react';
import Globe from 'react-globe.gl';

const GlobeComponent = ({ routeData }) => {
    const globeEl = useRef();
    const [places, setPlaces] = useState([]);
    const [arcs, setArcs] = useState([]);

    useEffect(() => {
        if (globeEl.current) {
            // Initial camera position (focused on IMEC region)
            globeEl.current.pointOfView({ lat: 25.0, lng: 55.0, altitude: 2.5 });
        }

        // Define IMEC Nodes with carbon-friendly labels
        // Define IMEC Nodes with carbon-friendly labels
        const imecNodes = [
            { name: "Mumbai", lat: 18.94, lng: 72.82, type: "port", co2Label: "Origin Port" },
            { name: "Jebel Ali", lat: 25.00, lng: 55.06, type: "port", co2Label: "IMEC Hub" },
            { name: "Riyadh", lat: 24.71, lng: 46.67, type: "rail", co2Label: "Rail Transit" },
            { name: "Haifa", lat: 32.80, lng: 34.98, type: "port", co2Label: "IMEC Port" },
            { name: "Piraeus", lat: 37.94, lng: 23.63, type: "port", co2Label: "EU Gateway" },
            { name: "Rotterdam", lat: 51.90, lng: 4.50, type: "port", co2Label: "EU Destination" },
            { name: "Hamburg", lat: 53.55, lng: 9.99, type: "port", co2Label: "EU Destination" },

            // Chokepoints
            { name: "Bab el-Mandeb", lat: 12.60, lng: 43.30, type: "chokepoint", co2Label: "Risk Zone" },
            { name: "Suez Canal", lat: 30.58, lng: 32.27, type: "chokepoint", co2Label: "Risk Zone" },
            { name: "Cape of Good Hope", lat: -34.36, lng: 18.47, type: "chokepoint", co2Label: "Longer Route" }
        ];
        setPlaces(imecNodes);

        // Default shipping routes with carbon data
        const defaultArcs = [
            // Route 1: Mumbai → Rotterdam (Suez) - GREEN (Greenest)
            {
                startLat: 18.94, startLng: 72.82,
                endLat: 12.60, endLng: 43.30,
                color: ['#22c55e', '#22c55e'],
                label: "Suez Route (18 days)",
                route: 'suez',
                co2: "18.8 tCO2"
            },
            {
                startLat: 12.60, startLng: 43.30,
                endLat: 30.58, endLng: 32.27,
                color: ['#22c55e', '#22c55e'],
                label: "Red Sea",
                route: 'suez',
                co2: ""
            },
            {
                startLat: 30.58, startLng: 32.27,
                endLat: 37.94, endLng: 23.63,
                color: ['#22c55e', '#22c55e'],
                label: "Mediterranean",
                route: 'suez',
                co2: ""
            },
            {
                startLat: 37.94, startLng: 23.63,
                endLat: 51.90, endLng: 4.50,
                color: ['#22c55e', '#22c55e'],
                label: "To Rotterdam",
                route: 'suez',
                co2: ""
            },

            // Route 2: IMEC Corridor - ORANGE (Hybrid)
            {
                startLat: 18.94, startLng: 72.82,
                endLat: 25.00, endLng: 55.06,
                color: ['#3b82f6', '#3b82f6'],
                label: "IMEC Sea (14 days)",
                route: 'imec',
                co2: "20.8 tCO2"
            },
            {
                startLat: 25.00, startLng: 55.06,
                endLat: 24.71, endLng: 46.67,
                color: ['#f97316', '#f97316'],
                label: "IMEC Rail",
                route: 'imec',
                co2: ""
            },
            {
                startLat: 24.71, startLng: 46.67,
                endLat: 32.80, endLng: 34.98,
                color: ['#f97316', '#f97316'],
                label: "IMEC Rail",
                route: 'imec',
                co2: ""
            },
            {
                startLat: 32.80, startLng: 34.98,
                endLat: 37.94, endLng: 23.63,
                color: ['#3b82f6', '#3b82f6'],
                label: "IMEC Sea",
                route: 'imec',
                co2: ""
            },
            {
                startLat: 37.94, startLng: 23.63,
                endLat: 51.90, endLng: 4.50,
                color: ['#3b82f6', '#3b82f6'],
                label: "To Rotterdam",
                route: 'imec',
                co2: ""
            },

            // Route 3: Cape of Good Hope - RED (Longest)
            {
                startLat: 18.94, startLng: 72.82,
                endLat: -34.36, endLng: 18.47,
                color: ['#ef4444', '#ef4444'],
                label: "Cape Route (28 days)",
                route: 'cape',
                co2: "31.9 tCO2"
            },
            {
                startLat: -34.36, startLng: 18.47,
                endLat: 51.90, endLng: 4.50,
                color: ['#ef4444', '#ef4444'],
                label: "Atlantic",
                route: 'cape',
                co2: ""
            },
        ];
        setArcs(defaultArcs);
    }, []);

    // Get label color based on node type
    const getLabelColor = (d) => {
        switch (d.type) {
            case 'port': return 'rgba(34, 197, 94, 0.9)'; // Green
            case 'rail': return 'rgba(249, 115, 22, 0.9)'; // Orange
            case 'chokepoint': return 'rgba(239, 68, 68, 0.9)'; // Red
            default: return 'rgba(255, 255, 255, 0.75)';
        }
    };

    return (
        <Globe
            ref={globeEl}
            globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
            backgroundImageUrl="//unpkg.com/three-globe/example/img/night-sky.png"

            // Labels
            labelsData={places}
            labelLat={d => d.lat}
            labelLng={d => d.lng}
            labelText={d => d.name}
            labelSize={1.5}
            labelDotRadius={0.5}
            labelColor={getLabelColor}
            labelResolution={2}

            // Arcs (Shipping Routes)
            arcsData={arcs}
            arcLabel={d => `${d.label}${d.co2 ? ` - ${d.co2}` : ''}`}
            arcColor={d => d.color}
            arcDashLength={0.4}
            arcDashGap={0.2}
            arcDashAnimateTime={1500}
            arcStroke={0.6}

            // Points (Port locations) 
            pointsData={places.filter(p => p.type === 'port')}
            pointLat={d => d.lat}
            pointLng={d => d.lng}
            pointColor={() => '#22c55e'}
            pointAltitude={0.01}
            pointRadius={0.5}
        />
    );
};

export default GlobeComponent;
