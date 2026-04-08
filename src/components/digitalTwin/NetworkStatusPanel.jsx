import React, { useEffect, useState } from 'react';
import { Activity, Shield, Server, CheckCircle2, AlertCircle } from 'lucide-react';
import { API_BASE } from '../../config';

async function fetchStatus() {
  const response = await fetch(`${API_BASE}/india-steel-twin/system/network-status`);
  const payload = await response.json();
  return payload.data;
}

function NetworkStatusPanel() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let timer;
    async function update() {
      try {
        const data = await fetchStatus();
        setStatus(data);
      } catch (err) {
        console.error('Failed to fetch network status', err);
      } finally {
        setLoading(false);
      }
      timer = setTimeout(update, 5000);
    }
    update();
    return () => clearTimeout(timer);
  }, []);

  if (loading && !status) return <div className="twin-panel twin-loading">Loading network status...</div>;

  const isFabric = status?.target === 'hyperledger_fabric';
  const containerCount = status?.count || 0;

  return (
    <section className="twin-panel twin-network-status-panel">
      <div className="twin-panel-header">
        <div>
          <p className="twin-kicker">Infrastructure</p>
          <h2>Blockchain Network Status</h2>
        </div>
        {isFabric ? (
          <span className="twin-status-tag is-online">
            <Activity size={12} /> Fabric Live
          </span>
        ) : (
          <span className="twin-status-tag is-offline">
            <Shield size={12} /> Local Fallback
          </span>
        )}
      </div>

      <div className="twin-network-metrics">
        <div className="twin-metric-item">
          <Server size={14} className="twin-metric-icon" />
          <div className="twin-metric-content">
            <span className="twin-metric-label">Nodes Up</span>
            <span className="twin-metric-value">{containerCount}</span>
          </div>
        </div>
        <div className="twin-metric-item">
          <CheckCircle2 size={14} className="twin-metric-icon" />
          <div className="twin-metric-content">
            <span className="twin-metric-label">Identity Service</span>
            <span className="twin-metric-value">{isFabric ? 'Active (CA)' : 'Mock'}</span>
          </div>
        </div>
      </div>

      <div className="twin-container-list">
        {status?.containers && status.containers.length > 0 ? (
          status.containers.map((container, idx) => {
            const [name, state] = container.split(': ');
            return (
              <div key={idx} className="twin-container-item">
                <div className="twin-container-name">{name}</div>
                <div className="twin-container-state">{state}</div>
              </div>
            );
          })
        ) : (
          <div className="twin-network-empty">
            <AlertCircle size={16} />
            <p>
              {isFabric 
                ? 'Network nodes are starting up...' 
                : 'Using LocalAuditLedgerBackend for development. Real Fabric network is offline.'}
            </p>
          </div>
        )}
      </div>
      
      <div className="twin-network-footer">
        <p>Verified via Docker CLI engine</p>
      </div>
    </section>
  );
}

export default NetworkStatusPanel;
