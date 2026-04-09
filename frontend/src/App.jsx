import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import CaseDetail from './pages/CaseDetail';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/cases" replace />} />
          <Route path="/cases" element={<Dashboard />} />
          <Route path="/cases/:caseId" element={<CaseDetail />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
