# Guide 01: Project Overview & System Architecture

## 1. Executive Summary & Project Goal
**HelpWise AI** is an enterprise-grade IT Service Management (ITSM) helpdesk platform designed to automate, streamline, and intelligently assist IT support teams. 

In a typical corporate IT environment, employees submit thousands of support tickets every day—ranging from password resets and VPN troubles to hardware replacements and database connectivity issues. Traditional ITSM solutions (like ServiceNow or Jira Service Management) often suffer from:
1. **Ticket backlog**: Repetitive queries overwhelm human agents.
2. **Slow resolution time (MTTR - Mean Time to Resolution)**: Searching through fragmented internal documentation is manual and slow.
3. **Inconsistent ticket triage**: Categorization, priority assignment, and routing often have human error.

**HelpWise AI solves this through a multi-phase system:**
- **Phase 1 (Current)**: Solid, decoupled foundation with a React/Vite frontend and a FastAPI backend with health monitoring.
- **Phase 2 (Upcoming)**: MongoDB Atlas persistence layer for ticket schemas, audit logs, and knowledge base documents.
- **Phase 3 (Upcoming)**: Retrieval-Augmented Generation (RAG) and LLM-driven query answering to automatically deflect and resolve common IT queries.
- **Phase 4 (Upcoming)**: ServiceNow integration (starting with a mock bridge) to synchronize enterprise tickets bi-directionally.

---

## 2. Technology Stack & Architectural Decision Records (ADRs)

When explaining your choices in an interview, you must articulate **why** you chose each technology over common alternatives:

| Layer | Chosen Technology | Alternatives Considered | Why This Technology Was Chosen |
|---|---|---|---|
| **Frontend Framework** | **React.js 18+** | Angular, Vue, Vanilla JS | Industry standard for single-page applications (SPAs). Component-driven model allows clean separation of UI blocks (e.g., ticket feeds, health probes, AI chat widgets). Massive ecosystem and familiar to hiring managers. |
| **Frontend Tooling** | **Vite** | Create React App (CRA), Webpack | Vite leverages native ES Modules (ESM) in the browser and compiles with `esbuild` (written in Go), providing millisecond Hot Module Replacement (HMR) and instant dev server startup, unlike legacy Webpack/CRA which pre-bundles entire dependency trees. |
| **Backend Framework** | **FastAPI** | Flask, Django | High-performance Python web framework based on Starlette (ASGI) and Pydantic. Provides native asynchronous (`async`/`await`) capabilities, automatic request validation, and zero-configuration interactive API documentation (`/docs` using Swagger UI). Much lighter and faster than Django, while significantly more modern and type-safe than Flask. |
| **ASGI Web Server** | **Uvicorn** | Gunicorn, Waitress | Lightning-fast ASGI server implementation for Python based on `uvloop` and `httptools`. Handles asynchronous concurrency effortlessly. |
| **Styling** | **Vanilla CSS (Modern Custom Design System)** | Tailwind, Bootstrap, Material UI | Maximizes control without heavy utility class bloat or third-party CSS dependencies. Uses modern CSS custom properties (variables), CSS Grid, Flexbox, glassmorphism (`backdrop-filter`), and responsive media queries. |
| **Database (Phase 2)** | **MongoDB Atlas** | PostgreSQL, MySQL | Document-based schema allows flexible structures for varied ITSM tickets, custom user fields, unstructured logs, and embeddings metadata. |

---

## 3. High-Level Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                                CLIENT BROWSER                                     |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                     React 18 Single-Page Application (SPA)                  |  |
|  |                                                                             |  |
|  |  • Brand Header & Status Indicator                                         |  |
|  |  • Backend Health Probe Widget (Round-trip latency meter, JSON inspector)   |  |
|  |  • Architectural Roadmap Dashboard                                         |  |
|  |  • Quick PowerShell Command Palettes                                        |  |
|  +---------------------------------------+-------------------------------------+  |
+------------------------------------------|----------------------------------------+
                                           |
                                  HTTP GET | Requests (Fetch API)
                                           | Origin: http://localhost:5173
                                           v
+-----------------------------------------------------------------------------------+
|                        FASTAPI BACKEND SERVICE (Port 8000)                        |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                     CORS Middleware (Cross-Origin Policy)                   |  |
|  |                     Validates allowed origins (localhost:5173)              |  |
|  +---------------------------------------+-------------------------------------+  |
|                                          |
|                                          v
|  +-----------------------------------------------------------------------------+  |
|  |                           FastAPI Router Engine                             |  |
|  |                                                                             |  |
|  |  • GET /        -> Root Welcome & Navigation                                |  |
|  |  • GET /health  -> Health Monitoring & Telemetry Response                   |  |
|  |  • GET /docs    -> Interactive Swagger UI OpenAPI Documentation            |  |
|  +---------------------------------------+-------------------------------------+  |
|                                          |
|                                          v
|  +-----------------------------------------------------------------------------+  |
|  |                         Pydantic Validation Layer                           |  |
|  |                         Validates & serializes HealthResponse schema        |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 4. Request-Response Lifecycle (How GET /health Works)

1. **User Action or Page Load**:
   - In `App.jsx`, when the React component mounts or when the user clicks `"Ping Backend"`, an asynchronous `fetch()` request is dispatched to `http://127.0.0.1:8000/health`.
   - `performance.now()` captures the start time timestamp.
2. **Browser CORS Verification**:
   - The browser inspects the destination. Since `http://localhost:5173` is calling `http://127.0.0.1:8000`, this is a cross-origin request.
   - The browser looks for headers like `Access-Control-Allow-Origin` in the response.
3. **FastAPI Middleware Processing**:
   - In `main.py`, FastAPI's `CORSMiddleware` intercepts the request, validates that the caller is in the allowed `origins` list, and appends the proper headers.
4. **Endpoint Execution**:
   - The `@app.get("/health")` route function is executed.
   - It instantiates a `HealthResponse` Pydantic model with fields:
     - `status`: `"healthy"`
     - `app`: `"HelpWise AI — ITSM Helpdesk"`
     - `version`: `"1.0.0"`
     - `timestamp`: Current UTC timestamp in ISO 8601 format
     - `environment`: `"development"`
5. **Serialization & HTTP Response**:
   - FastAPI serializes the Pydantic model into a JSON string and returns an HTTP `200 OK` status.
6. **React State Update & Re-render**:
   - In React, the promise resolves.
   - Latency is calculated: `Math.round(performance.now() - startTime)`.
   - React state (`setHealthData`, `setLatency`, `setLoading(false)`) is updated, triggering an efficient DOM update showing the green status badge and telemetry data.

---

## 5. Technical Glossary (Must-Know Interview Terminology)

- **ITSM (IT Service Management)**: The craft of designing, delivering, managing, and improving the lifecycle of IT services in an enterprise.
- **Decoupled Architecture**: Separating the presentation layer (frontend) from the business logic layer (backend) so both can evolve, scale, and deploy independently.
- **ASGI (Asynchronous Server Gateway Interface)**: The modern Python standard interface between async-capable Python web servers and web applications (successor to WSGI).
- **CORS (Cross-Origin Resource Sharing)**: An HTTP-header-based mechanism that allows a server to indicate any origins (domain, scheme, or port) other than its own from which a browser should permit loading resources.
- **Pydantic**: A data validation and parsing library for Python based on type annotations. Enforces data types at runtime and supplies user-friendly error messages when data is invalid.
- **HMR (Hot Module Replacement)**: A development feature that updates modules in the browser while an application is running, without a full page reload.
