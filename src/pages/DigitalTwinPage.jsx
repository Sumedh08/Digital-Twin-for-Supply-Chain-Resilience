import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, LoaderCircle } from 'lucide-react';
import { API_BASE } from '../config';
import ScenarioSwitcher from '../components/digitalTwin/ScenarioSwitcher';
import TwinRegistryPanel from '../components/digitalTwin/TwinRegistryPanel';
import TwinInspectorDrawer from '../components/digitalTwin/TwinInspectorDrawer';
import EmissionScopePanel from '../components/digitalTwin/EmissionScopePanel';
import LedgerChainPanel from '../components/digitalTwin/LedgerChainPanel';
import TransitionTimeline from '../components/digitalTwin/TransitionTimeline';
import DigitalTwinGlobe from '../components/digitalTwin/DigitalTwinGlobe';
import NetworkStatusPanel from '../components/digitalTwin/NetworkStatusPanel';
import './digitalTwin.css';

const MAX_SUPPLIERS = 5;

function buildQuery(path, params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    search.set(key, value);
  });
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

async function api(path, options) {
  const response = await fetch(`${API_BASE}${path}`, options);
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`Request to ${path} returned an invalid response.`);
  }
  if (!response.ok || payload.success === false) {
    throw new Error(payload.detail || payload.message || 'API request failed');
  }
  return payload.data ?? payload;
}

function aggregateEmissions(worldState) {
  const totals = { scope_1_tco2: 0, scope_2_tco2: 0, scope_3_tco2: 0, total_tco2: 0 };
  (worldState?.things || []).forEach((thing) => {
    const emission = thing.features?.emission?.properties?.current || {};
    totals.scope_1_tco2 += Number(emission.scope_1_tco2 || 0);
    totals.scope_2_tco2 += Number(emission.scope_2_tco2 || 0);
    totals.scope_3_tco2 += Number(emission.scope_3_tco2 || 0);
    totals.total_tco2 += Number(emission.total_tco2 || 0);
  });
  return Object.fromEntries(
    Object.entries(totals).map(([key, value]) => [key, Number(value.toFixed(4))])
  );
}

function normalizeRunData(payload, scenarioId, supplierThingId, batchTonnes) {
  return {
    correlationId: payload.correlationId,
    plantId: payload.plantId,
    scenarioId: payload.scenarioId || scenarioId,
    supplierThingId: payload.supplierThingId || supplierThingId,
    batchTonnes: payload.batchTonnes || batchTonnes,
    completed: Boolean(payload.completed),
    systemState: payload.systemState,
    ledger: payload.ledger,
    events: payload.events || [],
    spatialOverlay: payload.spatialOverlay,
    ledgerBackend: payload.ledgerBackend
  };
}

function DigitalTwinPage() {
  // --- Core state ---
  const [simulationPhase, setSimulationPhase] = useState('initial');
  const [context, setContext] = useState(null);
  const [plants, setPlants] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [previewOverlay, setPreviewOverlay] = useState(null);
  const [selectedPlantId, setSelectedPlantId] = useState('');
  const [selectedSupplierIds, setSelectedSupplierIds] = useState([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState('');
  const [batchTonnes, setBatchTonnes] = useState(1000);
  const [runData, setRunData] = useState(null);
  const [evidenceBundle, setEvidenceBundle] = useState(null);
  const [selectedThingId, setSelectedThingId] = useState('');
  const [replayIndex, setReplayIndex] = useState(0);
  const [stepCorrelationId, setStepCorrelationId] = useState('');
  const [busy, setBusy] = useState(false);
  const [booting, setBooting] = useState(true);
  const [error, setError] = useState('');

  const selectedPlant = useMemo(
    () => plants.find((plant) => plant.plantId === selectedPlantId) || null,
    [plants, selectedPlantId]
  );

  // --- PHASE: initial load (just JNPT + plant list) ---
  useEffect(() => {
    let cancelled = false;
    async function boot() {
      setError('');
      try {
        const [contextData, plantsData, overlayData] = await Promise.all([
          api('/india-steel-twin/context'),
          api('/india-steel-twin/plants'),
          api('/india-steel-twin/spatial-overlay'),
        ]);
        if (cancelled) return;
        setContext(contextData);
        setPlants(Array.isArray(plantsData) ? plantsData : []);
        setPreviewOverlay(overlayData);
      } catch (loadError) {
        if (!cancelled) setError(loadError.message);
      } finally {
        if (!cancelled) setBooting(false);
      }
    }
    boot();
    return () => { cancelled = true; };
  }, []);

  // --- PHASE: plant-selected → load scenarios + overlay with plant ---
  useEffect(() => {
    if (!selectedPlantId) {
      setSimulationPhase('initial');
      return;
    }

    let cancelled = false;
    async function loadPlantData() {
      setError('');
      try {
        const supplierIdsParam = selectedSupplierIds.length > 0
          ? selectedSupplierIds.join(',')
          : undefined;

        const [contextData, scenarioData, overlayData, comparisonData] = await Promise.all([
          api(buildQuery('/india-steel-twin/context', { plantId: selectedPlantId })),
          api(buildQuery('/india-steel-twin/scenarios', { plantId: selectedPlantId })),
          api(buildQuery('/india-steel-twin/spatial-overlay', {
            plantId: selectedPlantId,
            supplierIds: supplierIdsParam
          })),
          api('/india-steel-twin/compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plantId: selectedPlantId, batchTonnes })
          }),
        ]);
        if (cancelled) return;
        setContext(contextData);
        setScenarios(Array.isArray(scenarioData) ? scenarioData : []);
        setPreviewOverlay(overlayData);
        setComparison(comparisonData);

        // Update phase based on supplier selection
        if (selectedSupplierIds.length > 0) {
          setSimulationPhase('ready');
        } else {
          setSimulationPhase('plant-selected');
        }
      } catch (loadError) {
        if (!cancelled) setError(loadError.message);
      }
    }
    loadPlantData();
    return () => { cancelled = true; };
  }, [selectedPlantId, selectedSupplierIds, batchTonnes]);

  // --- Reset when plant changes ---
  const handlePlantChange = useCallback((plantId) => {
    // Clear everything from previous selection
    setSelectedSupplierIds([]);
    setSelectedScenarioId('');
    setRunData(null);
    setEvidenceBundle(null);
    setReplayIndex(0);
    setStepCorrelationId('');
    setError('');
    setSelectedPlantId(plantId);
    if (!plantId) {
      setSimulationPhase('initial');
    } else {
      setSimulationPhase('plant-selected');
    }
  }, []);

  // --- Supplier multi-select (max 5) ---
  const handleSupplierToggle = useCallback((supplierId) => {
    if (simulationPhase === 'running') return; // can't change during simulation
    setSelectedSupplierIds((prev) => {
      if (prev.includes(supplierId)) {
        const next = prev.filter((id) => id !== supplierId);
        return next;
      }
      if (prev.length >= MAX_SUPPLIERS) return prev;
      return [...prev, supplierId];
    });
  }, [simulationPhase]);

  // Update phase when suppliers change
  useEffect(() => {
    if (simulationPhase === 'running') return;
    if (!selectedPlantId) return;
    if (selectedSupplierIds.length > 0) {
      setSimulationPhase('ready');
    } else {
      setSimulationPhase('plant-selected');
    }
  }, [selectedSupplierIds, selectedPlantId]);

  // Keep selectedScenarioId in sync with first selected supplier's scenario
  useEffect(() => {
    if (selectedSupplierIds.length > 0 && scenarios.length > 0) {
      const match = scenarios.find((s) => selectedSupplierIds.includes(s.thingId));
      if (match) setSelectedScenarioId(match.scenarioId);
    } else {
      setSelectedScenarioId('');
    }
  }, [selectedSupplierIds, scenarios]);

  const selectedScenario = useMemo(
    () => scenarios.find((s) => s.scenarioId === selectedScenarioId) || null,
    [scenarios, selectedScenarioId]
  );

  // --- Replay frame ---
  const replayFrame = useMemo(() => {
    if (!runData) {
      return {
        worldState: null,
        aggregatedEmissions: null,
        activeStage: previewOverlay?.activeStage || 'Initial',
        overlay: previewOverlay
      };
    }
    const events = runData.events || [];
    const boundedIndex = Math.min(replayIndex, Math.max(events.length - 1, 0));
    const event = events[boundedIndex] || null;
    const worldState = event?.payload?.worldStateSnapshot || runData.systemState?.worldState || null;
    const aggregatedEmissions = worldState ? aggregateEmissions(worldState) : runData.systemState?.aggregatedEmissions;
    const activeStage = event?.event_type || runData.systemState?.currentStage || runData.spatialOverlay?.activeStage;
    return { worldState, aggregatedEmissions, activeStage, overlay: runData.spatialOverlay || previewOverlay };
  }, [previewOverlay, replayIndex, runData]);

  const currentStageLabel = replayFrame.activeStage || 'Initial';
  const worldThings = replayFrame.worldState?.things || runData?.systemState?.worldState?.things || [];
  const eventCount = (runData?.events || []).length;
  const chainLength = runData?.ledger?.chainLength || 0;
  const twinCount =
    worldThings.length ||
    ((replayFrame.overlay?.nodes?.length || 0) + (replayFrame.overlay?.trucks?.length || 0));

  const selectedTwin = useMemo(() => {
    const things = replayFrame.worldState?.things || runData?.systemState?.worldState?.things || [];
    return things.find((thing) => thing.thingId === selectedThingId) || null;
  }, [replayFrame.worldState, runData, selectedThingId]);

  // --- Evidence bundle ---
  useEffect(() => {
    if (!runData?.correlationId) {
      setEvidenceBundle(null);
      return;
    }
    let cancelled = false;
    async function loadEvidence() {
      try {
        const evidenceData = await api(`/india-steel-twin/evidence/${runData.correlationId}`);
        if (!cancelled) setEvidenceBundle(evidenceData.evidenceBundle || null);
      } catch {
        if (!cancelled) setEvidenceBundle(null);
      }
    }
    loadEvidence();
    return () => { cancelled = true; };
  }, [runData?.correlationId]);

  // --- Start Simulation (transition from ready → running + execute scenario) ---
  const startSimulation = useCallback(async () => {
    if (simulationPhase !== 'ready' || !selectedPlantId || !selectedScenario) return;
    if (busy) return; // prevent double-click
    setBusy(true);
    setError('');
    setSimulationPhase('running');
    try {
      const data = await api('/india-steel-twin/scenarios/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plantId: selectedPlantId,
          scenarioId: selectedScenario.scenarioId,
          supplierThingId: selectedScenario.thingId,
          batchTonnes
        })
      });
      const normalized = normalizeRunData(data, selectedScenario.scenarioId, selectedScenario.thingId, batchTonnes);
      setRunData(normalized);
      setReplayIndex(Math.max((normalized.events || []).length - 1, 0));
      setStepCorrelationId(normalized.correlationId);
    } catch (runError) {
      setError(runError.message);
      setSimulationPhase('ready');
    } finally {
      setBusy(false);
    }
  }, [simulationPhase, selectedPlantId, selectedScenario, batchTonnes, busy]);

  // --- Step forward (only in running phase) ---
  const stepForward = useCallback(async () => {
    if ((simulationPhase !== 'running' && simulationPhase !== 'ready') || !selectedPlantId || !selectedScenario) return;
    if (busy) return;
    setBusy(true);
    setSimulationPhase('running');
    setError('');
    try {
      const correlationId = stepCorrelationId || `interactive-${Date.now()}`;
      const data = await api('/india-steel-twin/transitions/advance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          correlationId,
          plantId: selectedPlantId,
          sourceThingId: selectedScenario.thingId,
          batchTonnes
        })
      });
      const normalized = normalizeRunData(data, selectedScenario.scenarioId, selectedScenario.thingId, batchTonnes);
      setRunData(normalized);
      setReplayIndex(Math.max((normalized.events || []).length - 1, 0));
      setStepCorrelationId(correlationId);
    } catch (runError) {
      setError(runError.message);
    } finally {
      setBusy(false);
    }
  }, [simulationPhase, selectedPlantId, selectedScenario, batchTonnes, busy, stepCorrelationId]);

  // --- Execute all (only in running phase) ---
  const executeScenario = useCallback(async () => {
    if ((simulationPhase !== 'running' && simulationPhase !== 'ready') || !selectedPlantId || !selectedScenario) return;
    if (busy) return;
    setBusy(true);
    setSimulationPhase('running');
    setError('');
    try {
      const data = await api('/india-steel-twin/scenarios/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plantId: selectedPlantId,
          scenarioId: selectedScenario.scenarioId,
          supplierThingId: selectedScenario.thingId,
          batchTonnes
        })
      });
      const normalized = normalizeRunData(data, selectedScenario.scenarioId, selectedScenario.thingId, batchTonnes);
      setRunData(normalized);
      setReplayIndex(Math.max((normalized.events || []).length - 1, 0));
      setStepCorrelationId(normalized.correlationId);
    } catch (runError) {
      setError(runError.message);
    } finally {
      setBusy(false);
    }
  }, [simulationPhase, selectedPlantId, selectedScenario, batchTonnes, busy]);

  // --- Reset view ---
  const resetView = useCallback(() => {
    setRunData(null);
    setEvidenceBundle(null);
    setReplayIndex(0);
    setStepCorrelationId('');
    setError('');
    if (selectedPlantId) {
      setSimulationPhase(selectedSupplierIds.length > 0 ? 'ready' : 'plant-selected');
    } else {
      setSimulationPhase('initial');
    }
  }, [selectedPlantId, selectedSupplierIds]);

  // --- Loading screen ---
  if (booting) {
    return (
      <div className="twin-loading-screen">
        <LoaderCircle className="twin-spinner" size={32} />
        <div>
          <h1>Bootstrapping SAIL digital twin</h1>
          <p>Loading plant registry and JNPT Mumbai port.</p>
        </div>
      </div>
    );
  }

  const phaseLabel = {
    'initial': 'Select a SAIL steel plant to begin',
    'plant-selected': 'Select suppliers to activate corridors',
    'suppliers-selected': 'Suppliers selected — ready to simulate',
    'ready': 'Ready — click Start Simulation',
    'running': currentStageLabel
  }[simulationPhase] || 'Initial';

  return (
    <div className="twin-shell">
      <div className="twin-page-frame">
        <header className="twin-hero">
          <div className="twin-hero-left">
            <Link to="/" className="twin-back-link">
              <ArrowLeft size={16} />
              CarbonShip home
            </Link>
            <div className="twin-title-block">
              <p className="twin-kicker">SAIL Digital Twin</p>
              <h1>{context?.title || 'SAIL Multi-Plant Steel Digital Twin'}</h1>
              <p>{phaseLabel}</p>
            </div>
          </div>

          <div className="twin-framework-badges">
            <span>{selectedPlant?.shortLabel || 'No plant selected'}</span>
            <span>{selectedSupplierIds.length} / {MAX_SUPPLIERS} suppliers</span>
            <span>{context?.ledgerBackend?.target || 'hyperledger_fabric'}</span>
            <span className={`twin-phase-badge twin-phase-${simulationPhase}`}>
              {simulationPhase.replace('-', ' ')}
            </span>
          </div>
        </header>

        {error && <div className="twin-error-banner">{error}</div>}

        <section className="twin-stage-shell">
          <div className="twin-stage-main">
            <section className="twin-panel twin-spatial-panel twin-spatial-panel-hero">
              <div className="twin-stage-toolbar">
                <div className="twin-state-readout">
                  <p className="twin-kicker">Current State</p>
                  <h2>{phaseLabel}</h2>
                  <p>
                    {selectedScenario?.label ||
                      selectedPlant?.label ||
                      'JNPT Mumbai — select a plant to begin'}
                  </p>
                </div>
                <div className="twin-stage-actions">
                  {(simulationPhase === 'ready' || simulationPhase === 'running') && (
                    <div className="twin-action-group">
                      <button
                        type="button"
                        className="twin-secondary-button"
                        onClick={stepForward}
                        disabled={busy || !selectedPlantId || selectedSupplierIds.length === 0}
                      >
                        {busy ? <LoaderCircle className="twin-btn-spinner" size={14} /> : 'Run Next'}
                      </button>
                      <button
                        type="button"
                        className="twin-primary-button"
                        onClick={executeScenario}
                        disabled={busy || !selectedPlantId || selectedSupplierIds.length === 0}
                      >
                        {busy ? <LoaderCircle className="twin-btn-spinner" size={14} /> : 'Run All'}
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <DigitalTwinGlobe
                overlay={replayFrame.overlay || runData?.spatialOverlay || previewOverlay}
                selectedThingId={selectedThingId}
                onSelectThing={setSelectedThingId}
              />

              <div className="twin-stage-summary">
                <div className="twin-summary-chip">
                  <span className="twin-inline-label">Plant</span>
                  <strong>{selectedPlant?.label || 'None selected'}</strong>
                </div>
                <div className="twin-summary-chip">
                  <span className="twin-inline-label">Suppliers</span>
                  <strong>{selectedSupplierIds.length > 0 ? `${selectedSupplierIds.length} selected` : 'None'}</strong>
                </div>
                <div className="twin-summary-chip">
                  <span className="twin-inline-label">Port</span>
                  <strong>JNPT Mumbai</strong>
                </div>
                <div className="twin-summary-chip">
                  <span className="twin-inline-label">Batch</span>
                  <strong>{batchTonnes.toLocaleString()} t HRC</strong>
                </div>
                <div className="twin-summary-chip">
                  <span className="twin-inline-label">Phase</span>
                  <strong>{simulationPhase.replace('-', ' ')}</strong>
                </div>
                <div className="twin-summary-chip">
                  <span className="twin-inline-label">Ledger Blocks</span>
                  <strong>{chainLength}</strong>
                </div>
              </div>
            </section>

            <TransitionTimeline
              events={runData?.events || []}
              replayIndex={Math.min(replayIndex, Math.max((runData?.events || []).length - 1, 0))}
              onReplayChange={setReplayIndex}
            />
          </div>

          <aside className="twin-stage-sidebar">
            <ScenarioSwitcher
              plants={plants}
              selectedPlantId={selectedPlantId}
              selectedPlant={selectedPlant}
              scenarios={scenarios}
              selectedScenarioId={selectedScenarioId}
              selectedSupplierIds={selectedSupplierIds}
              batchTonnes={batchTonnes}
              comparison={comparison}
              simulationPhase={simulationPhase}
              maxSuppliers={MAX_SUPPLIERS}
              onPlantChange={handlePlantChange}
              onSupplierToggle={handleSupplierToggle}
              onScenarioChange={setSelectedScenarioId}
              onBatchChange={setBatchTonnes}
              onReset={resetView}
              busy={busy}
              currentStage={currentStageLabel}
            />
            <EmissionScopePanel
              aggregatedEmissions={replayFrame.aggregatedEmissions || runData?.systemState?.aggregatedEmissions}
              comparison={comparison}
              selectedScenarioId={selectedScenarioId}
              selectedPlant={selectedPlant}
              selectedScenario={selectedScenario}
              ledgerBackend={runData?.ledgerBackend || context?.ledgerBackend}
            />
            <NetworkStatusPanel />
          </aside>
        </section>

        <div className="twin-secondary-grid">
          <LedgerChainPanel
            ledger={runData?.ledger}
            evidenceBundle={evidenceBundle}
            selectedPlant={selectedPlant}
            selectedScenario={selectedScenario}
          />

          <section className="twin-panel">
            <div className="twin-panel-header">
              <div>
                <p className="twin-kicker">Event Feed</p>
                <h2>Persisted transition history</h2>
              </div>
            </div>
            <div className="twin-event-feed">
              {(runData?.events || []).length > 0 ? (
                runData.events.map((event) => (
                  <article key={event.event_id} className={`twin-event-card ${event.event_id === runData.events[replayIndex]?.event_id ? 'is-active' : ''}`}>
                    <div className="twin-event-card-top">
                      <strong>{event.event_type}</strong>
                      <span>{event.created_at}</span>
                    </div>
                    <p>{event.stage}</p>
                    <div className="twin-event-card-bottom">
                      <span>{event.thing_id}</span>
                      <span>{event.from_state} to {event.to_state}</span>
                    </div>
                  </article>
                ))
              ) : (
                <p className="twin-empty">
                  {simulationPhase === 'initial'
                    ? 'Select a plant, then suppliers, then start the simulation to watch transitions.'
                    : simulationPhase === 'running'
                    ? 'Simulation is running — events will appear as stages complete.'
                    : 'Select suppliers and start the simulation to watch the transition history build.'}
                </p>
              )}
            </div>
          </section>

          <TwinRegistryPanel
            worldState={replayFrame.worldState || runData?.systemState?.worldState}
            selectedThingId={selectedThingId}
            onSelectThing={setSelectedThingId}
            selectedPlantLabel={selectedPlant?.shortLabel || selectedPlant?.label || ''}
          />
          <TwinInspectorDrawer twin={selectedTwin} />
        </div>
      </div>
    </div>
  );
}

export default DigitalTwinPage;
