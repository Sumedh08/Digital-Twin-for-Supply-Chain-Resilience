import React from 'react';
import { Factory, MapPinned, ShipWheel, Truck, Trees } from 'lucide-react';

const GROUPS = [
  { key: 'suppliers', label: 'Suppliers', icon: Trees },
  { key: 'plant', label: 'Plant', icon: Factory },
  { key: 'transportUnits', label: 'Transport Fleet', icon: Truck },
  { key: 'port', label: 'Port', icon: ShipWheel }
];

const formatEmission = (value) => `${(value || 0).toFixed(2)} tCO2`;

function TwinRegistryPanel({ worldState, selectedThingId, onSelectThing, selectedPlantLabel }) {
  const byType = worldState?.byType || {};

  const renderCard = (thing) => {
    const lifecycle = thing.features.lifecycle.properties.current;
    const emission = thing.features.emission.properties.current;
    const currentLocation = thing.features.location.properties.current;

    return (
      <button
        type="button"
        key={thing.thingId}
        className={`twin-thing-card ${selectedThingId === thing.thingId ? 'is-active' : ''}`}
        onClick={() => onSelectThing(thing.thingId)}
      >
        <div className="twin-thing-card-top">
          <strong>{thing.attributes.name}</strong>
          <span className="twin-revision-pill">r{thing.revision}</span>
        </div>
        <div className="twin-thing-card-meta">
          <span>{thing.thingId}</span>
          <span>{lifecycle.state}</span>
        </div>
        <div className="twin-thing-card-bottom">
          <span>{formatEmission(emission.total_tco2)}</span>
          <span className="twin-card-location">
            <MapPinned size={12} />
            {Number(currentLocation.lat).toFixed(2)}, {Number(currentLocation.lon).toFixed(2)}
          </span>
        </div>
      </button>
    );
  };

  return (
    <section className="twin-panel twin-registry-panel">
      <div className="twin-panel-header">
        <div>
          <p className="twin-kicker">Twin Network</p>
          <h2>{selectedPlantLabel ? `${selectedPlantLabel} active assets` : 'Select a plant to inspect twins'}</h2>
        </div>
      </div>

      <div className="twin-registry-groups">
        {GROUPS.map(({ key, label, icon: Icon }) => {
          const value = byType[key];
          const list = Array.isArray(value) ? value : value ? [value] : [];

          return (
            <section key={key} className="twin-registry-group">
              <div className="twin-registry-group-title">
                <span className="twin-group-icon"><Icon size={14} /></span>
                <h3>{label}</h3>
                <span className="twin-group-count">{list.length}</span>
              </div>
              <div className="twin-registry-group-list">
                {list.length > 0 ? (
                  list.map(renderCard)
                ) : (
                  <p className="twin-empty">
                    {selectedPlantLabel
                      ? 'Run or step the selected corridor to materialize this twin group.'
                      : 'Choose a plant and start a run to populate this registry.'}
                  </p>
                )}
              </div>
            </section>
          );
        })}
      </div>
    </section>
  );
}

export default TwinRegistryPanel;
