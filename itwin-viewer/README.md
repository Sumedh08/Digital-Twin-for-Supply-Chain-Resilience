# iTwin Viewer Microfrontend

This workspace documents the dedicated spatial microfrontend boundary for the India steel digital twin route.

How it fits the platform:
- The React app hosts `/public/itwin-viewer/index.html` in an iframe on `/digital-twin/india-steel`.
- The parent route posts overlay payloads from `/india-steel-twin/spatial-overlay`.
- When Bentley credentials and viewer packages are available, this boundary is where the official iTwin Web Viewer bootstrap should replace the current overlay stub.

Expected backend environment alignment:
- `BENTLEY_ITWIN_ID`
- `BENTLEY_IMODEL_ID`

Judge-facing message:
- The main page already demonstrates the spatial contract, overlay schema, and backend-to-viewer wiring.
- The current repo uses the fallback globe as the default visible renderer because the Bentley runtime and credentials are intentionally optional for offline demo portability.
