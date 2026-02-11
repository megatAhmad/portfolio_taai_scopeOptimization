/**
 * Main App component with routing
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { UploadPage } from './pages/UploadPage';
import { RulesPage } from './pages/RulesPage';
import { PreviewPage } from './pages/PreviewPage';
import { ProcessPage } from './pages/ProcessPage';
import { ResultsPage } from './pages/ResultsPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Navigate to="/upload" replace />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="rules" element={<RulesPage />} />
          <Route path="preview" element={<PreviewPage />} />
          <Route path="process" element={<ProcessPage />} />
          <Route path="results" element={<ResultsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
