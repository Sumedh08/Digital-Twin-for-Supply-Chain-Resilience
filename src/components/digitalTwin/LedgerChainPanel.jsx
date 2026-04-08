import React from 'react';

function shorten(hash) {
  if (!hash) return 'GENESIS';
  if (hash === 'GENESIS') return hash;
  return `${hash.slice(0, 10)}...${hash.slice(-8)}`;
}

function LedgerChainPanel({ ledger, evidenceBundle, selectedPlant, selectedScenario }) {
  const blocks = ledger?.blocks || [];
  const totalCheckpointEmission = blocks.reduce((sum, block) => sum + Number(block.emission || 0), 0);

  return (
    <section className="twin-panel">
      <div className="twin-panel-header">
        <div>
          <p className="twin-kicker">Audit Ledger</p>
          <h2>Authority-ready checkpoint trail</h2>
        </div>
        <div className={`twin-status-badge ${ledger?.isValid ? 'is-valid' : 'is-invalid'}`}>
          <span>{ledger?.isValid ? 'Hash valid' : 'Check failed'}</span>
        </div>
      </div>

      <div className="twin-ledger-summary">
        <div className="twin-summary-chip">
          <span className="twin-inline-label">Blocks</span>
          <strong>{ledger?.chainLength || 0}</strong>
        </div>
        <div className="twin-summary-chip">
          <span className="twin-inline-label">Checkpoint CO2</span>
          <strong>{totalCheckpointEmission.toFixed(2)} tCO2</strong>
        </div>
        <div className="twin-summary-chip">
          <span className="twin-inline-label">Backend</span>
          <strong>{ledger?.target || ledger?.id || 'Awaiting run'}</strong>
        </div>
      </div>

      <div className="twin-comparison-summary">
        <div>
          <span className="twin-inline-label">Plant</span>
          <strong>{selectedPlant?.label || ledger?.plantId || 'Select a plant'}</strong>
        </div>
        <div>
          <span className="twin-inline-label">Supplier</span>
          <strong>{selectedScenario?.label || ledger?.scenarioId || 'Choose a supplier corridor'}</strong>
        </div>
        <div>
          <span className="twin-inline-label">Phase</span>
          <strong>{ledger?.phase || 'phase_1'}</strong>
        </div>
      </div>

      {evidenceBundle && (
        <div className="twin-ledger-evidence">
          <div className="twin-ledger-evidence-top">
            <strong>Evidence bundle ready</strong>
            <span>{evidenceBundle.recordType}</span>
          </div>
          <div className="twin-ledger-evidence-grid">
            <span>Final emissions: {Number(evidenceBundle.finalEmissions?.total_tco2 || 0).toFixed(2)} tCO2</span>
            <span>Ledger refs: {evidenceBundle.ledgerReferences?.length || 0}</span>
            <span>Emission checkpoints: {evidenceBundle.emissionCheckpoints?.length || 0}</span>
            <span>Verification: {evidenceBundle.verification?.isValid ? 'valid' : 'invalid'}</span>
          </div>
        </div>
      )}

      <p className="twin-ledger-note">
        Carbon checkpoints and world-state digests are chained for the real-time simulation.
        {ledger?.target === 'hyperledger_fabric' ? (
          <span style={{ color: '#8fedb8', marginLeft: 6 }}>
            ✓ Blockchain verified via Hyperledger Fabric Test Network.
          </span>
        ) : (
          <span style={{ marginLeft: 6 }}>
            Local fallback audit chain active (Fabric offline).
          </span>
        )}
      </p>

      <div className="twin-ledger-list">
        {blocks.length > 0 ? (
          blocks.map((block) => (
            <article key={block.index} className="twin-ledger-block">
              <div className="twin-ledger-top">
                <strong>#{block.index} {block.stage}</strong>
                <span>{Number(block.emission).toFixed(2)} tCO2</span>
              </div>
              <div className="twin-ledger-meta">
                <span>{block.thingId}</span>
                <span>{block.timestamp}</span>
                <span style={{ color: block.txId?.startsWith('fabric:') ? '#8fedb8' : '#ffd59a' }}>
                  {block.txId || 'pending tx'}
                </span>
              </div>
              <div className="twin-hash-stack">
                <span>prev: {shorten(block.previousHash)}</span>
                <span>hash: {shorten(block.currentHash)}</span>
              </div>

              <div className="twin-ledger-breakdown">
                <span className="twin-inline-label">Event</span>
                <strong>{block.payload?.eventType || 'checkpoint'}</strong>
                <span>Plant: {block.payload?.plantId || ledger?.plantId || 'n/a'}</span>
                <span>Supplier: {block.payload?.supplierId || 'n/a'}</span>
                <span>World state digest: {shorten(block.worldStateDigest)}</span>
                {block.payload?.selectedSupplier && (
                  <span>Selected supplier: {block.payload.selectedSupplier}</span>
                )}
                {block.payload?.emission && (
                  <div className="twin-ledger-scope-grid">
                    <span>Scope 1: {Number(block.payload.emission.scope_1_tco2 || 0).toFixed(2)} tCO2</span>
                    <span>Scope 2: {Number(block.payload.emission.scope_2_tco2 || 0).toFixed(2)} tCO2</span>
                    <span>Scope 3: {Number(block.payload.emission.scope_3_tco2 || 0).toFixed(2)} tCO2</span>
                    <span>Total: {Number(block.payload.emission.total_tco2 || 0).toFixed(2)} tCO2</span>
                  </div>
                )}
              </div>
            </article>
          ))
        ) : (
          <p className="twin-empty">Run a scenario to materialize the ledger from planning through port delivery.</p>
        )}
      </div>
    </section>
  );
}

export default LedgerChainPanel;
