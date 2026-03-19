import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { loadDeployment } from './utils/ethereum'

// Initialize blockchain deployment info
load_deployment_async();

async function load_deployment_async() {
  await loadDeployment();
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
