import React, { useState, useEffect } from 'react';
import './index.css';

const API_BASE_URL = 'http://127.0.0.1:8000';

const CATEGORIES = ['Hardware', 'Software', 'Network', 'Access', 'Other'];
const PRIORITIES = ['Low', 'Medium', 'High', 'Critical'];
const STATUSES = ['Open', 'In Progress', 'Resolved', 'Closed'];
const AGENTS = ['Unassigned', 'Sarah Chen', 'Alex Morgan', 'David Miller', 'Priya Sharma'];

function App() {
  // Navigation & Layout
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [currentTime, setCurrentTime] = useState('');

  // System & Health Telemetry
  const [healthData, setHealthData] = useState(null);
  const [latency, setLatency] = useState(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [storageStatus, setStorageStatus] = useState(null);

  // Tickets & Stats Data
  const [tickets, setTickets] = useState([]);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [ticketsError, setTicketsError] = useState(null);
  const [stats, setStats] = useState(null);

  // KB Articles Data
  const [kbArticles, setKbArticles] = useState([]);
  const [kbLoading, setKbLoading] = useState(false);
  const [selectedArticle, setSelectedArticle] = useState(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState('ALL');
  const [filterPriority, setFilterPriority] = useState('ALL');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterAssignee, setFilterAssignee] = useState('ALL');
  const [sortBy, setSortBy] = useState('newest');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  // Create Incident Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createTitle, setCreateTitle] = useState('');
  const [createCategory, setCreateCategory] = useState('Software');
  const [createPriority, setCreatePriority] = useState('Medium');
  const [createAssignee, setCreateAssignee] = useState('Unassigned');
  const [createRequester, setCreateRequester] = useState('IT Operations');
  const [createDescription, setCreateDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [createError, setCreateError] = useState(null);
  const [createSuccess, setCreateSuccess] = useState(null);

  // Incident Details & Lifecycle Modal
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [updatingTicket, setUpdatingTicket] = useState(false);
  const [detailResolutionNotes, setDetailResolutionNotes] = useState('');

  // Clock Timer
  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setCurrentTime(
        now.toLocaleDateString('en-US', {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        }) + ' | ' + now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      );
    };
    updateClock();
    const timer = setInterval(updateClock, 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch Health & Storage
  const fetchHealth = async () => {
    setHealthLoading(true);
    const start = performance.now();
    try {
      const res = await fetch(`${API_BASE_URL}/health`);
      const end = performance.now();
      setLatency(Math.round(end - start));
      if (res.ok) {
        const data = await res.json();
        setHealthData(data);
      }
    } catch {
      setHealthData(null);
      setLatency(null);
    } finally {
      setHealthLoading(false);
    }
  };

  const fetchStorage = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/storage-status`);
      if (res.ok) {
        const data = await res.json();
        setStorageStatus(data);
      }
    } catch (e) {
      console.warn('Storage check failed:', e);
    }
  };

  // Fetch Tickets
  const fetchTickets = async () => {
    setTicketsLoading(true);
    setTicketsError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/tickets`);
      if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
      const data = await res.json();
      setTickets(data.tickets || []);
    } catch (err) {
      setTicketsError(err.message || 'Failed to connect to backend.');
    } finally {
      setTicketsLoading(false);
    }
  };

  // Fetch Stats
  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.warn('Stats fetch failed:', e);
    }
  };

  // Fetch KB Articles
  const fetchKB = async () => {
    setKbLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/kb`);
      if (res.ok) {
        const data = await res.json();
        setKbArticles(data);
      }
    } catch (e) {
      console.warn('KB fetch failed:', e);
    } finally {
      setKbLoading(false);
    }
  };

  // Initial Data Load
  useEffect(() => {
    fetchHealth();
    fetchStorage();
    fetchTickets();
    fetchStats();
    fetchKB();
  }, []);

  // Refresh all
  const handleGlobalRefresh = () => {
    fetchHealth();
    fetchTickets();
    fetchStats();
    if (activeTab === 'kb') fetchKB();
  };

  // Create Ticket Handler
  const handleCreateTicket = async (e) => {
    e.preventDefault();
    setCreateError(null);
    setCreateSuccess(null);

    const trimmedTitle = createTitle.trim();
    const trimmedDesc = createDescription.trim();

    if (trimmedTitle.length < 3) {
      setCreateError('Title must be at least 3 characters.');
      return;
    }
    if (trimmedDesc.length < 10) {
      setCreateError('Description must be at least 10 characters.');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        title: trimmedTitle,
        description: trimmedDesc,
        category: createCategory,
        priority: createPriority,
        assignee: createAssignee,
        requester: createRequester || 'IT Operations',
      };

      const res = await fetch(`${API_BASE_URL}/api/tickets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned error ${res.status}`);
      }

      const created = await res.json();
      setCreateSuccess(`Incident ${created.ticket_number} created successfully!`);

      // Reset form
      setCreateTitle('');
      setCreateDescription('');
      setCreateCategory('Software');
      setCreatePriority('Medium');
      setCreateAssignee('Unassigned');

      // Refresh data
      fetchTickets();
      fetchStats();

      // Close modal after 1.2s
      setTimeout(() => {
        setShowCreateModal(false);
        setCreateSuccess(null);
      }, 1200);
    } catch (err) {
      setCreateError(err.message || 'Error submitting incident.');
    } finally {
      setSubmitting(false);
    }
  };

  // Update Status / Lifecycle Handler
  const handleUpdateTicketStatus = async (ticketId, newStatus, resolutionNotes = null) => {
    setUpdatingTicket(true);
    try {
      const payload = {
        status: newStatus,
        resolution_notes: resolutionNotes,
        updated_by: 'Alex Morgan (Support Lead)',
      };

      const res = await fetch(`${API_BASE_URL}/api/tickets/${ticketId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
      const updated = await res.json();

      // Update state
      setSelectedTicket(updated);
      setTickets((prev) =>
        prev.map((t) => (t.id === updated.id || t.ticket_number === updated.ticket_number ? updated : t))
      );
      fetchStats();
    } catch (err) {
      alert(`Failed to update status: ${err.message}`);
    } finally {
      setUpdatingTicket(false);
    }
  };

  // Update Assignee Handler
  const handleUpdateAssignee = async (ticketId, newAssignee) => {
    setUpdatingTicket(true);
    try {
      const payload = {
        assignee: newAssignee,
        updated_by: 'Alex Morgan (Support Lead)',
      };

      const res = await fetch(`${API_BASE_URL}/api/tickets/${ticketId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
      const updated = await res.json();

      setSelectedTicket(updated);
      setTickets((prev) =>
        prev.map((t) => (t.id === updated.id || t.ticket_number === updated.ticket_number ? updated : t))
      );
      fetchStats();
    } catch (err) {
      alert(`Failed to reassign: ${err.message}`);
    } finally {
      setUpdatingTicket(false);
    }
  };

  // Filtering & Sorting Logic
  const filteredTickets = tickets.filter((t) => {
    if (searchQuery) {
      const q = searchQuery.toLowerCase().trim();
      const matchNumber = t.ticket_number.toLowerCase().includes(q);
      const matchTitle = t.title.toLowerCase().includes(q);
      const matchDesc = (t.description || '').toLowerCase().includes(q);
      const matchAssignee = (t.assignee || '').toLowerCase().includes(q);
      if (!(matchNumber || matchTitle || matchDesc || matchAssignee)) return false;
    }
    if (filterCategory !== 'ALL' && t.category !== filterCategory) return false;
    if (filterPriority !== 'ALL' && t.priority !== filterPriority) return false;
    if (filterStatus !== 'ALL' && t.status !== filterStatus) return false;
    if (filterAssignee !== 'ALL' && t.assignee !== filterAssignee) return false;
    if (activeTab === 'my_tickets' && t.assignee === 'Unassigned') return false;
    return true;
  });

  const sortedTickets = [...filteredTickets].sort((a, b) => {
    if (sortBy === 'newest') return new Date(b.created_at) - new Date(a.created_at);
    if (sortBy === 'oldest') return new Date(a.created_at) - new Date(b.created_at);
    if (sortBy === 'priority') {
      const order = { Critical: 4, High: 3, Medium: 2, Low: 1 };
      return (order[b.priority] || 0) - (order[a.priority] || 0);
    }
    return 0;
  });

  // Pagination Logic
  const totalPages = Math.ceil(sortedTickets.length / itemsPerPage) || 1;
  const paginatedTickets = sortedTickets.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  return (
    <div className="itsm-layout">
      {/* 1. Collapsible Left Sidebar */}
      <aside className={`itsm-sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-header">
          <div className="brand-link">
            <div className="brand-icon">H</div>
            {!sidebarCollapsed && <span>HelpWise AI</span>}
          </div>
        </div>

        <nav className="sidebar-nav">
          <div
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
            title="Operational Dashboard"
          >
            <span className="nav-icon">📊</span>
            {!sidebarCollapsed && <span>Dashboard</span>}
          </div>

          <div
            className={`nav-item ${activeTab === 'incidents' ? 'active' : ''}`}
            onClick={() => setActiveTab('incidents')}
            title="All Incidents"
          >
            <span className="nav-icon">🎫</span>
            {!sidebarCollapsed && <span>Incidents</span>}
          </div>

          <div
            className={`nav-item ${activeTab === 'my_tickets' ? 'active' : ''}`}
            onClick={() => setActiveTab('my_tickets')}
            title="Assigned Work Items"
          >
            <span className="nav-icon">👤</span>
            {!sidebarCollapsed && <span>My Tickets</span>}
          </div>

          <div
            className={`nav-item ${activeTab === 'kanban' ? 'active' : ''}`}
            onClick={() => setActiveTab('kanban')}
            title="Kanban Board View"
          >
            <span className="nav-icon">📋</span>
            {!sidebarCollapsed && <span>Kanban Board</span>}
          </div>

          <div
            className={`nav-item ${activeTab === 'kb' ? 'active' : ''}`}
            onClick={() => setActiveTab('kb')}
            title="Searchable Knowledge Base"
          >
            <span className="nav-icon">📚</span>
            {!sidebarCollapsed && <span>Knowledge Base</span>}
          </div>

          <div
            className={`nav-item ${activeTab === 'reports' ? 'active' : ''}`}
            onClick={() => setActiveTab('reports')}
            title="Reports & Analytics"
          >
            <span className="nav-icon">📈</span>
            {!sidebarCollapsed && <span>Reports</span>}
          </div>

          <div
            className={`nav-item ${activeTab === 'diagnostics' ? 'active' : ''}`}
            onClick={() => setActiveTab('diagnostics')}
            title="System Diagnostics & Storage"
          >
            <span className="nav-icon">⚙️</span>
            {!sidebarCollapsed && <span>System Status</span>}
          </div>
        </nav>

        <div className="sidebar-footer">
          <button
            className="collapse-btn"
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            title={sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          >
            <span className="nav-icon">{sidebarCollapsed ? '➡️' : '⬅️'}</span>
            {!sidebarCollapsed && <span>Collapse Sidebar</span>}
          </button>
        </div>
      </aside>

      {/* 2. Main Application Workspace */}
      <div className="itsm-main">
        {/* Top Navigation Bar */}
        <header className="itsm-topbar">
          <div className="topbar-left">
            <h1 className="breadcrumb-title">
              {activeTab === 'dashboard' && 'Operations Dashboard'}
              {activeTab === 'incidents' && 'Incident Management'}
              {activeTab === 'my_tickets' && 'My Assigned Tickets'}
              {activeTab === 'kanban' && 'Incident Kanban Analyzer'}
              {activeTab === 'kb' && 'IT Knowledge Base'}
              {activeTab === 'reports' && 'Performance & SLA Reports'}
              {activeTab === 'diagnostics' && 'System Health & Diagnostics'}
            </h1>
            <span className="topbar-time-pill">{currentTime}</span>
          </div>

          <div className="topbar-right">
            {/* Quick Search */}
            <div className="topbar-search-box">
              <span className="search-icon-pos">🔍</span>
              <input
                type="text"
                className="topbar-search-input"
                placeholder="Search incidents by ID, title..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            {/* Backend Connectivity Status Pill */}
            <div
              className="status-tag"
              style={{
                backgroundColor: healthData ? '#ecfdf5' : '#fff1f2',
                color: healthData ? '#059669' : '#e11d48',
                borderColor: healthData ? '#a7f3d0' : '#fecdd3',
                cursor: 'pointer',
              }}
              onClick={() => setActiveTab('diagnostics')}
              title="Click to view System Diagnostics"
            >
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: healthData ? '#10b981' : '#f43f5e',
                }}
              ></span>
              <span>{healthData ? `Healthy (${latency || 12}ms)` : 'Offline'}</span>
            </div>

            {/* Primary Action: Create Incident */}
            <button
              className="btn-primary"
              onClick={() => setShowCreateModal(true)}
            >
              <span>+</span>
              <span>Create Incident</span>
            </button>

            {/* User Profile */}
            <div className="user-profile-badge">
              <div className="user-avatar">AM</div>
              <div className="user-meta">
                <div className="user-meta-name">Alex Morgan</div>
                <div className="user-meta-role">Support Lead</div>
              </div>
            </div>
          </div>
        </header>

        {/* 3. Main Body Content Switcher */}
        <main className="content-body">
          {/* ====================================================================
              VIEW A: DASHBOARD
             ==================================================================== */}
          {activeTab === 'dashboard' && (
            <div>
              {/* Operational KPI Grid */}
              <div className="kpi-grid">
                <div className="kpi-card">
                  <div>
                    <div className="kpi-label">Total Incidents</div>
                    <div className="kpi-value">{stats?.total ?? tickets.length}</div>
                  </div>
                  <div className="kpi-icon-bubble" style={{ backgroundColor: '#eff6ff', color: '#2563eb' }}>
                    📑
                  </div>
                </div>

                <div className="kpi-card">
                  <div>
                    <div className="kpi-label">Open Queue</div>
                    <div className="kpi-value">{stats?.open ?? 0}</div>
                  </div>
                  <div className="kpi-icon-bubble" style={{ backgroundColor: '#eff6ff', color: '#3b82f6' }}>
                    🟢
                  </div>
                </div>

                <div className="kpi-card">
                  <div>
                    <div className="kpi-label">In Progress</div>
                    <div className="kpi-value">{stats?.in_progress ?? 0}</div>
                  </div>
                  <div className="kpi-icon-bubble" style={{ backgroundColor: '#fffbeb', color: '#d97706' }}>
                    🟡
                  </div>
                </div>

                <div className="kpi-card">
                  <div>
                    <div className="kpi-label">Resolved / Closed</div>
                    <div className="kpi-value">{(stats?.resolved ?? 0) + (stats?.closed ?? 0)}</div>
                  </div>
                  <div className="kpi-icon-bubble" style={{ backgroundColor: '#ecfdf5', color: '#059669' }}>
                    ✅
                  </div>
                </div>

                <div className="kpi-card">
                  <div>
                    <div className="kpi-label">High / Critical</div>
                    <div className="kpi-value">{stats?.high_critical ?? 0}</div>
                  </div>
                  <div className="kpi-icon-bubble" style={{ backgroundColor: '#ffe4e6', color: '#e11d48' }}>
                    🚨
                  </div>
                </div>
              </div>

              {/* Two Column Split: Category Distribution + Recent Incidents */}
              <div className="dashboard-split-grid">
                {/* Recent Incidents Card */}
                <div className="surface-card">
                  <div className="card-title-row">
                    <h2 className="card-heading">
                      <span>⏱️</span> Recently Updated Incidents
                    </h2>
                    <button
                      className="btn-secondary"
                      onClick={() => setActiveTab('incidents')}
                      style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
                    >
                      View All Incidents →
                    </button>
                  </div>

                  <div className="table-responsive">
                    <table className="itsm-table">
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Title</th>
                          <th>Category</th>
                          <th>Priority</th>
                          <th>Status</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tickets.slice(0, 5).map((t) => (
                          <tr key={t.id}>
                            <td className="ticket-number-cell" onClick={() => setSelectedTicket(t)}>
                              {t.ticket_number}
                            </td>
                            <td style={{ fontWeight: 500 }}>{t.title}</td>
                            <td>
                              <span className="category-tag">{t.category}</span>
                            </td>
                            <td>
                              <span className={`priority-tag ${t.priority}`}>
                                <span
                                  className="priority-dot"
                                  style={{
                                    backgroundColor:
                                      t.priority === 'Critical'
                                        ? '#e11d48'
                                        : t.priority === 'High'
                                        ? '#ea580c'
                                        : t.priority === 'Medium'
                                        ? '#d97706'
                                        : '#059669',
                                  }}
                                ></span>
                                {t.priority}
                              </span>
                            </td>
                            <td>
                              <span className={`status-tag ${t.status.replace(/\s+/g, '-')}`}>
                                {t.status}
                              </span>
                            </td>
                            <td>
                              <button
                                className="btn-secondary"
                                style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem' }}
                                onClick={() => setSelectedTicket(t)}
                              >
                                View
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Category & Status Breakdown Card */}
                <div className="surface-card">
                  <div className="card-title-row">
                    <h2 className="card-heading">
                      <span>📁</span> Incidents by Category
                    </h2>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Active Queue
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                    {CATEGORIES.map((cat) => {
                      const count = stats?.by_category?.[cat] || 0;
                      const percentage = stats?.total ? Math.round((count / stats.total) * 100) : 0;
                      return (
                        <div key={cat}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.825rem', marginBottom: '0.3rem' }}>
                            <span style={{ fontWeight: 600 }}>{cat}</span>
                            <span style={{ color: 'var(--text-muted)' }}>{count} ({percentage}%)</span>
                          </div>
                          <div style={{ height: '7px', backgroundColor: '#f1f5f9', borderRadius: '4px', overflow: 'hidden' }}>
                            <div
                              style={{
                                height: '100%',
                                width: `${percentage}%`,
                                backgroundColor: '#2563eb',
                                borderRadius: '4px',
                                transition: 'width 0.4s ease',
                              }}
                            ></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ====================================================================
              VIEW B: INCIDENTS TABLE & MANAGEMENT
             ==================================================================== */}
          {(activeTab === 'incidents' || activeTab === 'my_tickets') && (
            <div className="surface-card">
              {/* Filter and Action Bar */}
              <div className="filter-action-bar">
                <div className="filter-group">
                  {/* Category Filter */}
                  <select
                    className="select-filter"
                    value={filterCategory}
                    onChange={(e) => {
                      setFilterCategory(e.target.value);
                      setCurrentPage(1);
                    }}
                  >
                    <option value="ALL">All Categories</option>
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>

                  {/* Priority Filter */}
                  <select
                    className="select-filter"
                    value={filterPriority}
                    onChange={(e) => {
                      setFilterPriority(e.target.value);
                      setCurrentPage(1);
                    }}
                  >
                    <option value="ALL">All Priorities</option>
                    {PRIORITIES.map((p) => (
                      <option key={p} value={p}>
                        {p} Priority
                      </option>
                    ))}
                  </select>

                  {/* Status Filter */}
                  <select
                    className="select-filter"
                    value={filterStatus}
                    onChange={(e) => {
                      setFilterStatus(e.target.value);
                      setCurrentPage(1);
                    }}
                  >
                    <option value="ALL">All Statuses</option>
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>

                  {/* Assignee Filter */}
                  <select
                    className="select-filter"
                    value={filterAssignee}
                    onChange={(e) => {
                      setFilterAssignee(e.target.value);
                      setCurrentPage(1);
                    }}
                  >
                    <option value="ALL">All Assignees</option>
                    {AGENTS.map((a) => (
                      <option key={a} value={a}>
                        {a}
                      </option>
                    ))}
                  </select>

                  {/* Sort Filter */}
                  <select
                    className="select-filter"
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                  >
                    <option value="newest">Sort: Newest First</option>
                    <option value="oldest">Sort: Oldest First</option>
                    <option value="priority">Sort: Highest Priority</option>
                  </select>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button className="btn-secondary" onClick={handleGlobalRefresh} title="Refresh Table">
                    <span>↻ Refresh</span>
                  </button>
                  <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
                    <span>+ New Incident</span>
                  </button>
                </div>
              </div>

              {/* Table / Error State */}
              {ticketsError ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: '#e11d48' }}>
                  <p>⚠️ {ticketsError}</p>
                  <button className="btn-secondary" onClick={fetchTickets} style={{ marginTop: '0.75rem' }}>
                    Try Again
                  </button>
                </div>
              ) : paginatedTickets.length === 0 ? (
                <div className="empty-box">
                  <div className="empty-icon">📂</div>
                  <h3>No Incidents Found</h3>
                  <p style={{ marginTop: '0.35rem', fontSize: '0.85rem' }}>
                    {tickets.length === 0
                      ? 'No incidents logged yet. Create your first incident ticket!'
                      : 'No incidents match the active search and filter criteria.'}
                  </p>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="itsm-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Title / Short Description</th>
                        <th>Category</th>
                        <th>Priority</th>
                        <th>Status</th>
                        <th>Assignee</th>
                        <th>Created Date</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedTickets.map((ticket) => (
                        <tr key={ticket.id}>
                          <td
                            className="ticket-number-cell"
                            onClick={() => setSelectedTicket(ticket)}
                            title="Click to view details"
                          >
                            {ticket.ticket_number}
                          </td>
                          <td style={{ fontWeight: 600 }}>{ticket.title}</td>
                          <td>
                            <span className="category-tag">{ticket.category}</span>
                          </td>
                          <td>
                            <span className={`priority-tag ${ticket.priority}`}>
                              <span
                                className="priority-dot"
                                style={{
                                  backgroundColor:
                                    ticket.priority === 'Critical'
                                      ? '#e11d48'
                                      : ticket.priority === 'High'
                                      ? '#ea580c'
                                      : ticket.priority === 'Medium'
                                      ? '#d97706'
                                      : '#059669',
                                }}
                              ></span>
                              {ticket.priority}
                            </span>
                          </td>
                          <td>
                            <span className={`status-tag ${ticket.status.replace(/\s+/g, '-')}`}>
                              {ticket.status}
                            </span>
                          </td>
                          <td style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
                            {ticket.assignee}
                          </td>
                          <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            {new Date(ticket.created_at).toLocaleDateString()}{' '}
                            {new Date(ticket.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </td>
                          <td>
                            <button
                              className="btn-secondary"
                              style={{ padding: '0.3rem 0.65rem', fontSize: '0.775rem' }}
                              onClick={() => setSelectedTicket(ticket)}
                            >
                              Manage
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Pagination Controls */}
              {sortedTickets.length > 0 && (
                <div className="pagination-row">
                  <div>
                    Showing {(currentPage - 1) * itemsPerPage + 1} to{' '}
                    {Math.min(currentPage * itemsPerPage, sortedTickets.length)} of {sortedTickets.length} incidents
                  </div>
                  <div className="pagination-controls">
                    <button
                      className="btn-secondary"
                      disabled={currentPage === 1}
                      onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                    >
                      Previous
                    </button>
                    <span style={{ padding: '0 0.5rem', fontWeight: 600 }}>
                      Page {currentPage} of {totalPages}
                    </span>
                    <button
                      className="btn-secondary"
                      disabled={currentPage === totalPages}
                      onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ====================================================================
              VIEW C: KANBAN BOARD
             ==================================================================== */}
          {activeTab === 'kanban' && (
            <div>
              <div className="filter-action-bar" style={{ marginBottom: '1.25rem' }}>
                <div className="filter-group">
                  <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-main)' }}>
                    Workflow Columns:
                  </span>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    Drag or update status directly on cards
                  </span>
                </div>
                <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
                  + New Incident
                </button>
              </div>

              <div className="kanban-grid">
                {STATUSES.map((colStatus) => {
                  const colTickets = tickets.filter((t) => t.status === colStatus);
                  return (
                    <div key={colStatus} className="kanban-column">
                      <div className="kanban-column-header">
                        <div className="kanban-col-title">
                          <span>
                            {colStatus === 'Open' && '🟢'}
                            {colStatus === 'In Progress' && '🟡'}
                            {colStatus === 'Resolved' && '✅'}
                            {colStatus === 'Closed' && '📁'}
                          </span>
                          <span>{colStatus}</span>
                        </div>
                        <span className="kanban-count-badge">{colTickets.length}</span>
                      </div>

                      <div>
                        {colTickets.length === 0 ? (
                          <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-muted)', fontSize: '0.825rem' }}>
                            No incidents in {colStatus}
                          </div>
                        ) : (
                          colTickets.map((t) => (
                            <div key={t.id} className="kanban-card">
                              <div className="kanban-card-top">
                                <span
                                  className="ticket-number-cell"
                                  onClick={() => setSelectedTicket(t)}
                                >
                                  {t.ticket_number}
                                </span>
                                <span className={`priority-tag ${t.priority}`}>
                                  {t.priority}
                                </span>
                              </div>

                              <div className="kanban-card-title">{t.title}</div>
                              <div className="kanban-card-desc">{t.description}</div>

                              <div className="kanban-card-footer">
                                <span>👤 {t.assignee}</span>
                                <button
                                  className="btn-secondary"
                                  style={{ padding: '0.2rem 0.5rem', fontSize: '0.725rem' }}
                                  onClick={() => setSelectedTicket(t)}
                                >
                                  Details →
                                </button>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ====================================================================
              VIEW D: KNOWLEDGE BASE
             ==================================================================== */}
          {activeTab === 'kb' && (
            <div>
              <div className="surface-card" style={{ marginBottom: '1.5rem' }}>
                <div style={{ maxWidth: '600px' }}>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.4rem' }}>
                    IT Service Knowledge Base
                  </h2>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                    Standard operating procedures, incident resolution guides, and self-service documentation.
                  </p>
                  <div className="topbar-search-box" style={{ width: '100%' }}>
                    <span className="search-icon-pos">🔍</span>
                    <input
                      type="text"
                      className="topbar-search-input"
                      placeholder="Search troubleshooting guides by keyword, tool, or error code..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {kbLoading ? (
                <div style={{ textAlign: 'center', padding: '3rem' }}>Loading Knowledge Base...</div>
              ) : (
                <div className="kb-grid">
                  {kbArticles
                    .filter((art) => {
                      if (!searchQuery) return true;
                      const q = searchQuery.toLowerCase();
                      return (
                        art.title.toLowerCase().includes(q) ||
                        art.excerpt.toLowerCase().includes(q) ||
                        art.category.toLowerCase().includes(q) ||
                        art.tags.some((t) => t.toLowerCase().includes(q))
                      );
                    })
                    .map((art) => (
                      <div
                        key={art.id}
                        className="kb-card"
                        onClick={() => setSelectedArticle(art)}
                      >
                        <div className="kb-tag-row">
                          <span className="category-tag">{art.category}</span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
                            ⏱️ {art.read_time}
                          </span>
                        </div>
                        <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.5rem' }}>
                          {art.title}
                        </h3>
                        <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: 1.45, marginBottom: '0.75rem' }}>
                          {art.excerpt}
                        </p>
                        <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                          {art.tags.map((tag) => (
                            <span key={tag} className="kb-pill">
                              #{tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </div>
          )}

          {/* ====================================================================
              VIEW E: REPORTS & ANALYTICS
             ==================================================================== */}
          {activeTab === 'reports' && (
            <div>
              <div className="kpi-grid">
                <div className="kpi-card">
                  <div>
                    <div className="kpi-label">SLA Compliance Rate</div>
                    <div className="kpi-value" style={{ color: '#059669' }}>94.2%</div>
                  </div>
                  <div className="kpi-icon-bubble" style={{ backgroundColor: '#ecfdf5', color: '#059669' }}>🎯</div>
                </div>

                <div className="kpi-card">
                  <div>
                    <div className="kpi-label">Mean Time to Resolve (MTTR)</div>
                    <div className="kpi-value">2.4h</div>
                  </div>
                  <div className="kpi-icon-bubble" style={{ backgroundColor: '#eff6ff', color: '#2563eb' }}>⏱️</div>
                </div>

                <div className="kpi-card">
                  <div>
                    <div className="kpi-label">First Contact Resolution</div>
                    <div className="kpi-value">78.5%</div>
                  </div>
                  <div className="kpi-icon-bubble" style={{ backgroundColor: '#fffbeb', color: '#d97706' }}>💡</div>
                </div>

                <div className="kpi-card">
                  <div>
                    <div className="kpi-label">Critical Incident Backlog</div>
                    <div className="kpi-value" style={{ color: '#e11d48' }}>
                      {stats?.by_priority?.['Critical'] || 0}
                    </div>
                  </div>
                  <div className="kpi-icon-bubble" style={{ backgroundColor: '#ffe4e6', color: '#e11d48' }}>🔥</div>
                </div>
              </div>

              <div className="surface-card">
                <div className="card-title-row">
                  <h2 className="card-heading">
                    <span>📊</span> Priority Breakdown vs Resolution SLA
                  </h2>
                </div>
                <div className="table-responsive">
                  <table className="itsm-table">
                    <thead>
                      <tr>
                        <th>Priority Level</th>
                        <th>Active Count</th>
                        <th>Target Response SLA</th>
                        <th>Target Resolution SLA</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td><span className="priority-tag Critical">Critical</span></td>
                        <td><strong>{stats?.by_priority?.['Critical'] || 0}</strong></td>
                        <td>15 minutes</td>
                        <td>2 hours</td>
                        <td><span className="status-tag In-Progress">Monitored</span></td>
                      </tr>
                      <tr>
                        <td><span className="priority-tag High">High</span></td>
                        <td><strong>{stats?.by_priority?.['High'] || 0}</strong></td>
                        <td>30 minutes</td>
                        <td>4 hours</td>
                        <td><span className="status-tag Open">Normal</span></td>
                      </tr>
                      <tr>
                        <td><span className="priority-tag Medium">Medium</span></td>
                        <td><strong>{stats?.by_priority?.['Medium'] || 0}</strong></td>
                        <td>2 hours</td>
                        <td>8 hours</td>
                        <td><span className="status-tag Open">Normal</span></td>
                      </tr>
                      <tr>
                        <td><span className="priority-tag Low">Low</span></td>
                        <td><strong>{stats?.by_priority?.['Low'] || 0}</strong></td>
                        <td>4 hours</td>
                        <td>24 hours</td>
                        <td><span className="status-tag Resolved">Healthy</span></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ====================================================================
              VIEW F: SYSTEM STATUS & DIAGNOSTICS
             ==================================================================== */}
          {activeTab === 'diagnostics' && (
            <div>
              <div className="dashboard-split-grid">
                {/* Health & API Diagnostics Card */}
                <div className="surface-card">
                  <div className="card-title-row">
                    <h2 className="card-heading">
                      <span>⚡</span> Backend API Diagnostics
                    </h2>
                    <button className="btn-secondary" onClick={fetchHealth} disabled={healthLoading}>
                      {healthLoading ? 'Testing...' : 'Test Connection'}
                    </button>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.6rem 0', borderBottom: '1px solid var(--border)' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>REST API Status</span>
                      <span className="status-tag Open">{healthData ? healthData.status.toUpperCase() : 'OFFLINE'}</span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.6rem 0', borderBottom: '1px solid var(--border)' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Round-Trip Latency</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{latency !== null ? `${latency} ms` : '—'}</span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.6rem 0', borderBottom: '1px solid var(--border)' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Service Version</span>
                      <span style={{ fontFamily: 'var(--font-mono)' }}>v1.1.0 (FastAPI ASGI)</span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.6rem 0' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Active Storage Engine</span>
                      <span className="category-tag">{storageStatus?.mode || 'in_memory_fallback'}</span>
                    </div>
                  </div>
                </div>

                {/* MongoDB Atlas Setup & Storage Card */}
                <div className="surface-card">
                  <div className="card-title-row">
                    <h2 className="card-heading">
                      <span>🍃</span> Database Storage Configuration
                    </h2>
                    <span
                      className="status-tag"
                      style={{
                        backgroundColor: storageStatus?.connected ? '#ecfdf5' : '#fffbeb',
                        color: storageStatus?.connected ? '#059669' : '#d97706',
                      }}
                    >
                      {storageStatus?.connected ? 'Atlas Connected' : 'In-Memory Fallback'}
                    </span>
                  </div>

                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem', lineHeight: 1.5 }}>
                    {storageStatus?.connected
                      ? `Connected to permanent MongoDB Atlas cluster ('${storageStatus.database_name}'). Incidents persist permanently across server restarts.`
                      : 'Currently operating on the high-performance in-memory development fallback. When you are ready to configure MongoDB Atlas, follow the instructions below.'}
                  </p>

                  <div style={{ backgroundColor: 'var(--bg-surface-alt)', padding: '1rem', borderRadius: 'var(--radius-md)', fontSize: '0.8rem', lineHeight: 1.6 }}>
                    <div style={{ fontWeight: 700, marginBottom: '0.35rem' }}>Next Step: MongoDB Atlas Setup</div>
                    1. Create a free M0 cluster at <a href="https://cloud.mongodb.com" target="_blank" rel="noreferrer" style={{ color: 'var(--primary)' }}>cloud.mongodb.com</a>.<br />
                    2. Add Database User & whitelist IP (0.0.0.0/0).<br />
                    3. Copy Python connection URI into <code>backend/.env</code>:<br />
                    <code style={{ display: 'block', margin: '0.4rem 0', padding: '0.4rem', backgroundColor: '#ffffff', border: '1px solid var(--border)', borderRadius: '4px' }}>
                      MONGODB_URI=mongodb+srv://&lt;username&gt;:&lt;password&gt;@cluster0.mongodb.net/?retryWrites=true&w=majority
                    </code>
                    4. Restart backend server to activate permanent storage.
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* ====================================================================
          MODAL 1: CREATE INCIDENT
         ==================================================================== */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Log New Incident Ticket</h2>
              <button
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text-muted)' }}
                onClick={() => setShowCreateModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateTicket}>
              <div className="modal-body">
                {createSuccess && (
                  <div style={{ padding: '0.75rem', backgroundColor: '#ecfdf5', color: '#059669', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.85rem' }}>
                    ✅ {createSuccess}
                  </div>
                )}
                {createError && (
                  <div style={{ padding: '0.75rem', backgroundColor: '#fff1f2', color: '#e11d48', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.85rem' }}>
                    ⚠️ {createError}
                  </div>
                )}

                {/* Title */}
                <div className="form-field">
                  <div className="field-label">
                    <span>Short Description / Title *</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{createTitle.length}/150</span>
                  </div>
                  <input
                    type="text"
                    className="input-text"
                    placeholder="e.g., Cannot access corporate Git repository"
                    value={createTitle}
                    onChange={(e) => setCreateTitle(e.target.value)}
                    maxLength={150}
                    required
                  />
                </div>

                {/* Category & Priority Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
                  <div>
                    <div className="field-label">Category *</div>
                    <select
                      className="select-control"
                      value={createCategory}
                      onChange={(e) => setCreateCategory(e.target.value)}
                    >
                      {CATEGORIES.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <div className="field-label">Urgency / Priority *</div>
                    <select
                      className="select-control"
                      value={createPriority}
                      onChange={(e) => setCreatePriority(e.target.value)}
                    >
                      {PRIORITIES.map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Assignee & Requester Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
                  <div>
                    <div className="field-label">Assignee</div>
                    <select
                      className="select-control"
                      value={createAssignee}
                      onChange={(e) => setCreateAssignee(e.target.value)}
                    >
                      {AGENTS.map((a) => (
                        <option key={a} value={a}>
                          {a}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <div className="field-label">Requester Department</div>
                    <input
                      type="text"
                      className="input-text"
                      placeholder="e.g., DevOps, Finance, Sales"
                      value={createRequester}
                      onChange={(e) => setCreateRequester(e.target.value)}
                    />
                  </div>
                </div>

                {/* Detailed Description */}
                <div className="form-field">
                  <div className="field-label">
                    <span>Detailed Technical Description *</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{createDescription.length}/2000</span>
                  </div>
                  <textarea
                    className="textarea-control"
                    placeholder="Provide reproduction steps, error messages, client OS, and impact..."
                    value={createDescription}
                    onChange={(e) => setCreateDescription(e.target.value)}
                    maxLength={2000}
                    required
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={submitting}
                >
                  {submitting ? 'Submitting Incident...' : 'Log Incident Ticket'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ====================================================================
          MODAL 2: INCIDENT DETAILS & LIFECYCLE MANAGEMENT
         ==================================================================== */}
      {selectedTicket && (
        <div className="modal-overlay" onClick={() => setSelectedTicket(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '750px' }}>
            <div className="modal-header">
              <div>
                <span className="ticket-number-cell" style={{ fontSize: '1rem' }}>
                  {selectedTicket.ticket_number}
                </span>
                <span style={{ margin: '0 0.5rem', color: 'var(--text-muted)' }}>•</span>
                <span className={`status-tag ${selectedTicket.status.replace(/\s+/g, '-')}`}>
                  {selectedTicket.status}
                </span>
              </div>
              <button
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text-muted)' }}
                onClick={() => setSelectedTicket(null)}
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '0.65rem' }}>
                {selectedTicket.title}
              </h2>

              {/* Badges strip */}
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
                <span className="category-tag">Category: {selectedTicket.category}</span>
                <span className={`priority-tag ${selectedTicket.priority}`}>Priority: {selectedTicket.priority}</span>
                <span className="category-tag">Assignee: {selectedTicket.assignee}</span>
                <span className="category-tag">Requester: {selectedTicket.requester}</span>
              </div>

              {/* Description box */}
              <div style={{ backgroundColor: 'var(--bg-surface-alt)', padding: '1rem', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem', fontSize: '0.875rem', lineHeight: 1.6 }}>
                <strong>Issue Description:</strong>
                <p style={{ marginTop: '0.35rem', whiteSpace: 'pre-wrap' }}>{selectedTicket.description}</p>
                {selectedTicket.resolution_notes && (
                  <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)', color: '#059669' }}>
                    <strong>Resolution Notes:</strong> {selectedTicket.resolution_notes}
                  </div>
                )}
              </div>

              {/* Lifecycle Actions Bar */}
              <div style={{ border: '1px solid var(--border)', padding: '1rem', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem' }}>
                <h3 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '0.75rem' }}>
                  Incident Lifecycle & Transition Actions:
                </h3>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                  {selectedTicket.status === 'Open' && (
                    <button
                      className="btn-primary"
                      disabled={updatingTicket}
                      onClick={() => handleUpdateTicketStatus(selectedTicket.id, 'In Progress')}
                    >
                      Start Working (In Progress)
                    </button>
                  )}

                  {selectedTicket.status === 'In Progress' && (
                    <button
                      className="btn-primary"
                      style={{ backgroundColor: '#059669', borderColor: '#059669' }}
                      disabled={updatingTicket}
                      onClick={() => {
                        const note = prompt('Please enter resolution notes:') || 'Resolved by IT support';
                        handleUpdateTicketStatus(selectedTicket.id, 'Resolved', note);
                      }}
                    >
                      Mark as Resolved
                    </button>
                  )}

                  {selectedTicket.status === 'Resolved' && (
                    <>
                      <button
                        className="btn-primary"
                        style={{ backgroundColor: '#475569', borderColor: '#475569' }}
                        disabled={updatingTicket}
                        onClick={() => handleUpdateTicketStatus(selectedTicket.id, 'Closed')}
                      >
                        Close Incident
                      </button>
                      <button
                        className="btn-secondary"
                        disabled={updatingTicket}
                        onClick={() => handleUpdateTicketStatus(selectedTicket.id, 'In Progress', 'Reopened by support agent')}
                      >
                        Reopen Incident
                      </button>
                    </>
                  )}

                  {selectedTicket.status === 'Closed' && (
                    <button
                      className="btn-secondary"
                      disabled={updatingTicket}
                      onClick={() => handleUpdateTicketStatus(selectedTicket.id, 'In Progress', 'Reopened from closed state')}
                    >
                      Reopen Incident
                    </button>
                  )}

                  {/* Reassign Dropdown */}
                  <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Reassign:</span>
                    <select
                      className="select-filter"
                      value={selectedTicket.assignee}
                      onChange={(e) => handleUpdateAssignee(selectedTicket.id, e.target.value)}
                      disabled={updatingTicket}
                    >
                      {AGENTS.map((a) => (
                        <option key={a} value={a}>
                          {a}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Activity Timeline / Audit Trail */}
              <div>
                <h3 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                  Incident Activity History & Timeline:
                </h3>
                <div className="timeline-list">
                  {(selectedTicket.activity_history || []).map((entry, idx) => (
                    <div key={idx} className="timeline-entry">
                      <div className="timeline-dot"></div>
                      <div className="timeline-meta">
                        {new Date(entry.timestamp).toLocaleString()} • <strong>{entry.actor}</strong> ({entry.action})
                      </div>
                      <div className="timeline-text">{entry.note}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setSelectedTicket(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ====================================================================
          MODAL 3: KNOWLEDGE BASE ARTICLE READER
         ==================================================================== */}
      {selectedArticle && (
        <div className="modal-overlay" onClick={() => setSelectedArticle(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '700px' }}>
            <div className="modal-header">
              <div>
                <span className="category-tag">{selectedArticle.category}</span>
                <span style={{ margin: '0 0.5rem', color: 'var(--text-muted)' }}>•</span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>⏱️ {selectedArticle.read_time}</span>
              </div>
              <button
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text-muted)' }}
                onClick={() => setSelectedArticle(null)}
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.75rem' }}>
                {selectedArticle.title}
              </h2>
              <div style={{ display: 'flex', gap: '0.35rem', marginBottom: '1.25rem' }}>
                {selectedArticle.tags.map((t) => (
                  <span key={t} className="kb-pill">
                    #{t}
                  </span>
                ))}
              </div>

              <div style={{ backgroundColor: 'var(--bg-surface-alt)', padding: '1.25rem', borderRadius: 'var(--radius-md)', fontSize: '0.9rem', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                {selectedArticle.content}
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setSelectedArticle(null)}>
                Close Article
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
