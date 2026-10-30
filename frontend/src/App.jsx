import React, { useState, useEffect, useRef } from 'react';
import './index.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const CATEGORIES = ['Hardware', 'Software', 'Network', 'Access', 'Other'];
const PRIORITIES = ['Low', 'Medium', 'High', 'Critical'];
const STATUSES = ['Open', 'In Progress', 'Resolved', 'Closed'];
const AGENTS = ['Unassigned', 'Sarah Chen', 'Alex Morgan', 'David Miller', 'Priya Sharma'];

// Three defined personas representing the required roles
const PERSONAS = [
  { id: 'usr-employee', name: 'Alex Morgan', email: 'alex.morgan@company.com', role: 'employee', title: 'Senior Software Engineer' },
  { id: 'usr-agent', name: 'Sarah Chen', email: 'sarah.chen@company.com', role: 'support_agent', title: 'IT Support Lead' },
  { id: 'usr-admin', name: 'Marcus Vance', email: 'marcus.vance@company.com', role: 'administrator', title: 'Global IT Administrator' },
];

function App() {
  // User Identity & Persona
  const [currentUser, setCurrentUser] = useState(PERSONAS[1]); // Default to Sarah Chen (Support Agent)

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

  // Service Requests & Catalogue State
  const [catalogItems, setCatalogItems] = useState([]);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [serviceRequests, setServiceRequests] = useState([]);
  const [requestsLoading, setRequestsLoading] = useState(false);
  const [showCatalogModal, setShowCatalogModal] = useState(false);
  const [selectedCatalogItem, setSelectedCatalogItem] = useState(null);
  const [reqJustification, setReqJustification] = useState('');
  const [reqDescription, setReqDescription] = useState('');
  const [reqSubmitting, setReqSubmitting] = useState(false);
  const [reqError, setReqError] = useState(null);
  const [reqSuccess, setReqSuccess] = useState(null);
  const [filterReqStatus, setFilterReqStatus] = useState('ALL');

  // Work Timers & Timeline State
  const [workSessions, setWorkSessions] = useState([]);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [activeTimer, setActiveTimer] = useState(null); // { ticket_id, ticket_number, started_at }
  const [elapsedTimerSeconds, setElapsedTimerSeconds] = useState(0);
  const [timerActionLoading, setTimerActionLoading] = useState(false);

  // Self-Heal Diagnostics State
  const [diagnosticsReport, setDiagnosticsReport] = useState(null);
  const [diagnosticsLoading, setDiagnosticsLoading] = useState(false);

  // ServiceNow Integration State
  const [serviceNowStatus, setServiceNowStatus] = useState(null);
  const [serviceNowLoading, setServiceNowLoading] = useState(false);
  const [syncingTicketId, setSyncingTicketId] = useState(null);
  const [serviceNowSyncSuccess, setServiceNowSyncSuccess] = useState(null);

  // KB Articles & Authoring State
  const [kbArticles, setKbArticles] = useState([]);
  const [kbLoading, setKbLoading] = useState(false);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [kbQuestion, setKbQuestion] = useState('');
  const [kbAskLoading, setKbAskLoading] = useState(false);
  const [kbAskError, setKbAskError] = useState(null);
  const [kbAskResult, setKbAskResult] = useState(null);
  const [showCreateKbModal, setShowCreateKbModal] = useState(false);
  const [kbTitle, setKbTitle] = useState('');
  const [kbCategory, setKbCategory] = useState('Software');
  const [kbExcerpt, setKbExcerpt] = useState('');
  const [kbContent, setKbContent] = useState('');
  const [kbTags, setKbTags] = useState('');
  const [kbSubmitting, setKbSubmitting] = useState(false);
  const [kbCreateSuccess, setKbCreateSuccess] = useState(null);
  const [kbCreateError, setKbCreateError] = useState(null);

  // Conversational Chat State (All-Rounder Assistant)
  const [chatMessages, setChatMessages] = useState([]); // { role, content, sources, has_answer, generation_mode, intent, action_proposed, action_result }
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState(null);
  const chatEndRef = useRef(null);

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
  const [createRequester, setCreateRequester] = useState(currentUser.name);
  const [createDescription, setCreateDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [createError, setCreateError] = useState(null);
  const [createSuccess, setCreateSuccess] = useState(null);

  // Incident Details & Lifecycle Modal
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [updatingTicket, setUpdatingTicket] = useState(false);
  const [ticketTimerData, setTicketTimerData] = useState(null);

  // Sync requester field and isolate chat session when persona changes
  useEffect(() => {
    setCreateRequester(currentUser.name);
    setChatMessages([]);
    setChatInput('');
    setChatError(null);
  }, [currentUser]);

  // Auth headers generator helper
  const getAuthHeaders = () => ({
    'Content-Type': 'application/json',
    'X-User-Name': currentUser.name,
    'X-User-Role': currentUser.role,
    'X-User-Email': currentUser.email,
  });

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

  // Active Timer Ticking Hook
  useEffect(() => {
    if (!activeTimer) {
      setElapsedTimerSeconds(0);
      return;
    }
    const updateElapsed = () => {
      const start = new Date(activeTimer.started_at).getTime();
      const now = Date.now();
      setElapsedTimerSeconds(Math.max(0, Math.floor((now - start) / 1000)));
    };
    updateElapsed();
    const interval = setInterval(updateElapsed, 1000);
    return () => clearInterval(interval);
  }, [activeTimer]);

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

  // Fetch ServiceNow integration status
  const fetchServiceNowStatus = async (live = false) => {
    setServiceNowLoading(true);
    try {
      const url = live
        ? `${API_BASE_URL}/api/servicenow/status?check_live=true`
        : `${API_BASE_URL}/api/servicenow/status`;
      const res = await fetch(url, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setServiceNowStatus(data);
      }
    } catch (e) {
      console.warn('ServiceNow status fetch failed:', e);
    } finally {
      setServiceNowLoading(false);
    }
  };

  // Fetch Tickets
  const fetchTickets = async () => {
    setTicketsLoading(true);
    setTicketsError(null);
    try {
      let url = `${API_BASE_URL}/api/tickets`;
      if (activeTab === 'my_tickets' && currentUser.role === 'employee') {
        url += `?requester=${encodeURIComponent(currentUser.name)}`;
      }
      const res = await fetch(url, { headers: getAuthHeaders() });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `HTTP Error ${res.status}`);
      }
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

  // Fetch Service Catalog
  const fetchCatalog = async () => {
    setCatalogLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/service-catalog`);
      if (res.ok) {
        const data = await res.json();
        setCatalogItems(data);
      }
    } catch (e) {
      console.warn('Catalog fetch failed:', e);
    } finally {
      setCatalogLoading(false);
    }
  };

  // Fetch Service Requests
  const fetchServiceRequests = async () => {
    setRequestsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/service-requests`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setServiceRequests(data);
      }
    } catch (e) {
      console.warn('Service requests fetch failed:', e);
    } finally {
      setRequestsLoading(false);
    }
  };

  // Fetch Work Sessions (Timeline)
  const fetchWorkSessions = async () => {
    setTimelineLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/work-sessions`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setWorkSessions(data);
      }
    } catch (e) {
      console.warn('Work sessions fetch failed:', e);
    } finally {
      setTimelineLoading(false);
    }
  };

  // Fetch active timer for current user
  const fetchActiveTimer = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/tickets/active-timer?agent=${encodeURIComponent(currentUser.name)}`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setActiveTimer(data.active_timer);
      }
    } catch (e) {
      console.warn('Active timer fetch failed:', e);
    }
  };

  // Fetch ticket-specific timer status
  const fetchTicketTimerStatus = async (ticketId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/tickets/${ticketId}/timer-status?agent=${encodeURIComponent(currentUser.name)}`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setTicketTimerData(data);
      }
    } catch (e) {
      console.warn('Ticket timer status fetch failed:', e);
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
    fetchCatalog();
    fetchServiceRequests();
    fetchWorkSessions();
    fetchActiveTimer();
    fetchServiceNowStatus();
  }, []);

  // When persona changes or activeTab changes to my_tickets, re-fetch
  useEffect(() => {
    fetchTickets();
    fetchActiveTimer();
  }, [currentUser, activeTab]);

  // When selectedTicket changes, load its timer status
  useEffect(() => {
    if (selectedTicket) {
      fetchTicketTimerStatus(selectedTicket.id);
    } else {
      setTicketTimerData(null);
    }
  }, [selectedTicket]);

  // Refresh all
  const handleGlobalRefresh = () => {
    fetchHealth();
    fetchTickets();
    fetchStats();
    fetchServiceRequests();
    fetchWorkSessions();
    fetchActiveTimer();
    if (activeTab === 'kb') fetchKB();
  };

  // ── Work Timer Start/Stop Handlers ──────────────────────────────────────────
  const handleStartTimer = async (ticketId) => {
    setTimerActionLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/tickets/${ticketId}/work-sessions/start`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ agent: currentUser.name }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error ${res.status}`);
      }
      const data = await res.json();
      setActiveTimer(data);
      await fetchTicketTimerStatus(ticketId);
      await fetchWorkSessions();
    } catch (err) {
      alert(`⚠️ Cannot start timer: ${err.message}`);
    } finally {
      setTimerActionLoading(false);
    }
  };

  const handleStopTimer = async (ticketId) => {
    setTimerActionLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/tickets/${ticketId}/work-sessions/stop`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ agent: currentUser.name }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error ${res.status}`);
      }
      const data = await res.json();
      setActiveTimer(null);
      await fetchTicketTimerStatus(ticketId);
      await fetchWorkSessions();
      alert(`✅ Work session stopped. Duration: ${data.duration_minutes} minutes recorded.`);
    } catch (err) {
      alert(`⚠️ Cannot stop timer: ${err.message}`);
    } finally {
      setTimerActionLoading(false);
    }
  };

  // ── Service Requests Handlers ───────────────────────────────────────────────
  const handleSubmitServiceRequest = async (e) => {
    e.preventDefault();
    setReqError(null);
    setReqSuccess(null);
    if (!selectedCatalogItem) return;
    if (reqJustification.trim().length < 5) {
      setReqError('Please provide a valid business justification (min 5 characters).');
      return;
    }
    setReqSubmitting(true);
    try {
      const payload = {
        catalog_item_id: selectedCatalogItem.id,
        item_name: selectedCatalogItem.name,
        category: selectedCatalogItem.category,
        requester: currentUser.name,
        requester_email: currentUser.email,
        business_justification: reqJustification.trim(),
        additional_details: reqDescription.trim(),
      };
      const res = await fetch(`${API_BASE_URL}/api/service-requests`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP Error ${res.status}`);
      }
      const data = await res.json();
      setReqSuccess(`Request ${data.request_number} submitted successfully!`);
      setReqJustification('');
      setReqDescription('');
      fetchServiceRequests();
      setTimeout(() => {
        setShowCatalogModal(false);
        setReqSuccess(null);
      }, 1500);
    } catch (err) {
      setReqError(err.message || 'Failed to submit service request.');
    } finally {
      setReqSubmitting(false);
    }
  };

  const handleUpdateServiceRequestStatus = async (requestId, newStatus, reason = '') => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/service-requests/${requestId}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          status: newStatus,
          rejection_reason: reason,
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP Error ${res.status}`);
      }
      await fetchServiceRequests();
    } catch (err) {
      alert(`⚠️ Action failed: ${err.message}`);
    }
  };

  // ── Self-Heal Diagnostics Runner ───────────────────────────────────────────
  const handleRunDiagnostics = async () => {
    setDiagnosticsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/diagnostics/run`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
      const data = await res.json();
      setDiagnosticsReport(data);
    } catch (err) {
      alert(`Diagnostics run failed: ${err.message}`);
    } finally {
      setDiagnosticsLoading(false);
    }
  };

  // ── ServiceNow Sync Handler ────────────────────────────────────────────────
  const handleSyncServiceNow = async (ticketId) => {
    setSyncingTicketId(ticketId);
    setServiceNowSyncSuccess(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/servicenow/sync/${ticketId}`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP Error ${res.status}`);
      }
      const result = await res.json();
      setServiceNowSyncSuccess(result);
      if (result.synced) {
        if (selectedTicket && selectedTicket.id === ticketId) {
          setSelectedTicket((prev) => ({
            ...prev,
            servicenow_sys_id: result.sys_id,
            servicenow_incident_number: result.number,
            servicenow_mode: result.mode,
          }));
        }
        await fetchTickets();
      } else {
        alert(`ServiceNow Sync Notice: ${result.message || 'Sync could not be completed.'}`);
      }
    } catch (err) {
      alert(`ServiceNow Sync Failed: ${err.message}`);
    } finally {
      setSyncingTicketId(null);
    }
  };

  // ── Knowledge Authoring Handler ────────────────────────────────────────────
  const handleCreateKbArticle = async (e) => {
    e.preventDefault();
    setKbCreateError(null);
    setKbCreateSuccess(null);
    if (kbTitle.trim().length < 5 || kbContent.trim().length < 20) {
      setKbCreateError('Title must be at least 5 chars and content at least 20 chars.');
      return;
    }
    setKbSubmitting(true);
    try {
      const tagsArray = kbTags
        .split(',')
        .map((t) => t.trim().toLowerCase())
        .filter(Boolean);
      const payload = {
        title: kbTitle.trim(),
        category: kbCategory,
        excerpt: kbExcerpt.trim() || kbContent.trim().slice(0, 100) + '...',
        content: kbContent.trim(),
        tags: tagsArray.length > 0 ? tagsArray : ['general'],
        read_time: '2 min read',
      };
      const res = await fetch(`${API_BASE_URL}/api/kb/articles`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP Error ${res.status}`);
      }
      const created = await res.json();
      setKbCreateSuccess(`Article "${created.title}" published & indexed into vector database!`);
      setKbTitle('');
      setKbExcerpt('');
      setKbContent('');
      setKbTags('');
      await fetchKB();
      setTimeout(() => {
        setShowCreateKbModal(false);
        setKbCreateSuccess(null);
      }, 1500);
    } catch (err) {
      setKbCreateError(err.message || 'Failed to create article.');
    } finally {
      setKbSubmitting(false);
    }
  };

  // ── Ask Knowledge Base handler ─────────────────────────────────────────────
  const handleAskKnowledgeBase = async (e) => {
    e.preventDefault();
    const question = kbQuestion.trim();
    if (question.length < 3) {
      setKbAskError('Enter at least 3 characters describing the IT issue.');
      return;
    }
    setKbAskError(null);
    setKbAskLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/kb/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned error ${res.status}`);
      }
      const data = await res.json();
      setKbAskResult(data);
    } catch (err) {
      setKbAskResult(null);
      setKbAskError(err.message || 'Knowledge search failed.');
    } finally {
      setKbAskLoading(false);
    }
  };

  // ── All-Rounder Chatbot Handler ────────────────────────────────────────────
  const handleChatSend = async (overrideMessage) => {
    const text = (overrideMessage !== undefined ? overrideMessage : chatInput).trim();
    if (!text || text.length < 2 || chatLoading) return;

    // Append user message immediately
    const userMsg = { role: 'user', content: text };
    const nextMessages = [...chatMessages, userMsg];
    setChatMessages(nextMessages);
    setChatInput('');
    setChatError(null);
    setChatLoading(true);

    const historyForApi = chatMessages
      .slice(-20)
      .map((m) => ({ role: m.role, content: m.content.slice(0, 2000) }));

    try {
      const res = await fetch(`${API_BASE_URL}/api/kb/chat`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ message: text, history: historyForApi }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error ${res.status}`);
      }
      const data = await res.json();
      const assistantMsg = {
        role: 'assistant',
        content: data.message,
        sources: data.matched_articles || [],
        has_answer: data.has_answer,
        generation_mode: data.generation_mode,
        llm_used: data.llm_used,
        intent: data.intent,
        action_proposed: data.action_proposed,
        action_result: data.action_result,
      };
      setChatMessages((prev) => [...prev, assistantMsg]);

      // If an action was completed, refresh the tickets or requests automatically
      if (data.action_result?.type === 'incident_created') {
        fetchTickets();
        fetchStats();
      } else if (data.action_result?.type === 'service_request_created') {
        fetchServiceRequests();
      }
    } catch (err) {
      setChatError(err.message || 'The assistant could not respond. Please try again.');
    } finally {
      setChatLoading(false);
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    }
  };

  const handleChatKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleChatSend();
    }
  };

  const handleNewChat = () => {
    setChatMessages([]);
    setChatInput('');
    setChatError(null);
  };

  // ── Create Ticket Handler ───────────────────────────────────────────────────
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
        requester: createRequester,
      };

      const res = await fetch(`${API_BASE_URL}/api/tickets`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP Error ${res.status}`);
      }

      const created = await res.json();
      setCreateSuccess(`Incident ${created.ticket_number} created successfully.`);

      // Reset form
      setCreateTitle('');
      setCreateDescription('');

      // Refresh list & stats
      await fetchTickets();
      await fetchStats();

      setTimeout(() => {
        setShowCreateModal(false);
        setCreateSuccess(null);
      }, 1200);
    } catch (err) {
      setCreateError(err.message || 'Failed to submit incident.');
    } finally {
      setSubmitting(false);
    }
  };

  // ── Update Ticket Status Handler ───────────────────────────────────────────
  const handleUpdateTicketStatus = async (ticketId, newStatus, resolutionNotes = '') => {
    setUpdatingTicket(true);
    try {
      const payload = {
        status: newStatus,
        updated_by: `${currentUser.name} (${currentUser.role})`,
      };
      if (resolutionNotes) {
        payload.resolution_notes = resolutionNotes;
      }

      const res = await fetch(`${API_BASE_URL}/api/tickets/${ticketId}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
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
      alert(`Failed to update status: ${err.message}`);
    } finally {
      setUpdatingTicket(false);
    }
  };

  // ── Update Assignee Handler ────────────────────────────────────────────────
  const handleUpdateAssignee = async (ticketId, newAssignee) => {
    setUpdatingTicket(true);
    try {
      const payload = {
        assignee: newAssignee,
        updated_by: `${currentUser.name} (${currentUser.role})`,
      };

      const res = await fetch(`${API_BASE_URL}/api/tickets/${ticketId}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
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

  // ── Filtering & Sorting Logic ──────────────────────────────────────────────
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

    // Role-based My Tickets filtering
    if (activeTab === 'my_tickets') {
      if (currentUser.role === 'employee') {
        const isRequester = (t.requester || '').toLowerCase().includes(currentUser.name.toLowerCase().split(' ')[0]) ||
                            (t.requester || '').toLowerCase().includes('operations');
        if (!isRequester) return false;
      } else if (currentUser.role === 'support_agent') {
        if (t.assignee !== currentUser.name) return false;
      }
    }
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

  // Helper format seconds
  const formatSeconds = (sec) => {
    const mins = Math.floor(sec / 60);
    const s = sec % 60;
    return `${mins}m ${s < 10 ? '0' : ''}${s}s`;
  };

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
            title="Assigned Work Items & My Requests"
          >
            <span className="nav-icon">👤</span>
            {!sidebarCollapsed && (
              <span>{currentUser.role === 'employee' ? 'My Tickets' : 'Assigned Queue'}</span>
            )}
          </div>

          <div
            className={`nav-item ${activeTab === 'service_requests' ? 'active' : ''}`}
            onClick={() => setActiveTab('service_requests')}
            title="Service Catalogue & Requests"
          >
            <span className="nav-icon">📦</span>
            {!sidebarCollapsed && <span>Service Requests</span>}
          </div>

          <div
            className={`nav-item ${activeTab === 'timeline' ? 'active' : ''}`}
            onClick={() => setActiveTab('timeline')}
            title="Ticket Work Sessions & Timeline"
          >
            <span className="nav-icon">⏱️</span>
            {!sidebarCollapsed && <span>Work Timeline</span>}
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
            title="Knowledge Base & All-Rounder AI Assistant"
          >
            <span className="nav-icon">📚</span>
            {!sidebarCollapsed && <span>AI Knowledge & Chat</span>}
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
            title="Self-Healing System Diagnostics"
          >
            <span className="nav-icon">⚙️</span>
            {!sidebarCollapsed && <span>Self-Heal Diagnostics</span>}
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
              {activeTab === 'my_tickets' && (currentUser.role === 'employee' ? 'My Submitted Tickets' : 'Assigned Incident Queue')}
              {activeTab === 'service_requests' && 'IT Service Catalogue & Requests'}
              {activeTab === 'timeline' && 'Ticket Work Sessions & Timeline'}
              {activeTab === 'kanban' && 'Incident Kanban Analyzer'}
              {activeTab === 'kb' && 'Knowledge Base & AI Assistant'}
              {activeTab === 'reports' && 'Performance & SLA Reports'}
              {activeTab === 'diagnostics' && 'Self-Healing IT Diagnostics & Health'}
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
                placeholder="Search by ID, title, assignee..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            {/* Active Work Timer Banner (if running) */}
            {activeTimer && (
              <div
                className="active-timer-pill"
                onClick={() => {
                  const match = tickets.find((t) => t.id === activeTimer.ticket_id || t.ticket_number === activeTimer.ticket_number);
                  if (match) setSelectedTicket(match);
                }}
                title="Click to view ticket with active work timer"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.45rem',
                  backgroundColor: '#fef3c7',
                  border: '1px solid #fde047',
                  color: '#92400e',
                  padding: '0.35rem 0.75rem',
                  borderRadius: '9999px',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  animation: 'pulse 2s infinite',
                }}
              >
                <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#d97706', display: 'inline-block' }}></span>
                <span>Active: {activeTimer.ticket_number} ({formatSeconds(elapsedTimerSeconds)})</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleStopTimer(activeTimer.ticket_id);
                  }}
                  style={{
                    backgroundColor: '#d97706',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '0.15rem 0.4rem',
                    fontSize: '0.7rem',
                    cursor: 'pointer',
                  }}
                >
                  Stop
                </button>
              </div>
            )}

            {/* Backend Connectivity Status Pill */}
            <div
              className="status-tag"
              style={{
                backgroundColor:
                  healthData?.status === 'healthy'
                    ? '#ecfdf5'
                    : healthData?.status === 'degraded'
                    ? '#fef3c7'
                    : '#fff1f2',
                color:
                  healthData?.status === 'healthy'
                    ? '#059669'
                    : healthData?.status === 'degraded'
                    ? '#b45309'
                    : '#e11d48',
                borderColor:
                  healthData?.status === 'healthy'
                    ? '#a7f3d0'
                    : healthData?.status === 'degraded'
                    ? '#fde68a'
                    : '#fecdd3',
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
                  backgroundColor:
                    healthData?.status === 'healthy'
                      ? '#10b981'
                      : healthData?.status === 'degraded'
                      ? '#f59e0b'
                      : '#f43f5e',
                }}
              ></span>
              <span>
                {healthData?.status === 'healthy'
                  ? `Healthy (${latency || 12}ms)`
                  : healthData?.status === 'degraded'
                  ? 'Atlas Offline'
                  : 'Offline'}
              </span>
            </div>

            {/* Primary Action: Create Incident */}
            <button
              className="btn-primary"
              onClick={() => setShowCreateModal(true)}
            >
              <span>+</span>
              <span>New Incident</span>
            </button>

            {/* Persona Switcher (Local Testing / Demo) */}
            <div className="persona-switcher-box" title="Local Persona Switcher for testing identity & authorization">
              <span className="persona-badge-tag">Demo Persona</span>
              <select
                className="persona-select"
                value={currentUser.id}
                onChange={(e) => {
                  const selected = PERSONAS.find((p) => p.id === e.target.value);
                  if (selected) setCurrentUser(selected);
                }}
              >
                {PERSONAS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.role.replace('_', ' ').toUpperCase()})
                  </option>
                ))}
              </select>
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
              {/* Atlas Disconnected Warning Banner */}
              {(healthData?.status === 'degraded' || storageStatus?.mode === 'atlas_unreachable' || ticketsError) && (
                <div style={{
                  backgroundColor: '#fffbeb',
                  border: '1px solid #fde68a',
                  color: '#92400e',
                  padding: '0.85rem 1.25rem',
                  borderRadius: '8px',
                  marginBottom: '1.25rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '0.875rem',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <span style={{ fontSize: '1.2rem' }}>⚠️</span>
                    <span>
                      <strong>MongoDB Atlas Offline:</strong> Unable to reach cluster.
                      Please ensure your current IP address is added to the MongoDB Atlas Network Access whitelist.
                    </span>
                  </div>
                  <button
                    className="btn-secondary"
                    onClick={() => { fetchHealth(); fetchStorage(); fetchTickets(); fetchStats(); }}
                    style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem', whiteSpace: 'nowrap', marginLeft: '1rem' }}
                  >
                    Retry Connection
                  </button>
                </div>
              )}

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
                    <div className="kpi-value" style={{ color: '#e11d48' }}>
                      {(stats?.by_priority?.['High'] || 0) + (stats?.by_priority?.['Critical'] || 0)}
                    </div>
                  </div>
                  <div className="kpi-icon-bubble" style={{ backgroundColor: '#fff1f2', color: '#e11d48' }}>
                    🔥
                  </div>
                </div>

                <div className="kpi-card">
                  <div>
                    <div className="kpi-label">Pending Service Requests</div>
                    <div className="kpi-value" style={{ color: '#d97706' }}>
                      {serviceRequests.filter((r) => r.status === 'Pending Approval' || r.status === 'Submitted').length}
                    </div>
                  </div>
                  <div className="kpi-icon-bubble" style={{ backgroundColor: '#fef3c7', color: '#d97706' }}>
                    📦
                  </div>
                </div>
              </div>

              {/* Split Sections */}
              <div className="dashboard-split-grid">
                {/* Priority Distribution */}
                <div className="surface-card">
                  <div className="card-title-row">
                    <h2 className="card-heading">
                      <span>📊</span> Priority Breakdown
                    </h2>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Real-time Distribution</span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                    {PRIORITIES.map((p) => {
                      const count = stats?.by_priority?.[p] || 0;
                      const percentage = stats?.total ? Math.round((count / stats.total) * 100) : 0;
                      const colorMap = {
                        Critical: '#e11d48',
                        High: '#ea580c',
                        Medium: '#d97706',
                        Low: '#059669',
                      };
                      return (
                        <div key={p}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.825rem', marginBottom: '0.3rem' }}>
                            <span style={{ fontWeight: 600 }}>{p}</span>
                            <span style={{ color: 'var(--text-muted)' }}>{count} ({percentage}%)</span>
                          </div>
                          <div style={{ height: '7px', backgroundColor: '#f1f5f9', borderRadius: '4px', overflow: 'hidden' }}>
                            <div
                              style={{
                                height: '100%',
                                width: `${percentage}%`,
                                backgroundColor: colorMap[p] || '#64748b',
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

                {/* Category Distribution */}
                <div className="surface-card">
                  <div className="card-title-row">
                    <h2 className="card-heading">
                      <span>🏷️</span> Incident by Category
                    </h2>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Top Root Causes</span>
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
              VIEW B: INCIDENTS TABLE & MY TICKETS
             ==================================================================== */}
          {(activeTab === 'incidents' || activeTab === 'my_tickets') && (
            <div className="surface-card">
              {/* Persona Context Banner */}
              {activeTab === 'my_tickets' && (
                <div style={{ padding: '0.75rem 1rem', backgroundColor: '#eff6ff', borderRadius: '6px', marginBottom: '1rem', border: '1px solid #bfdbfe', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong>Viewing My Tickets: </strong>
                    {currentUser.role === 'employee' && `Submitted by ${currentUser.name} (Employee Role)`}
                    {currentUser.role === 'support_agent' && `Assigned to ${currentUser.name} (Support Agent Queue)`}
                    {currentUser.role === 'administrator' && `Full Access (Administrator View)`}
                  </div>
                  <span className="category-tag">{currentUser.role.replace('_', ' ').toUpperCase()}</span>
                </div>
              )}

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
                      <option key={c} value={c}>{c}</option>
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
                      <option key={p} value={p}>{p} Priority</option>
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
                      <option key={s} value={s}>{s}</option>
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
                      <option key={a} value={a}>{a}</option>
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
                        <th>Requester</th>
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
                          <td>{ticket.assignee}</td>
                          <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{ticket.requester}</td>
                          <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
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
              VIEW C: SERVICE REQUESTS & SERVICE CATALOGUE
             ==================================================================== */}
          {activeTab === 'service_requests' && (
            <div>
              {/* Catalogue Header & Description */}
              <div className="surface-card" style={{ marginBottom: '1.25rem' }}>
                <div className="card-title-row">
                  <div>
                    <h2 className="card-heading">
                      <span>📦</span> IT Service Catalogue
                    </h2>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                      Request pre-approved developer tools, cloud environments, access privileges, and enterprise hardware.
                    </p>
                  </div>
                  <span className="category-tag">Role: {currentUser.role.replace('_', ' ').toUpperCase()}</span>
                </div>

                {/* Catalogue Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
                  {catalogItems.map((item) => (
                    <div
                      key={item.id}
                      className="surface-card"
                      style={{
                        padding: '1rem',
                        border: '1px solid var(--border)',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                          <span className="category-tag">{item.category}</span>
                          {item.requires_approval ? (
                            <span style={{ fontSize: '0.7rem', color: '#d97706', backgroundColor: '#fef3c7', padding: '0.15rem 0.4rem', borderRadius: '4px', fontWeight: 600 }}>
                              Approval Req.
                            </span>
                          ) : (
                            <span style={{ fontSize: '0.7rem', color: '#059669', backgroundColor: '#ecfdf5', padding: '0.15rem 0.4rem', borderRadius: '4px', fontWeight: 600 }}>
                              Pre-approved
                            </span>
                          )}
                        </div>
                        <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.35rem' }}>{item.name}</h3>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4, marginBottom: '0.75rem' }}>
                          {item.description}
                        </p>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                          SLA Fulfillment: <strong>{item.estimated_hours}h</strong>
                        </div>
                      </div>

                      <button
                        className="btn-primary"
                        style={{ width: '100%', fontSize: '0.8rem', padding: '0.45rem' }}
                        onClick={() => {
                          setSelectedCatalogItem(item);
                          setShowCatalogModal(true);
                        }}
                      >
                        Request This Service
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Service Requests List */}
              <div className="surface-card">
                <div className="card-title-row">
                  <h2 className="card-heading">
                    <span>📋</span> Submitted Service Requests
                  </h2>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <select
                      className="select-filter"
                      value={filterReqStatus}
                      onChange={(e) => setFilterReqStatus(e.target.value)}
                    >
                      <option value="ALL">All Statuses</option>
                      <option value="Submitted">Submitted</option>
                      <option value="Pending Approval">Pending Approval</option>
                      <option value="Approved">Approved</option>
                      <option value="In Progress">In Progress</option>
                      <option value="Fulfilled">Fulfilled</option>
                      <option value="Rejected">Rejected</option>
                      <option value="Cancelled">Cancelled</option>
                    </select>
                    <button className="btn-secondary" onClick={fetchServiceRequests}>
                      ↻ Refresh
                    </button>
                  </div>
                </div>

                {serviceRequests.length === 0 ? (
                  <div className="empty-box">
                    <div className="empty-icon">📦</div>
                    <h3>No Service Requests Yet</h3>
                    <p style={{ fontSize: '0.85rem' }}>Select an item from the catalogue above or request software via the AI chat assistant.</p>
                  </div>
                ) : (
                  <div className="table-responsive">
                    <table className="itsm-table">
                      <thead>
                        <tr>
                          <th>Request ID</th>
                          <th>Requested Item</th>
                          <th>Category</th>
                          <th>Requester</th>
                          <th>Business Justification</th>
                          <th>Status</th>
                          <th>Approver</th>
                          <th>Submitted</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {serviceRequests
                          .filter((req) => filterReqStatus === 'ALL' || req.status === filterReqStatus)
                          .map((req) => (
                            <tr key={req.id}>
                              <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--primary)' }}>
                                {req.request_number}
                              </td>
                              <td style={{ fontWeight: 600 }}>{req.item_name}</td>
                              <td><span className="category-tag">{req.category}</span></td>
                              <td>{req.requester}</td>
                              <td style={{ fontSize: '0.8rem', maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={req.business_justification}>
                                {req.business_justification}
                              </td>
                              <td>
                                <span className={`status-tag ${req.status.replace(/\s+/g, '-')}`}>
                                  {req.status}
                                </span>
                              </td>
                              <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                                {req.approver || '—'}
                              </td>
                              <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                {new Date(req.created_at).toLocaleDateString()}
                              </td>
                              <td>
                                <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                                  {/* Admin & Support Agent Approval actions */}
                                  {(currentUser.role === 'administrator' || currentUser.role === 'support_agent') && (req.status === 'Submitted' || req.status === 'Pending Approval') && (
                                    <>
                                      <button
                                        className="btn-primary"
                                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.72rem', backgroundColor: '#059669', borderColor: '#059669' }}
                                        onClick={() => handleUpdateServiceRequestStatus(req.id, 'Approved')}
                                        title="Approve this service request"
                                      >
                                        ✓ Approve
                                      </button>
                                      <button
                                        className="btn-secondary"
                                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.72rem', color: '#e11d48' }}
                                        onClick={() => {
                                          const reason = prompt('Rejection Reason:') || 'Policy denial';
                                          handleUpdateServiceRequestStatus(req.id, 'Rejected', reason);
                                        }}
                                        title="Reject this service request"
                                      >
                                        ✕ Reject
                                      </button>
                                    </>
                                  )}

                                  {/* Fulfillment action for support/admin */}
                                  {(currentUser.role === 'administrator' || currentUser.role === 'support_agent') && req.status === 'Approved' && (
                                    <button
                                      className="btn-primary"
                                      style={{ padding: '0.25rem 0.5rem', fontSize: '0.72rem' }}
                                      onClick={() => handleUpdateServiceRequestStatus(req.id, 'Fulfilled')}
                                    >
                                      Mark Fulfilled
                                    </button>
                                  )}

                                  {/* Employee cancel action */}
                                  {currentUser.role === 'employee' && (req.status === 'Submitted' || req.status === 'Pending Approval') && (
                                    <button
                                      className="btn-secondary"
                                      style={{ padding: '0.25rem 0.5rem', fontSize: '0.72rem' }}
                                      onClick={() => handleUpdateServiceRequestStatus(req.id, 'Cancelled', 'Cancelled by requester')}
                                    >
                                      Cancel
                                    </button>
                                  )}
                                </div>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ====================================================================
              VIEW D: WORK SESSIONS & TICKET TIMELINE
             ==================================================================== */}
          {activeTab === 'timeline' && (
            <div>
              {/* Active Timer Card */}
              {activeTimer ? (
                <div className="surface-card" style={{ marginBottom: '1.25rem', backgroundColor: '#fef3c7', border: '1px solid #fde047' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontSize: '0.8rem', color: '#92400e', fontWeight: 600 }}>Active Work Session in Progress</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#78350f', marginTop: '0.2rem' }}>
                        {activeTimer.ticket_number} — Elapsed: {formatSeconds(elapsedTimerSeconds)}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#b45309', marginTop: '0.2rem' }}>
                        Agent: <strong>{activeTimer.agent}</strong> | Started at: {new Date(activeTimer.started_at).toLocaleTimeString()}
                      </div>
                    </div>
                    <button
                      className="btn-primary"
                      style={{ backgroundColor: '#d97706', borderColor: '#d97706' }}
                      disabled={timerActionLoading}
                      onClick={() => handleStopTimer(activeTimer.ticket_id)}
                    >
                      {timerActionLoading ? 'Stopping...' : '⏹️ Stop Work Session'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="surface-card" style={{ marginBottom: '1.25rem', padding: '1rem', backgroundColor: '#f8fafc' }}>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    ⏱️ No active timer running for <strong>{currentUser.name}</strong>. Open any incident and click <strong>"Start Work"</strong> to begin tracking real work duration.
                  </span>
                </div>
              )}

              {/* Timeline Header & Sessions Table */}
              <div className="surface-card">
                <div className="card-title-row">
                  <div>
                    <h2 className="card-heading">
                      <span>⏱️</span> Support Agent Work Session History
                    </h2>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                      Real recorded time intervals tracked per agent and ticket. Duration is strictly calculated from recorded start/stop timestamps.
                    </p>
                  </div>
                  <button className="btn-secondary" onClick={fetchWorkSessions}>
                    ↻ Refresh
                  </button>
                </div>

                {workSessions.length === 0 ? (
                  <div className="empty-box">
                    <div className="empty-icon">⏳</div>
                    <h3>No Recorded Work Sessions</h3>
                    <p style={{ fontSize: '0.85rem' }}>Start working on an incident ticket to record your first session.</p>
                  </div>
                ) : (
                  <div className="table-responsive">
                    <table className="itsm-table">
                      <thead>
                        <tr>
                          <th>Ticket ID</th>
                          <th>Agent</th>
                          <th>Start Time</th>
                          <th>End Time</th>
                          <th>Duration</th>
                          <th>Status</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {workSessions.map((session) => (
                          <tr key={session.id}>
                            <td
                              className="ticket-number-cell"
                              onClick={() => {
                                const match = tickets.find((t) => t.id === session.ticket_id || t.ticket_number === session.ticket_number);
                                if (match) setSelectedTicket(match);
                              }}
                              title="Click to open ticket"
                            >
                              {session.ticket_number}
                            </td>
                            <td style={{ fontWeight: 600 }}>{session.agent}</td>
                            <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                              {new Date(session.start_time).toLocaleString()}
                            </td>
                            <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                              {session.end_time ? new Date(session.end_time).toLocaleString() : 'In Progress'}
                            </td>
                            <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                              {session.is_active ? 'Active Now' : `${session.duration_minutes} min`}
                            </td>
                            <td>
                              <span className={`status-tag ${session.is_active ? 'In-Progress' : 'Resolved'}`}>
                                {session.is_active ? 'Active' : 'Completed'}
                              </span>
                            </td>
                            <td>
                              <button
                                className="btn-secondary"
                                style={{ padding: '0.25rem 0.5rem', fontSize: '0.72rem' }}
                                onClick={() => {
                                  const match = tickets.find((t) => t.id === session.ticket_id || t.ticket_number === session.ticket_number);
                                  if (match) setSelectedTicket(match);
                                }}
                              >
                                View Ticket
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ====================================================================
              VIEW E: KANBAN BOARD
             ==================================================================== */}
          {activeTab === 'kanban' && (
            <div>
              <div className="filter-action-bar" style={{ marginBottom: '1.25rem' }}>
                <div className="filter-group">
                  <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-main)' }}>
                    Workflow Columns:
                  </span>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    Track status transitions across open and closed incidents
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
                                <span className={`priority-tag ${t.priority}`}>{t.priority}</span>
                              </div>
                              <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.4rem' }}>{t.title}</div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                <span>{t.category}</span>
                                <span>{t.assignee}</span>
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
              VIEW F: KNOWLEDGE BASE & ALL-ROUNDER AI ASSISTANT
             ==================================================================== */}
          {activeTab === 'kb' && (
            <div>
              {/* Quick Assistant Feature Guide */}
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', alignSelf: 'center' }}>Try Asking:</span>
                {[
                  'I need Docker Desktop',
                  'Check status of INC-1001',
                  'Run self-heal network diagnostics',
                  'VPN keeps disconnecting',
                  'My monitor has no display signal',
                ].map((sample) => (
                  <button
                    key={sample}
                    className="btn-secondary"
                    style={{ fontSize: '0.75rem', padding: '0.2rem 0.55rem', borderRadius: '9999px' }}
                    onClick={() => handleChatSend(sample)}
                  >
                    💬 {sample}
                  </button>
                ))}
              </div>

              {/* Knowledge Base Split: Chatbot on Left, Articles on Right */}
              <div className="dashboard-split-grid" style={{ gridTemplateColumns: '1.2fr 1fr' }}>
                {/* 1. All-Rounder Chatbot Panel */}
                <div className="surface-card" style={{ display: 'flex', flexDirection: 'column', height: '680px' }}>
                  <div className="card-title-row" style={{ borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '1.3rem' }}>🤖</span>
                      <div>
                        <h2 className="card-heading" style={{ fontSize: '1rem', margin: 0 }}>HelpWise All-Rounder AI</h2>
                        <span style={{ fontSize: '0.7rem', color: '#059669', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#10b981', display: 'inline-block' }}></span>
                          FLAN-T5-small + MiniLM ChromaDB
                        </span>
                      </div>
                    </div>
                    <button className="btn-secondary" onClick={handleNewChat} style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}>
                      ↺ New Chat
                    </button>
                  </div>

                  {/* Chat message scroll area */}
                  <div style={{ flex: 1, overflowY: 'auto', padding: '1rem 0', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                    {chatMessages.length === 0 && (
                      <div style={{ textAlign: 'center', padding: '3rem 1.5rem', color: 'var(--text-muted)' }}>
                        <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>💡</div>
                        <h3 style={{ fontSize: '1rem', color: 'var(--text-main)', marginBottom: '0.4rem' }}>How can I help you today?</h3>
                        <p style={{ fontSize: '0.825rem', lineHeight: 1.5, maxWidth: '360px', margin: '0 auto' }}>
                          I can answer IT troubleshooting questions, check ticket statuses, submit service requests, run diagnostics, and log incidents.
                        </p>
                      </div>
                    )}

                    {chatMessages.map((msg, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                          gap: '0.35rem',
                        }}
                      >
                        {/* Bubble */}
                        <div
                          style={{
                            maxWidth: '88%',
                            padding: '0.75rem 1rem',
                            borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                            backgroundColor: msg.role === 'user' ? 'var(--primary)' : 'var(--bg-surface-alt)',
                            color: msg.role === 'user' ? '#fff' : 'var(--text-main)',
                            border: msg.role === 'assistant' ? '1px solid var(--border)' : 'none',
                            fontSize: '0.875rem',
                            lineHeight: 1.55,
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                          }}
                        >
                          {msg.content}
                        </div>

                        {/* Interactive Action Proposal Card (Confirm & Submit) */}
                        {msg.action_proposed && (
                          <div
                            className="chat-action-card"
                            style={{
                              maxWidth: '88%',
                              padding: '0.85rem',
                              backgroundColor: '#eff6ff',
                              border: '1px solid #bfdbfe',
                              borderRadius: '8px',
                              marginTop: '0.25rem',
                            }}
                          >
                            <div style={{ fontWeight: 700, fontSize: '0.825rem', color: '#1e40af', marginBottom: '0.35rem' }}>
                              ⚡ Proposed Action Confirmation
                            </div>
                            <div style={{ fontSize: '0.78rem', color: '#1e3a8a', lineHeight: 1.4, marginBottom: '0.6rem' }}>
                              {(msg.action_proposed.type === 'create_incident' || msg.action_proposed.type === 'create_ticket') && (
                                <>
                                  <strong>Incident Title:</strong> {msg.action_proposed.details?.title}<br />
                                  <strong>Category:</strong> {msg.action_proposed.details?.category} | <strong>Priority:</strong> {msg.action_proposed.details?.priority}
                                </>
                              )}
                              {msg.action_proposed.type === 'create_service_request' && (
                                <>
                                  <strong>Service Item:</strong> {msg.action_proposed.details?.item_name}<br />
                                  <strong>Justification:</strong> {msg.action_proposed.details?.business_justification}
                                </>
                              )}
                            </div>
                            <button
                              className="btn-primary"
                              style={{ fontSize: '0.75rem', padding: '0.3rem 0.7rem' }}
                              onClick={() => handleChatSend('Yes, confirm please')}
                            >
                              ✓ Confirm & Submit Now
                            </button>
                          </div>
                        )}

                        {/* Action Result Card */}
                        {msg.action_result && (
                          <div
                            style={{
                              maxWidth: '88%',
                              padding: '0.65rem 0.85rem',
                              backgroundColor: '#ecfdf5',
                              border: '1px solid #a7f3d0',
                              borderRadius: '8px',
                              fontSize: '0.8rem',
                              color: '#065f46',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              gap: '0.5rem',
                            }}
                          >
                            <span>✅ Record Created: <strong>{msg.action_result.record_id}</strong></span>
                            <button
                              className="btn-secondary"
                              style={{ padding: '0.2rem 0.5rem', fontSize: '0.7rem' }}
                              onClick={() => {
                                if (msg.action_result.type === 'incident_created') setActiveTab('incidents');
                                if (msg.action_result.type === 'service_request_created') setActiveTab('service_requests');
                              }}
                            >
                              View in Table
                            </button>
                          </div>
                        )}

                        {/* Assistant Source Citations */}
                        {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', paddingLeft: '0.25rem' }}>
                            Source:{' '}
                            {msg.sources.slice(0, 2).map((src, si) => (
                              <React.Fragment key={src.id}>
                                <button
                                  type="button"
                                  onClick={() => setSelectedArticle(src)}
                                  style={{ background: 'none', border: 'none', padding: 0, color: 'var(--primary)', cursor: 'pointer', textDecoration: 'underline', fontWeight: 600, fontSize: '0.75rem' }}
                                >
                                  📖 {src.title}
                                </button>
                                {si < Math.min(msg.sources.length, 2) - 1 && <span style={{ margin: '0 0.25rem' }}>·</span>}
                              </React.Fragment>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}

                    {chatLoading && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        <span>⚡ HelpWise Assistant is reasoning…</span>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>

                  {/* Chat Input Bar */}
                  <div style={{ borderTop: '1px solid var(--border)', paddingTop: '0.75rem' }}>
                    {chatError && (
                      <div style={{ fontSize: '0.75rem', color: '#e11d48', marginBottom: '0.4rem' }}>
                        ⚠️ {chatError}
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <input
                        type="text"
                        className="input-text"
                        placeholder="Ask troubleshooting, request software, check status..."
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        onKeyDown={handleChatKeyDown}
                        disabled={chatLoading}
                      />
                      <button
                        className="btn-primary"
                        onClick={() => handleChatSend()}
                        disabled={chatLoading || !chatInput.trim()}
                      >
                        Send
                      </button>
                    </div>
                  </div>
                </div>

                {/* 2. Knowledge Base Articles List Panel */}
                <div className="surface-card" style={{ display: 'flex', flexDirection: 'column', height: '680px' }}>
                  <div className="card-title-row" style={{ borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '1.2rem' }}>📚</span>
                      <h2 className="card-heading" style={{ fontSize: '1rem', margin: 0 }}>Articles Repository</h2>
                    </div>
                    {/* Authorship permission check: agents & admins can add articles */}
                    {(currentUser.role === 'support_agent' || currentUser.role === 'administrator') && (
                      <button
                        className="btn-primary"
                        style={{ fontSize: '0.75rem', padding: '0.3rem 0.65rem' }}
                        onClick={() => setShowCreateKbModal(true)}
                      >
                        + New Article
                      </button>
                    )}
                  </div>

                  {/* Articles scrollable list */}
                  <div style={{ flex: 1, overflowY: 'auto', padding: '0.75rem 0', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {kbArticles.map((art) => (
                      <div
                        key={art.id}
                        className="surface-card"
                        onClick={() => setSelectedArticle(art)}
                        style={{ padding: '0.85rem 1rem', cursor: 'pointer', transition: 'box-shadow 0.15s' }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                          <span className="category-tag">{art.category}</span>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>⏱️ {art.read_time}</span>
                        </div>
                        <p style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.3rem' }}>{art.title}</p>
                        <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.4, marginBottom: '0.4rem' }}>{art.excerpt}</p>
                        <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                          {art.tags.map((tag) => (
                            <span key={tag} className="kb-pill">#{tag}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ====================================================================
              VIEW G: REPORTS & ANALYTICS
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
                      {PRIORITIES.map((p) => {
                        const count = stats?.by_priority?.[p] || 0;
                        const targets = {
                          Critical: { resp: '15 mins', resol: '2 hours' },
                          High: { resp: '30 mins', resol: '4 hours' },
                          Medium: { resp: '2 hours', resol: '8 hours' },
                          Low: { resp: '4 hours', resol: '24 hours' },
                        };
                        return (
                          <tr key={p}>
                            <td>
                              <span className={`priority-tag ${p}`}>{p}</span>
                            </td>
                            <td style={{ fontWeight: 600 }}>{count}</td>
                            <td>{targets[p].resp}</td>
                            <td>{targets[p].resol}</td>
                            <td>
                              <span className="status-tag Open">Compliant</span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ====================================================================
              VIEW H: SELF-HEALING SYSTEM DIAGNOSTICS
             ==================================================================== */}
          {activeTab === 'diagnostics' && (
            <div>
              {/* Top Banner with Run Button */}
              <div className="surface-card" style={{ marginBottom: '1.25rem' }}>
                <div className="card-title-row">
                  <div>
                    <h2 className="card-heading">
                      <span>🛠️</span> Self-Healing IT Diagnostics Engine
                    </h2>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                      Non-destructive health inspections across Network connectivity, Python runtime/ChromaDB memory, and disk storage.
                    </p>
                  </div>
                  <button
                    className="btn-primary"
                    disabled={diagnosticsLoading}
                    onClick={handleRunDiagnostics}
                  >
                    {diagnosticsLoading ? 'Running Checks...' : '▶️ Run Full Diagnostic Suite'}
                  </button>
                </div>
              </div>

              {/* Diagnostic Results Cards */}
              {diagnosticsReport && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
                  {diagnosticsReport.checks.map((chk, ci) => (
                    <div key={ci} className="surface-card" style={{ border: `1px solid ${chk.status === 'Passed' ? '#a7f3d0' : '#fecdd3'}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                        <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>{chk.category}</h3>
                        <span className={`status-tag ${chk.status === 'Passed' ? 'Resolved' : 'Critical'}`}>
                          {chk.status}
                        </span>
                      </div>
                      <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', marginBottom: '0.65rem' }}>
                        {chk.message}
                      </p>

                      {/* Detail metrics */}
                      <div style={{ backgroundColor: 'var(--bg-surface-alt)', padding: '0.5rem 0.75rem', borderRadius: '4px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', marginBottom: '0.65rem' }}>
                        {Object.entries(chk.details || {}).map(([k, v]) => (
                          <div key={k} style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span style={{ color: 'var(--text-muted)' }}>{k}:</span>
                            <span style={{ fontWeight: 600 }}>{String(v)}</span>
                          </div>
                        ))}
                      </div>

                      {/* Recommendations */}
                      {chk.recommendations && chk.recommendations.length > 0 && (
                        <div style={{ fontSize: '0.75rem', color: '#1e40af', backgroundColor: '#eff6ff', padding: '0.5rem', borderRadius: '4px', marginBottom: '0.5rem' }}>
                          <strong>Action:</strong> {chk.recommendations[0]}
                        </div>
                      )}

                      {/* Escalate button if check warned/failed */}
                      {chk.status !== 'Passed' && (
                        <button
                          className="btn-secondary"
                          style={{ width: '100%', fontSize: '0.75rem', color: '#e11d48' }}
                          onClick={() => {
                            setCreateTitle(`Diagnostic Alert: ${chk.category} Failed`);
                            setCreateDescription(`Self-healing diagnostic check detected an anomaly:\n\n${chk.message}\n\nDetails: ${JSON.stringify(chk.details, null, 2)}`);
                            setCreateCategory('Other');
                            setCreatePriority('High');
                            setShowCreateModal(true);
                          }}
                        >
                          🚨 Escalate to Incident Ticket
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Underlying System Telemetry & MongoDB Atlas Info */}
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
                      <span style={{ fontFamily: 'var(--font-mono)' }}>v1.2.0 (FastAPI ASGI + ChromaDB RAG)</span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.6rem 0' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Active Storage Engine</span>
                      <span className="category-tag">{storageStatus?.mode || 'in_memory_fallback'}</span>
                    </div>
                  </div>
                </div>

                {/* ServiceNow Integration Telemetry Card */}
                <div className="surface-card">
                  <div className="card-title-row">
                    <h2 className="card-heading">
                      <span>🔗</span> ServiceNow Table API Adapter
                    </h2>
                    <button
                      className="btn-secondary"
                      onClick={() => fetchServiceNowStatus(true)}
                      disabled={serviceNowLoading}
                    >
                      {serviceNowLoading ? 'Verifying...' : 'Verify Live Connection'}
                    </button>
                  </div>

                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem', lineHeight: 1.5 }}>
                    Connects local ITSM tickets directly to ServiceNow instances using the official Table API (<code>/api/now/table/incident</code>).
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--border)' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Adapter Mode:</span>
                      <span className={`status-tag ${serviceNowStatus?.mode === 'live' ? (serviceNowStatus?.connection_verified ? 'Resolved' : 'InProgress') : 'Open'}`}>
                        {serviceNowStatus?.mode === 'live' ? (serviceNowStatus?.connection_verified ? 'LIVE CONNECTED' : 'LIVE (UNVERIFIED)') : 'SIMULATION MODE'}
                      </span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--border)' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Target Instance:</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{serviceNowStatus?.instance_url || 'Simulation (dev-simulation)'}</span>
                    </div>

                    {serviceNowStatus?.message && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--border)' }}>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Status Detail:</span>
                        <span style={{ fontSize: '0.8rem', color: serviceNowStatus?.connection_verified ? '#059669' : 'var(--text-secondary)', textAlign: 'right', maxWidth: '65%' }}>
                          {serviceNowStatus.message}
                        </span>
                      </div>
                    )}

                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Adapter Capabilities:</span>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>Create Incident, Sync Status, Fetch Incident</span>
                    </div>
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
                        <option key={c} value={c}>{c}</option>
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
                        <option key={p} value={p}>{p}</option>
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
                        <option key={a} value={a}>{a}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <div className="field-label">Requester</div>
                    <input
                      type="text"
                      className="input-text"
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
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '780px' }}>
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
              <div style={{ backgroundColor: 'var(--bg-surface-alt)', padding: '1rem', borderRadius: 'var(--radius-md)', marginBottom: '1.25rem', fontSize: '0.875rem', lineHeight: 1.6 }}>
                <strong>Issue Description:</strong>
                <p style={{ marginTop: '0.35rem', whiteSpace: 'pre-wrap' }}>{selectedTicket.description}</p>
                {selectedTicket.resolution_notes && (
                  <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)', color: '#059669' }}>
                    <strong>Resolution Notes:</strong> {selectedTicket.resolution_notes}
                  </div>
                )}
              </div>

              {/* Work Session Timer Control Widget */}
              <div style={{ border: '1px solid #fed7aa', backgroundColor: '#fffbeb', padding: '1rem', borderRadius: 'var(--radius-md)', marginBottom: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span style={{ fontSize: '1.1rem' }}>⏱️</span>
                    <strong style={{ fontSize: '0.9rem', color: '#9a3412' }}>Persistent Work Timer (MongoDB Stored)</strong>
                  </div>
                  <span style={{ fontSize: '0.78rem', color: '#c2410c', fontWeight: 600 }}>
                    Total Time Logged: {ticketTimerData?.total_duration_minutes || 0} minutes
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  {ticketTimerData?.is_agent_active ? (
                    <button
                      className="btn-primary"
                      style={{ backgroundColor: '#d97706', borderColor: '#d97706' }}
                      disabled={timerActionLoading}
                      onClick={() => handleStopTimer(selectedTicket.id)}
                    >
                      {timerActionLoading ? 'Stopping...' : '⏹️ Stop Work (Active for ' + currentUser.name + ')'}
                    </button>
                  ) : (
                    <button
                      className="btn-primary"
                      style={{ backgroundColor: '#2563eb', borderColor: '#2563eb' }}
                      disabled={timerActionLoading || (activeTimer && activeTimer.ticket_id !== selectedTicket.id)}
                      onClick={() => handleStartTimer(selectedTicket.id)}
                      title={activeTimer ? 'You have an active timer on another ticket. Stop it first.' : 'Start recording work time'}
                    >
                      {timerActionLoading ? 'Starting...' : '▶️ Start Work on This Ticket'}
                    </button>
                  )}

                  {activeTimer && activeTimer.ticket_id !== selectedTicket.id && (
                    <span style={{ fontSize: '0.75rem', color: '#b45309' }}>
                      ⚠️ Active timer on {activeTimer.ticket_number}. (Only 1 timer per agent allowed).
                    </span>
                  )}
                </div>
              </div>

              {/* ServiceNow Sync Widget */}
              <div style={{ border: '1px solid var(--border)', padding: '1rem', borderRadius: 'var(--radius-md)', marginBottom: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>🔗 ServiceNow Integration</div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                    {selectedTicket.servicenow_incident_number ? (
                      <span style={{ color: selectedTicket.servicenow_mode === 'live' ? '#059669' : '#2563eb', fontWeight: 600 }}>
                        Synced: {selectedTicket.servicenow_incident_number} ({selectedTicket.servicenow_mode === 'live' ? 'Live Instance' : 'Simulated'}) {selectedTicket.servicenow_sys_id && `• sys_id: ${selectedTicket.servicenow_sys_id.slice(0, 10)}...`}
                      </span>
                    ) : (
                      'Not yet synced with ServiceNow Table API'
                    )}
                  </div>
                </div>

                <button
                  className="btn-secondary"
                  disabled={syncingTicketId === selectedTicket.id}
                  onClick={() => handleSyncServiceNow(selectedTicket.id)}
                >
                  {syncingTicketId === selectedTicket.id ? 'Syncing...' : '🔄 Sync with ServiceNow'}
                </button>
              </div>

              {/* Lifecycle Actions Bar */}
              <div style={{ border: '1px solid var(--border)', padding: '1rem', borderRadius: 'var(--radius-md)', marginBottom: '1.25rem' }}>
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
                        <option key={a} value={a}>{a}</option>
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
                  <span key={t} className="kb-pill">#{t}</span>
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

      {/* ====================================================================
          MODAL 4: SUBMIT SERVICE REQUEST
         ==================================================================== */}
      {showCatalogModal && selectedCatalogItem && (
        <div className="modal-overlay" onClick={() => setShowCatalogModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Request: {selectedCatalogItem.name}</h2>
              <button
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text-muted)' }}
                onClick={() => setShowCatalogModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmitServiceRequest}>
              <div className="modal-body">
                {reqSuccess && (
                  <div style={{ padding: '0.75rem', backgroundColor: '#ecfdf5', color: '#059669', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.85rem' }}>
                    ✅ {reqSuccess}
                  </div>
                )}
                {reqError && (
                  <div style={{ padding: '0.75rem', backgroundColor: '#fff1f2', color: '#e11d48', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.85rem' }}>
                    ⚠️ {reqError}
                  </div>
                )}

                <div style={{ backgroundColor: 'var(--bg-surface-alt)', padding: '0.75rem', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.825rem' }}>
                  <div><strong>Category:</strong> {selectedCatalogItem.category}</div>
                  <div><strong>Approval Required:</strong> {selectedCatalogItem.requires_approval ? 'Yes (Manager/IT Signoff)' : 'Pre-approved'}</div>
                  <div><strong>Estimated SLA:</strong> {selectedCatalogItem.estimated_hours} hours</div>
                </div>

                <div className="form-field">
                  <div className="field-label">
                    <span>Business Justification *</span>
                  </div>
                  <input
                    type="text"
                    className="input-text"
                    placeholder="e.g., Required for Sprint 42 backend container development"
                    value={reqJustification}
                    onChange={(e) => setReqJustification(e.target.value)}
                    required
                  />
                </div>

                <div className="form-field">
                  <div className="field-label">
                    <span>Additional Requirements / Version (Optional)</span>
                  </div>
                  <textarea
                    className="textarea-control"
                    placeholder="Specify license edition, OS version, or account access..."
                    value={reqDescription}
                    onChange={(e) => setReqDescription(e.target.value)}
                    rows={3}
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowCatalogModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={reqSubmitting}
                >
                  {reqSubmitting ? 'Submitting...' : 'Submit Service Request'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ====================================================================
          MODAL 5: CREATE KNOWLEDGE BASE ARTICLE
         ==================================================================== */}
      {showCreateKbModal && (
        <div className="modal-overlay" onClick={() => setShowCreateKbModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Publish Knowledge Base Article</h2>
              <button
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text-muted)' }}
                onClick={() => setShowCreateKbModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateKbArticle}>
              <div className="modal-body">
                {kbCreateSuccess && (
                  <div style={{ padding: '0.75rem', backgroundColor: '#ecfdf5', color: '#059669', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.85rem' }}>
                    ✅ {kbCreateSuccess}
                  </div>
                )}
                {kbCreateError && (
                  <div style={{ padding: '0.75rem', backgroundColor: '#fff1f2', color: '#e11d48', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.85rem' }}>
                    ⚠️ {kbCreateError}
                  </div>
                )}

                <div className="form-field">
                  <div className="field-label">Article Title *</div>
                  <input
                    type="text"
                    className="input-text"
                    placeholder="e.g., Resolving SSH Connection Timeouts to Staging Servers"
                    value={kbTitle}
                    onChange={(e) => setKbTitle(e.target.value)}
                    required
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                  <div>
                    <div className="field-label">Category *</div>
                    <select
                      className="select-control"
                      value={kbCategory}
                      onChange={(e) => setKbCategory(e.target.value)}
                    >
                      {CATEGORIES.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <div className="field-label">Tags (comma separated)</div>
                    <input
                      type="text"
                      className="input-text"
                      placeholder="e.g., ssh, network, timeout"
                      value={kbTags}
                      onChange={(e) => setKbTags(e.target.value)}
                    />
                  </div>
                </div>

                <div className="form-field">
                  <div className="field-label">Short Summary / Excerpt</div>
                  <input
                    type="text"
                    className="input-text"
                    placeholder="One-line summary for search snippets..."
                    value={kbExcerpt}
                    onChange={(e) => setKbExcerpt(e.target.value)}
                  />
                </div>

                <div className="form-field">
                  <div className="field-label">Article Content (Markdown / Text) *</div>
                  <textarea
                    className="textarea-control"
                    placeholder="Step-by-step troubleshooting instructions, diagnosis steps, and verified resolution..."
                    value={kbContent}
                    onChange={(e) => setKbContent(e.target.value)}
                    rows={8}
                    required
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowCreateKbModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={kbSubmitting}
                >
                  {kbSubmitting ? 'Indexing Article...' : 'Publish & Vector Index'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
