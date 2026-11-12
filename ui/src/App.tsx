import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { MockBanner } from './components/layout/MockBanner';
import { ForecastPage } from './pages/Forecast';
import { AccuracyPage } from './pages/Accuracy';
import { ErrorHeatmapPage } from './pages/ErrorHeatmap';
import { MissedPeaksPage } from './pages/MissedPeaks';
import { ProcurementPage } from './pages/Procurement';
import { InsightsPage } from './pages/Insights';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-brand-bg text-brand-text flex flex-col font-sans">
        <MockBanner />
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/forecast" element={<ForecastPage />} />
            <Route path="/accuracy" element={<AccuracyPage />} />
            <Route path="/errors" element={<ErrorHeatmapPage />} />
            <Route path="/missed-peaks" element={<MissedPeaksPage />} />
            <Route path="/procurement" element={<ProcurementPage />} />
            <Route path="/insights" element={<InsightsPage />} />
            <Route path="/" element={<Navigate to="/forecast" replace />} />
            <Route path="*" element={<Navigate to="/forecast" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
};

export default App;
