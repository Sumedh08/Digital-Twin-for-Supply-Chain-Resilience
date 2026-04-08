import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import HomePage from './pages/HomePage';
import DigitalTwinPage from './pages/DigitalTwinPage';
import RAGComparisonPage from './pages/RAGComparisonPage';
import TradeGPTPage from './pages/TradeGPTPage';
import VectorRAGPage from './pages/VectorRAGPage';
import RouteErrorBoundary from './components/RouteErrorBoundary';

function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <RouteErrorBoundary>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/digital-twin/india-steel" element={<DigitalTwinPage />} />
          <Route path="/tradegpt" element={<TradeGPTPage />} />
          <Route path="/rag-comparison" element={<RAGComparisonPage />} />
          <Route path="/vector-rag" element={<VectorRAGPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </RouteErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
