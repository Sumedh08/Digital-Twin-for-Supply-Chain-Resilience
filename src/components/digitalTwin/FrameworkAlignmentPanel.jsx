import React from 'react';

function FrameworkAlignmentPanel({ frameworkAlignment, architecture, sources }) {
  const frameworks = frameworkAlignment?.frameworks || [];
  const sourceList = sources || [];

  return (
    <section className="twin-panel">
      <div className="twin-panel-header">
        <div>
          <p className="twin-kicker">Linux Foundation Ecosystem Mapping</p>
          <h2>Why this backend is not just a demo</h2>
        </div>
      </div>

      <div className="twin-architecture-strip twin-architecture-mini">
        {(architecture?.layers || []).map((layer, index) => (
          <div key={layer} className="twin-architecture-step">
            <span>{index + 1}</span>
            <strong>{layer}</strong>
            <p>{architecture?.explanation?.[layer]}</p>
          </div>
        ))}
      </div>

      <div className="twin-framework-list">
        {frameworks.map((framework) => (
          <article key={framework.name} className="twin-framework-card">
            <div className="twin-framework-top">
              <strong>{framework.name}</strong>
              <span>{framework.visibleOnPage}</span>
            </div>
            <ul>
              {framework.whatIsImplemented.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <a href={framework.reference} target="_blank" rel="noreferrer">
              Reference
            </a>
          </article>
        ))}
      </div>

      <div className="twin-source-list">
        <div className="twin-source-header">
          <strong>India data grounding</strong>
          <span>{sourceList.length} sources</span>
        </div>
        {sourceList.slice(0, 4).map((source) => (
          <a key={source.id} href={source.url} target="_blank" rel="noreferrer" className="twin-source-link">
            <span>{source.title}</span>
            <small>{source.supports?.[0]}</small>
          </a>
        ))}
      </div>
    </section>
  );
}

export default FrameworkAlignmentPanel;
