import React, { useState, useEffect } from 'react';
import './index.css';

const API_BASE_URL = 'http://127.0.0.1:8000';

const CATEGORIES = [
  { id: 'Hardware', label: 'Hardware', icon: '💻' },
  { id: 'Software', label: 'Software', icon: '💾' },
  { id: 'Network', label: 'Network', icon: '🌐' },
  { id: 'Access', label: 'Access', icon: '🔑' },
  { id: 'Other', label: 'Other', icon: '📦' },
];

const PRIORITIES = [
  { id: 'Low', label: 'Low', color: '#10b981' },
  { id: 'Medium', label: 'Medium', color: '#f59e0b' },
  { id: 'High', label: 'High', color: '#f97316' },
  { id: 'Critical', label: 'Critical', color: '#f43f5e' },
];

function App() {
  // Health & System state
  const [healthData, setHealthData] = useState(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthError, setHealthError] = useState(null);
  const [latency, setLatency] = useState(null);

  // Storage & Atlas Guide state
  const [storageStatus, setStorageStatus] = useState(null);
  const [showAtlasGuide, setShowAtlasGuide] = useState(false);

  // Tickets state
  const [tickets, setTickets] = useState([]);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [ticketsError, setTicketsError] = useState(null);

  // Filter state
  const [filterCategory, setFilterCategory] = useState('ALL');
  const [filterPriority, setFilterPriority] = useState('ALL');

  // Create Ticket Form state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('Software');
  const [priority, setPriority] = useState('Medium');
  const [submitting, setSubmitting] = useState(false);
  const [formSuccess, setFormSuccess] = useState(null);
  const [formError, setFormError] = useState(null);

  // 1. Backend Health Check
  const checkHealth = async () => {
    setHealthLoading(true);
    setHealthError(null);
    const start = performance.now();

    try {
      const res = await fetch(`${API_BASE_URL}/health`);
      const end = performance.now();
      setLatency(Math.round(end - start));

      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      const data = await res.json();
      setHealthData(data);
    } catch (err) {
      setHealthError(err.message || 'Unable to connect to FastAPI backend');
      setHealthData(null);
      setLatency(null);
    } finally {
      setHealthLoading(false);
    }
  };

  // 2. Fetch Storage Status
  const fetchStorageStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/storage-status`);
      if (res.ok) {
        const data = await res.json();
        setStorageStatus(data);
      }
    } catch (err) {
      console.warn('Storage status query skipped:', err.message);
    }
  };

  // 3. Fetch All Tickets
  const fetchTickets = async () => {
    setTicketsLoading(true);
    setTicketsError(null);

    try {
      const res = await fetch(`${API_BASE_URL}/api/tickets`);
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      const data = await res.json();
      setTickets(data.tickets || []);
    } catch (err) {
      setTicketsError(err.message || 'Failed to load tickets');
    } finally {
      setTicketsLoading(false);
    }
  };

  // Initial mount load
  useEffect(() => {
    checkHealth();
    fetchStorageStatus();
    fetchTickets();
  }, []);

  // 4. Handle Ticket Form Submission
  const handleCreateTicket = async (e) => {
    e.preventDefault();
    setFormSuccess(null);
    setFormError(null);

    // Client-side validations
    const trimmedTitle = title.trim();
    const trimmedDesc = description.trim();

    if (trimmedTitle.length < 3) {
      setFormError('Ticket title must be at least 3 characters long.');
      return;
    }
    if (trimmedDesc.length < 10) {
      setFormError('Ticket description must be at least 10 characters long to provide sufficient detail.');
      return;
    }

    setSubmitting(true);

    try {
      const payload = {
        title: trimmedTitle,
        description: trimmedDesc,
        category: category,
        priority: priority,
      };

      const res = await fetch(`${API_BASE_URL}/api/tickets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned HTTP ${res.status}`);
      }

      const createdTicket = await res.json();
      setFormSuccess(`Ticket ${createdTicket.ticket_number} created successfully!`);

      // Reset form fields
      setTitle('');
      setDescription('');
      setCategory('Software');
      setPriority('Medium');

      // Refresh ticket board
      fetchTickets();
    } catch (err) {
      setFormError(err.message || 'Error submitting ticket. Please check backend connection.');
    } finally {
      setSubmitting(false);
    }
  };

  // Filtered tickets
  const filteredTickets = tickets.filter((t) => {
    if (filterCategory !== 'ALL' && t.category !== filterCategory) return false;
    if (filterPriority !== 'ALL' && t.priority !== filterPriority) return false;
    return true;
  });

  return (
    <div className="app-container">
      {/* Brand Header */}
      <header className="header-section">
        <div className="brand-badge">
          <span>Enterprise ITSM Core</span>
          <span>•</span>
          <span>Phase 2: Incident Management & Database</span>
        </div>
        <h1 className="brand-title">
          HelpWise AI <span className="highlight">— ITSM Helpdesk</span>
        </h1>
        <p className="brand-subtitle">
          Enterprise IT Service Management platform with real-time ticket ingestion,
          REST API validation, and dynamic MongoDB Atlas persistence with fallback support.
        </p>
      </header>

      {/* Top Status & Health Grid */}
      <div className="top-grid">
        {/* Card 1: Backend Health Probe */}
        <div className="glass-card">
          <div className="card-header">
            <h2 className="card-title">
              <span>⚡</span> Backend Health Probe
            </h2>
            <div
              className={`status-pill ${
                healthLoading ? 'checking' : healthData ? 'online' : 'offline'
              }`}
            >
              <span
                className={`pulse-dot ${
                  healthLoading ? 'checking' : healthData ? 'online' : 'offline'
                }`}
              ></span>
              <span>
                {healthLoading ? 'Checking...' : healthData ? 'Connected' : 'Offline'}
              </span>
            </div>
          </div>

          <div className="endpoint-info-box">
            <div>
              <span className="endpoint-method">GET</span>
              <span className="endpoint-url">{API_BASE_URL}/health</span>
            </div>
            <button
              id="ping-backend-btn"
              className="btn-primary"
              onClick={checkHealth}
              disabled={healthLoading}
            >
              {healthLoading ? 'Probing...' : 'Ping Backend'}
            </button>
          </div>

          <div className="telemetry-grid">
            <div className="telemetry-item">
              <div className="telemetry-label">API Status</div>
              <div
                className="telemetry-value"
                style={{
                  color: healthData ? '#10b981' : healthError ? '#f43f5e' : '#94a3b8',
                }}
              >
                {healthData ? healthData.status.toUpperCase() : healthError ? 'UNAVAILABLE' : 'PENDING'}
              </div>
            </div>

            <div className="telemetry-item">
              <div className="telemetry-label">Round-Trip Latency</div>
              <div className="telemetry-value">
                {latency !== null ? `${latency} ms` : '—'}
              </div>
            </div>
          </div>
        </div>

        {/* Card 2: Database Layer Status & MongoDB Atlas Guide */}
        <div className="glass-card">
          <div className="card-header">
            <h2 className="card-title">
              <span>🍃</span> Database Storage Layer
            </h2>
            <span
              className="status-pill"
              style={{
                background: storageStatus?.connected
                  ? 'rgba(16, 185, 129, 0.15)'
                  : 'rgba(245, 158, 11, 0.15)',
                color: storageStatus?.connected ? '#34d399' : '#fbbf24',
                borderColor: storageStatus?.connected
                  ? 'rgba(16, 185, 129, 0.3)'
                  : 'rgba(245, 158, 11, 0.3)',
              }}
            >
              {storageStatus?.connected ? 'Atlas Connected' : 'In-Memory Fallback'}
            </span>
          </div>

          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
            {storageStatus?.connected
              ? `Connected to MongoDB Atlas cluster (Database: '${storageStatus.database_name}'). All tickets persist in cloud collections.`
              : 'Running on in-memory storage fallback. Data is live and functional for development. Configure MongoDB Atlas below for permanent storage.'}
          </p>

          <button
            className="btn-secondary"
            onClick={() => setShowAtlasGuide(!showAtlasGuide)}
          >
            {showAtlasGuide ? '▲ Hide MongoDB Atlas Setup' : '▼ How to Connect MongoDB Atlas'}
          </button>

          {showAtlasGuide && (
            <div className="atlas-guide-card">
              <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '0.5rem', color: '#34d399' }}>
                5-Step MongoDB Atlas Setup Guide:
              </div>
              <div className="atlas-guide-step">
                <strong>1.</strong> Sign up for free at <a href="https://cloud.mongodb.com" target="_blank" rel="noreferrer" style={{ color: '#818cf8' }}>cloud.mongodb.com</a> and create a free <strong>M0 Shared Cluster</strong>.
              </div>
              <div className="atlas-guide-step">
                <strong>2.</strong> Under <strong>Database Access</strong>, add a Database User with username & password.
              </div>
              <div className="atlas-guide-step">
                <strong>3.</strong> Under <strong>Network Access</strong>, click <em>Add IP Address</em> & select <strong>Allow Access from Anywhere</strong> (<code>0.0.0.0/0</code>).
              </div>
              <div className="atlas-guide-step">
                <strong>4.</strong> Click <strong>Connect &gt; Drivers &gt; Python</strong> and copy your connection URI.
              </div>
              <div className="atlas-guide-step">
                <strong>5.</strong> Paste into <code>backend/.env</code> and restart FastAPI:
                <code className="code-snippet">
                  MONGODB_URI=mongodb+srv://&lt;username&gt;:&lt;password&gt;@cluster0.mongodb.net/?retryWrites=true&w=majority
                </code>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Content Grid: Create Ticket Form + Tickets Board */}
      <div className="main-content-grid">
        {/* Left Column: Create Ticket Form */}
        <div className="glass-card">
          <div className="card-header">
            <h2 className="card-title">
              <span>📝</span> Create Support Ticket
            </h2>
            <span className="card-badge">Incident Form</span>
          </div>

          {formSuccess && (
            <div className="alert-banner success">
              <span>✅</span>
              <span>{formSuccess}</span>
            </div>
          )}

          {formError && (
            <div className="alert-banner error">
              <span>⚠️</span>
              <span>{formError}</span>
            </div>
          )}

          <form onSubmit={handleCreateTicket}>
            {/* Title Field */}
            <div className="form-group">
              <label className="form-label" htmlFor="ticket-title">
                <span>Issue Title *</span>
                <span className="char-counter">{title.length}/150</span>
              </label>
              <input
                id="ticket-title"
                type="text"
                className="form-input"
                placeholder="e.g., Cannot access internal CRM portal"
                value={title}
                maxLength={150}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </div>

            {/* Category Field */}
            <div className="form-group">
              <label className="form-label">Category *</label>
              <div className="pill-grid">
                {CATEGORIES.map((cat) => (
                  <div
                    key={cat.id}
                    className={`pill-option ${category === cat.id ? 'selected' : ''}`}
                    onClick={() => setCategory(cat.id)}
                  >
                    <span>{cat.icon}</span>
                    <span>{cat.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Priority Field */}
            <div className="form-group">
              <label className="form-label">Priority Level *</label>
              <div className="pill-grid">
                {PRIORITIES.map((p) => (
                  <div
                    key={p.id}
                    className={`pill-option ${priority === p.id ? 'selected' : ''}`}
                    onClick={() => setPriority(p.id)}
                  >
                    <span
                      style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        backgroundColor: p.color,
                        display: 'inline-block',
                      }}
                    ></span>
                    <span>{p.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Description Field */}
            <div className="form-group">
              <label className="form-label" htmlFor="ticket-desc">
                <span>Detailed Description *</span>
                <span className="char-counter">{description.length}/2000</span>
              </label>
              <textarea
                id="ticket-desc"
                className="form-textarea"
                placeholder="Describe the technical issue, error messages, and steps to reproduce (min 10 characters)..."
                value={description}
                maxLength={2000}
                onChange={(e) => setDescription(e.target.value)}
                required
              />
            </div>

            <button
              id="submit-ticket-btn"
              type="submit"
              className="btn-primary"
              style={{ width: '100%', marginTop: '0.5rem' }}
              disabled={submitting}
            >
              {submitting ? 'Submitting Incident...' : '⚡ Submit Incident Ticket'}
            </button>
          </form>
        </div>

        {/* Right Column: Incident Tickets List & Filters */}
        <div className="glass-card">
          <div className="tickets-filter-bar">
            <div>
              <h2 className="card-title" style={{ marginBottom: '0.2rem' }}>
                <span>📋</span> Incident Tickets
              </h2>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Showing {filteredTickets.length} of {tickets.length} total tickets
              </span>
            </div>

            <div className="filter-controls">
              {/* Category Filter */}
              <select
                className="filter-select"
                value={filterCategory}
                onChange={(e) => setFilterCategory(e.target.value)}
                aria-label="Filter by category"
              >
                <option value="ALL">All Categories</option>
                {CATEGORIES.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>

              {/* Priority Filter */}
              <select
                className="filter-select"
                value={filterPriority}
                onChange={(e) => setFilterPriority(e.target.value)}
                aria-label="Filter by priority"
              >
                <option value="ALL">All Priorities</option>
                {PRIORITIES.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label} Priority
                  </option>
                ))}
              </select>

              {/* Refresh Button */}
              <button
                className="btn-secondary"
                onClick={fetchTickets}
                disabled={ticketsLoading}
                title="Refresh Tickets"
              >
                {ticketsLoading ? '↻ Loading...' : '↻ Refresh'}
              </button>
            </div>
          </div>

          {/* Error Banner */}
          {ticketsError && (
            <div className="alert-banner error">
              <span>⚠️</span>
              <span>{ticketsError}</span>
            </div>
          )}

          {/* Tickets List */}
          {filteredTickets.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📂</div>
              <h3>No Tickets Found</h3>
              <p style={{ marginTop: '0.35rem', fontSize: '0.85rem' }}>
                {tickets.length === 0
                  ? 'No tickets submitted yet. Use the form on the left to create the first one!'
                  : 'No tickets match the selected filters. Try changing or clearing your filter criteria.'}
              </p>
            </div>
          ) : (
            <div className="tickets-list">
              {filteredTickets.map((ticket) => (
                <div key={ticket.id || ticket.ticket_number} className="ticket-item">
                  <div className="ticket-top-row">
                    <span className="ticket-id">{ticket.ticket_number}</span>
                    <div className="ticket-badges">
                      <span className="tag-badge cat">
                        {ticket.category}
                      </span>
                      <span className={`tag-badge priority-${ticket.priority}`}>
                        {ticket.priority}
                      </span>
                      <span className={`tag-badge status-${ticket.status.replace(/\s+/g, '-')}`}>
                        {ticket.status}
                      </span>
                    </div>
                  </div>

                  <h3 className="ticket-title">{ticket.title}</h3>
                  <p className="ticket-desc">{ticket.description}</p>

                  <div className="ticket-footer">
                    <span>
                      Created: {new Date(ticket.created_at).toLocaleString()}
                    </span>
                    <span style={{ fontFamily: 'var(--font-mono)' }}>
                      ID: {ticket.id}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
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
            <div className="cmd-title">3. Interactive Swagger UI Docs</div>
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
