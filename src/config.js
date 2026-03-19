/**
 * Config for CarbonShip Frontend
 */

const getApiBase = () => {
    // Determine the environment
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    
    // If we're on a local network or localhost, connect to port 8000 on the same host
    const isLocal = hostname === 'localhost' || 
                    hostname === '127.0.0.1' || 
                    hostname.startsWith('192.168.') || 
                    hostname.startsWith('10.') || 
                    hostname.endsWith('.local');
    
    if (isLocal) {
        // Use the same hostname but port 8000
        return `${protocol}//${hostname}:8000`;
    }

    // Otherwise, assume the API is on the same host but maybe a different port/subdomain
    // Or fallback to a known production URL if one exists.
    return import.meta.env.VITE_API_URL || 'https://digital-twin-for-supply-chain-resilience.onrender.com';
};

export const API_BASE = getApiBase();
