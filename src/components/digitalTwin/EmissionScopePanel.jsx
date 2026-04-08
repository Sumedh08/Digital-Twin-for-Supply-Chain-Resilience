import React from 'react';
import { Bolt, Factory, Leaf } from 'lucide-react';

const CARDS = [
  { key: 'scope_1_tco2', label: 'Scope 1', note: 'Process fuel + plant handling', icon: Factory },
  { key: 'scope_2_tco2', label: 'Scope 2', note: 'Grid electricity', icon: Bolt },
  { key: 'scope_3_tco2', label: 'Scope 3', note: 'Supplier and logistics', icon: Leaf }
];

function EmissionScopePanel({
  aggregatedEmissions,
  comparison,
  selectedScenarioId,
  selectedPlant,
  selectedScenario,
  ledgerBackend
}) {
  const rankedScenario = comparison?.rankedScenarios?.find(
    (scenario) => scenario.scenarioId === selectedScenarioId
  );

  return (
    <section className="twin-panel">
      <div className="twin-panel-header">
        <div>
          <p className="twin-kicker">Emission Snapshot</p>
          <h2>Scope contribution</h2>
        </div>
        <div className="twin-total-card">
          <span>Total</span>
          <strong>{(aggregatedEmissions?.total_tco2 || 0).toFixed(2)} tCO2</strong>
        </div>
      </div>

      <div className="twin-scope-grid">
        {CARDS.map(({ key, label, note, icon: Icon }) => (
          <article key={key} className="twin-scope-card">
            <div className="twin-scope-card-title">
              <span className="twin-group-icon"><Icon size={14} /></span>
              <h3>{label}</h3>
            </div>
            <strong>{(aggregatedEmissions?.[key] || 0).toFixed(2)} tCO2</strong>
            <p>{note}</p>
          </article>
        ))}
      </div>

      {(selectedPlant || selectedScenario || ledgerBackend) && (
        <div className="twin-comparison-summary">
          <div>
            <span className="twin-inline-label">Plant</span>
            <strong>{selectedPlant?.label || 'Select a SAIL plant'}</strong>
          </div>
          <div>
            <span className="twin-inline-label">Supplier</span>
            <strong>{selectedScenario?.label || 'Choose a supplier corridor'}</strong>
          </div>
          <div>
            <span className="twin-inline-label">Ledger backend</span>
            <strong>
              {ledgerBackend?.target === 'hyperledger_fabric' ? (
                <span style={{ color: '#8fedb8' }}>✓ Blockchain verified</span>
              ) : (
                ledgerBackend?.target || 'Awaiting run'
              )}
            </strong>
          </div>
        </div>
      )}

      {rankedScenario && (
        <div className="twin-benchmark-grid">
          <div className="twin-summary-chip">
            <span className="twin-inline-label">Scenario intensity</span>
            <strong>{rankedScenario.intensityTco2PerTonne.toFixed(3)} tCO2/t HRC</strong>
          </div>
          <div className="twin-summary-chip">
            <span className="twin-inline-label">Best-case savings</span>
            <strong>{comparison?.deltaAnalysis?.absoluteSavingsTco2?.toFixed(2) || '0.00'} tCO2</strong>
          </div>
          <div className="twin-summary-chip">
            <span className="twin-inline-label">India reference</span>
            <strong>{comparison?.benchmarks?.indiaCrudeSteelReferenceTco2PerTonne?.toFixed?.(2) || '0.00'} tCO2/t</strong>
          </div>
        </div>
      )}
    </section>
  );
}

export default EmissionScopePanel;
