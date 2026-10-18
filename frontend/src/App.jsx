import React, { useState, useEffect } from 'react';
import './index.css';

// API Base URL - configured to point to our FastAPI local server
const BACKEND_HEALTH_URL = 'http://127.0.0.1:8000/health';

function App() {
  // State management for API health status
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [latency, setLatency] = useState(null);
  const [showRaw, setShowRaw] = useState(false);

  // Function to call FastAPI GET /health endpoint
  const checkBackendHealth = async () => {
    setLoading(true);
    setError(null);
    const startTime = performance.now();

    try {
      const response = await fetch(BACKEND_HEALTH_URL, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const endTime = performance.now();
      setLatency(Math.round(endTime - startTime));

      if (!response.ok) {
        throw new Error(`HTTP Error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      setHealthData(data);
    } catch (err) {
      setError(err.message || 'Unable to connect to FastAPI backend');
      setHealthData(null);
      setLatency(null);
    } finally {
      setLoading(false);
    }
  };

  // Check health automatically on initial page mount
  useEffect(() => {
    checkBackendHealth();
  }, []);

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="header-section">
        <div className="brand-badge">
          <span>Enterprise ITSM Core</span>
          <span>•</span>
          <span>Phase 1: Foundation</span>
        </div>
        <h1 className="brand-title">
          HelpWise AI <span className="highlight">— ITSM Helpdesk</span>
        </h1>
        <p className="brand-subtitle">
          Next-generation AI-powered IT Service Management system built with modern React,
          FastAPI, MongoDB Atlas, and intelligent RAG workflows.
        </p>
      </header>

      {/* Main Grid */}
      <div className="dashboard-grid">
        {/* Card 1: Backend Connection & Health Status */}
        <div className="glass-card">
          <div className="card-header">
            <h2 className="card-title">
              <span>⚡</span> Backend Health Probe
            </h2>
            <div
              className={`status-pill ${
                loading
                  ? 'checking'
                  : healthData
                  ? 'online'
                  : 'offline'
              }`}
            >
              <span
                className={`pulse-dot ${
                  loading
                    ? 'checking'
                    : healthData
                    ? 'online'
                    : 'offline'
                }`}
              ></span>
              <span>
                {loading
                  ? 'Checking...'
                  : healthData
                  ? 'Connected'
                  : 'Offline'}
              </span>
            </div>
          </div>

          <div className="endpoint-info-box">
            <div>
              <span className="endpoint-method">GET</span>
              <span className="endpoint-url">{BACKEND_HEALTH_URL}</span>
            </div>
            <button
              id="ping-backend-btn"
              className="btn-primary"
              onClick={checkBackendHealth}
              disabled={loading}
            >
              {loading ? 'Probing...' : 'Ping Backend'}
            </button>
          </div>

          {/* Telemetry Metrics */}
          <div className="telemetry-grid">
            <div className="telemetry-item">
              <div className="telemetry-label">API Status</div>
              <div
                className="telemetry-value"
                style={{
                  color: healthData ? '#10b981' : error ? '#f43f5e' : '#94a3b8',
                }}
              >
                {healthData ? healthData.status.toUpperCase() : error ? 'UNAVAILABLE' : 'PENDING'}
              </div>
            </div>

            <div className="telemetry-item">
              <div className="telemetry-label">Round-Trip Latency</div>
              <div className="telemetry-value">
                {latency !== null ? `${latency} ms` : '—'}
              </div>
            </div>

            <div className="telemetry-item">
              <div className="telemetry-label">Backend Service</div>
              <div className="telemetry-value" style={{ fontSize: '0.9rem' }}>
                {healthData ? healthData.app : 'FastAPI Service'}
              </div>
            </div>

            <div className="telemetry-item">
              <div className="telemetry-label">Environment</div>
              <div className="telemetry-value" style={{ fontSize: '0.9rem' }}>
                {healthData ? `${healthData.environment} (v${healthData.version})` : 'development'}
              </div>
            </div>
          </div>

          {/* Error Message Alert (if offline) */}
          {error && (
            <div
              style={{
                background: 'rgba(244, 63, 94, 0.1)',
                border: '1px solid rgba(244, 63, 94, 0.3)',
                borderRadius: '8px',
                padding: '0.85rem 1rem',
                marginBottom: '1rem',
                color: '#fecdd3',
                fontSize: '0.85rem',
              }}
            >
              <strong>Backend connection not detected:</strong> {error}
              <div style={{ marginTop: '0.35rem', color: '#fda4af' }}>
                Start FastAPI backend in PowerShell:
                <code
                  style={{
                    display: 'block',
                    marginTop: '0.25rem',
                    background: '#020617',
                    padding: '0.35rem 0.5rem',
                    borderRadius: '4px',
                    fontFamily: 'var(--font-mono)',
                    color: '#38bdf8',
                  }}
                >
                  cd backend; .\.venv\Scripts\Activate.ps1; uvicorn main:app --reload
                </code>
              </div>
            </div>
          )}

          {/* Raw JSON Toggle */}
          {healthData && (
            <div>
              <button
                onClick={() => setShowRaw(!showRaw)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#818cf8',
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  marginBottom: '0.6rem',
                  textDecoration: 'underline',
                }}
              >
                {showRaw ? '▼ Hide Raw JSON Response' : '► View Raw JSON Response'}
              </button>

              {showRaw && (
                <pre className="code-preview">
                  {JSON.stringify(healthData, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>

        {/* Card 2: ITSM System Roadmap & Architectural Stack */}
        <div className="glass-card">
          <div className="card-header">
            <h2 className="card-title">
              <span>🏗️</span> Architecture & Roadmap
            </h2>
            <span className="card-badge">Step 1 of 5</span>
          </div>

          <div className="arch-list">
            <div className="arch-item">
              <div className="arch-info">
                <span className="arch-title">1. Frontend Web Client</span>
                <span className="arch-desc">React 18, Vite build tool, Vanilla CSS</span>
              </div>
              <span className="arch-badge active">Active</span>
            </div>

            <div className="arch-item">
              <div className="arch-info">
                <span className="arch-title">2. REST API Engine</span>
                <span className="arch-desc">FastAPI, Uvicorn ASGI, Pydantic schemas</span>
              </div>
              <span className="arch-badge active">Active</span>
            </div>

            <div className="arch-item">
              <div className="arch-info">
                <span className="arch-title">3. Database Layer</span>
                <span className="arch-desc">MongoDB Atlas for tickets, KB, audit trails</span>
              </div>
              <span className="arch-badge planned">Upcoming</span>
            </div>

            <div className="arch-item">
              <div className="arch-info">
                <span className="arch-title">4. AI & RAG Pipeline</span>
                <span className="arch-desc">Vector search, document embeddings, LLM agent</span>
              </div>
              <span className="arch-badge planned">Upcoming</span>
            </div>

            <div className="arch-item">
              <div className="arch-info">
                <span className="arch-title">5. ServiceNow Integration</span>
                <span className="arch-desc">Bidirectional ticket sync (Mock mode first)</span>
              </div>
              <span className="arch-badge planned">Upcoming</span>
            </div>
          </div>
        </div>
      </div>

      {/* Commands Reference Container */}
      <div className="commands-container">
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>💻</span> Quick Reference Commands (Windows PowerShell)
        </h3>
        <div className="commands-grid">
          <div className="cmd-card">
            <div className="cmd-title">1. Start Backend (Port 8000)</div>
            <div className="cmd-text">uvicorn main:app --reload</div>
          </div>
          <div className="cmd-card">
            <div className="cmd-title">2. Start Frontend (Port 5173)</div>
            <div className="cmd-text">npm run dev</div>
          </div>
          <div className="cmd-card">
            <div className="cmd-title">3. Interactive API Docs</div>
            <div className="cmd-text">http://127.0.0.1:8000/docs</div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="footer">
        <p>HelpWise AI — Enterprise ITSM Helpdesk Assessment Project</p>
        <p style={{ marginTop: '0.25rem', fontSize: '0.8rem' }}>
          Engineered with clean separation of concerns, complete documentation, and enterprise coding standards.
        </p>
      </footer>
    </div>
  );
}

export default App;
