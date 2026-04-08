import React from 'react';
import { RotateCcw, ChevronDown } from 'lucide-react';

function ScenarioSwitcher({
  plants,
  selectedPlantId,
  selectedPlant,
  scenarios,
  selectedScenarioId,
  selectedSupplierIds,
  batchTonnes,
  comparison,
  simulationPhase,
  maxSuppliers,
  onPlantChange,
  onSupplierToggle,
  onScenarioChange,
  onBatchChange,
  onReset,
  busy,
  currentStage
}) {
  const suppliersFromScenarios = React.useMemo(() => {
    if (!scenarios.length) return [];
    const seen = new Set();
    return scenarios
      .filter((s) => {
        if (seen.has(s.thingId)) return false;
        seen.add(s.thingId);
        return true;
      })
      .map((s) => ({
        thingId: s.thingId,
        label: s.label || s.thingId,
        supplierLabel: s.supplierLabel || s.label || s.thingId,
        scenarioId: s.scenarioId,
        iron_content_pct: s.iron_content_pct,
      }));
  }, [scenarios]);

  const isLocked = simulationPhase === 'running';

  return (
    <section className="twin-panel twin-scenario-panel">
      <div className="twin-panel-header">
        <div>
          <p className="twin-kicker">Simulation Setup</p>
          <h2>Step-by-Step Configuration</h2>
        </div>
        {simulationPhase === 'running' && (
          <button type="button" className="twin-reset-button" onClick={onReset} disabled={busy}>
            <RotateCcw size={14} /> Reset
          </button>
        )}
      </div>

      {/* Step 1: Plant Selection */}
      <div className="twin-setup-step">
        <div className="twin-step-header">
          <span className={`twin-step-number ${selectedPlantId ? 'is-complete' : 'is-active'}`}>1</span>
          <span className="twin-step-label">Select Steel Plant</span>
        </div>
        <div className="twin-plant-select-wrapper">
          <select
            className="twin-plant-select"
            value={selectedPlantId}
            onChange={(e) => onPlantChange(e.target.value)}
            disabled={isLocked}
          >
            <option value="">— Select a SAIL plant —</option>
            {plants.map((plant) => (
              <option key={plant.plantId} value={plant.plantId}>
                {plant.label}
              </option>
            ))}
          </select>
          <ChevronDown size={14} className="twin-select-icon" />
        </div>
      </div>

      {/* Step 2: Supplier Selection (visible only after plant is selected) */}
      {selectedPlantId && (
        <div className="twin-setup-step">
          <div className="twin-step-header">
            <span className={`twin-step-number ${selectedSupplierIds.length > 0 ? 'is-complete' : 'is-active'}`}>2</span>
            <span className="twin-step-label">
              Select Suppliers
              <span className="twin-step-counter">
                ({selectedSupplierIds.length} / {maxSuppliers})
              </span>
            </span>
          </div>
          <div className="twin-supplier-list">
            {suppliersFromScenarios.length === 0 ? (
              <p className="twin-empty">No supplier corridors for this plant.</p>
            ) : (
              suppliersFromScenarios.map((supplier) => {
                const isChecked = selectedSupplierIds.includes(supplier.thingId);
                const isDisabled = isLocked || (!isChecked && selectedSupplierIds.length >= maxSuppliers);
                return (
                  <label
                    key={supplier.thingId}
                    className={`twin-supplier-checkbox ${isChecked ? 'is-selected' : ''} ${isDisabled ? 'is-disabled' : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      disabled={isDisabled}
                      onChange={() => onSupplierToggle(supplier.thingId)}
                    />
                    <div className="twin-supplier-info">
                      <span className="twin-supplier-name">{supplier.supplierLabel}</span>
                      {supplier.iron_content_pct && (
                        <span className="twin-supplier-meta">
                          Fe {supplier.iron_content_pct}%
                        </span>
                      )}
                    </div>
                  </label>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Step 3: Batch size (visible when suppliers selected) */}
      {selectedSupplierIds.length > 0 && (
        <div className="twin-setup-step">
          <div className="twin-step-header">
            <span className={`twin-step-number ${simulationPhase === 'ready' || simulationPhase === 'running' ? 'is-complete' : 'is-active'}`}>3</span>
            <span className="twin-step-label">Batch Size</span>
          </div>
          <div className="twin-batch-row">
            <input
              type="range"
              className="twin-batch-slider"
              min={100}
              max={10000}
              step={100}
              value={batchTonnes}
              onChange={(e) => onBatchChange(Number(e.target.value))}
              disabled={isLocked}
            />
            <span className="twin-batch-value">{batchTonnes.toLocaleString()} t</span>
          </div>
        </div>
      )}

      {/* Comparison scores (visible when ready or running) */}
      {comparison && (simulationPhase === 'ready' || simulationPhase === 'running') && (
        <div className="twin-comparison-box">
          <p className="twin-kicker">Scenario Comparison</p>
          <div className="twin-comparison-grid">
            {(comparison.results || []).slice(0, 3).map((result) => (
              <div
                key={result.scenarioId}
                className={`twin-comparison-card ${result.scenarioId === selectedScenarioId ? 'is-selected' : ''}`}
              >
                <span className="twin-comparison-label">{result.supplierLabel || result.scenarioId}</span>
                <span className="twin-comparison-value">{Number(result.totalTco2).toFixed(2)} tCO₂</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Status bar */}
      {simulationPhase === 'running' && (
        <div className="twin-run-status">
          <span className="twin-run-dot" />
          <span className="twin-run-label">{currentStage}</span>
        </div>
      )}
    </section>
  );
}

export default ScenarioSwitcher;
