(function () {
  const params = new URLSearchParams(window.location.search);
  const apiBase = params.get('apiBase');
  const network = document.getElementById('viewerNetwork');
  const status = document.getElementById('viewerStatus');
  const mode = document.getElementById('viewerMode');

  function renderOverlay(overlay) {
    if (!overlay) return;
    status.textContent = overlay.activeStage || 'Overlay received';
    mode.textContent = `Overlay bridge ready for ${overlay.viewerMode || 'fallback-globe'} handoff.`;
    network.innerHTML = '';

    const items = [...(overlay.nodes || []), ...(overlay.trucks || [])];
    items.forEach((item) => {
      const card = document.createElement('article');
      card.className = 'viewer-node';
      card.innerHTML = `
        <strong>
          <span>${item.label}</span>
          <span>${item.state || item.type}</span>
        </strong>
        <small>${item.id}</small>
        <small>Lat ${Number(item.lat || 0).toFixed(3)} | Lon ${Number(item.lon || 0).toFixed(3)}</small>
        <small>Total ${Number(item.totalTco2 || 0).toFixed(3)} tCO2</small>
      `;
      network.appendChild(card);
    });
  }

  window.addEventListener('message', (event) => {
    if (event.origin !== window.location.origin) return;
    if (event.data?.type === 'overlay-update') {
      renderOverlay(event.data.overlay);
    }
  });

  if (apiBase) {
    fetch(`${apiBase}/india-steel-twin/spatial-overlay`)
      .then((response) => response.json())
      .then((payload) => {
        if (payload.success) {
          renderOverlay(payload.data);
        }
      })
      .catch(() => {
        status.textContent = 'Waiting for parent overlay';
      });
  }
})();
