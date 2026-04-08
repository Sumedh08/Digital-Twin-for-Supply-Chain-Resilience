import React from 'react';

function JsonBlock({ title, data }) {
  return (
    <div className="twin-json-block">
      <div className="twin-json-title">{title}</div>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}

function TwinInspectorDrawer({ twin }) {
  if (!twin) {
    return (
      <section className="twin-panel twin-inspector-panel">
        <div className="twin-panel-header">
          <div>
            <p className="twin-kicker">Twin Details</p>
            <h2>Select an asset to inspect its state</h2>
          </div>
        </div>
        <p className="twin-empty">Select a twin to inspect its full contract and state layers.</p>
      </section>
    );
  }

  const featureNames = Object.keys(twin.features || {});

  return (
    <section className="twin-panel twin-inspector-panel">
      <div className="twin-panel-header">
        <div>
          <p className="twin-kicker">Twin Details</p>
          <h2>{twin.attributes.name}</h2>
        </div>
        <div className="twin-status-badge">
          <span>{twin.metadata.entityType}</span>
        </div>
      </div>

      <div className="twin-inspector-meta">
        <span>{twin.thingId}</span>
        <span>{twin.definition}</span>
        <span>Revision {twin.revision}</span>
      </div>

      <JsonBlock title="Attributes" data={twin.attributes} />

      {featureNames.map((featureName) => {
        const feature = twin.features[featureName];
        return (
          <div key={featureName} className="twin-feature-stack">
            <div className="twin-feature-heading">
              <h3>{featureName}</h3>
              <span>{feature.metadata.unit}</span>
            </div>
            <JsonBlock title="Desired" data={feature.properties.desired} />
            <JsonBlock title="Reported" data={feature.properties.reported} />
            <JsonBlock title="Current" data={feature.properties.current} />
          </div>
        );
      })}
    </section>
  );
}

export default TwinInspectorDrawer;
