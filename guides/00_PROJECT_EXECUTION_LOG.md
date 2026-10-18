# Guide 00: Project Execution & Command Journal

This document records **every single move, command, decision, and verification** made in HelpWise AI from the very start of the project. It serves as your audit trail and technical logbook so you can track what was done, why it was done, the commands run, and the outcomes.

---

## 📋 Table of Completed Actions (Chronological Audit Log)

| Step # | Action / Operation | Why We Did This (Rationale) | Exact Command / File Affected | Result / Status |
|:---:|---|---|---|---|
| **01** | Inspect Workspace | Verify whether the root directory `e:\HelpWise-AI` contained existing files or configurations before writing code. | `list_dir(e:\HelpWise-AI)` | Directory confirmed empty (clean slate). |
| **02** | Environment Prerequisite Check | Confirm that Python, Node.js, and npm are installed and meet version requirements on Windows. | `node -v; npm -v; python --version` | `Node v22.18.0`, `npm 10.9.3`, `Python 3.13.1`. All modern and supported. |
| **03** | Scaffold React + Vite Frontend | Initialize a clean React single-page app (SPA) using Vite in non-interactive mode. | `npx.cmd -y create-vite@latest frontend --template react --no-interactive` | Created `frontend/` directory with standard Vite structure. |
| **04** | Install Frontend Dependencies | Download React 18, React-DOM, and Vite development tooling into `frontend/node_modules/`. | `npm install` (in `frontend/`) | 24 packages installed in 27s, 0 vulnerabilities. |
| **05** | Define Backend Dependencies | Specify locked Python libraries for FastAPI, ASGI server, validation, and env config. | Created [`backend/requirements.txt`](file:///e:/HelpWise-AI/backend/requirements.txt) | Specified `fastapi>=0.110.0`, `uvicorn[standard]>=0.28.0`, `pydantic>=2.6.0`, `python-dotenv>=1.0.0`. |
| **06** | Create Python Virtual Environment | Isolate backend dependencies from global Windows Python libraries to prevent dependency collisions. | `python -m venv .venv` (in `backend/`) | Created isolated `.venv` directory. |
| **07** | Install Backend Dependencies | Install FastAPI, Uvicorn, and Pydantic into `.venv`. | `.venv\Scripts\pip.exe install -r requirements.txt` | Successfully installed `fastapi-0.143.5`, `uvicorn-0.54.0`, `pydantic-2.14.1`, etc. |
| **08** | Implement FastAPI Service (`main.py`) | Create core API instance with CORS middleware, root endpoint (`GET /`), and health check (`GET /health`). | Created [`backend/main.py`](file:///e:/HelpWise-AI/backend/main.py) | API app defined with Pydantic `HealthResponse` schema and `/health` route. |
| **09** | Configure HTML Title & Typography | Update browser tab title to "HelpWise AI — ITSM Helpdesk" and load Inter & JetBrains Mono fonts. | Edited [`frontend/index.html`](file:///e:/HelpWise-AI/frontend/index.html) | Title set, Google Fonts `<link>` added. |
| **10** | Create Enterprise Design System | Provide modern, dark-mode glassmorphism styling, glowing status pills, and responsive layout. | Created [`frontend/src/index.css`](file:///e:/HelpWise-AI/frontend/src/index.css) | Custom CSS design tokens, HSL colors, pulse animations, zero external CSS bloat. |
| **11** | Build React App Component (`App.jsx`) | Create root UI with live backend health probe, round-trip latency meter, raw JSON inspector, and roadmap. | Created [`frontend/src/App.jsx`](file:///e:/HelpWise-AI/frontend/src/App.jsx) | UI renders title, architecture cards, and connects to `http://127.0.0.1:8000/health`. |
| **12** | Verify Frontend Production Build | Validate that JSX compiles, asset bundling succeeds, and there are no syntax or lint errors. | `npm run build` (in `frontend/`) | Built successfully in 317ms (`dist/index.html`, `dist/assets/`). |
| **13** | Launch Backend Server (Verification) | Start Uvicorn ASGI server as a background daemon to test endpoint responsiveness. | `.venv\Scripts\uvicorn.exe main:app --host 127.0.0.1 --port 8000` | Uvicorn running on `http://127.0.0.1:8000`. |
| **14** | Probe Backend `GET /health` | Execute HTTP request against backend to verify JSON response contract. | `Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get` | Returned `200 OK` with JSON: `{"status": "healthy", "app": "HelpWise AI — ITSM Helpdesk", "version": "1.0.0", ...}`. |
| **15** | Launch Frontend Server (Verification) | Start Vite dev server on port 5173 to verify HTTP serving. | `npm run dev -- --host 127.0.0.1 --port 5173` | Vite dev server running on `http://127.0.0.1:5173`. |
| **16** | Verify Frontend HTTP Status | Confirm that Vite serves HTML on port 5173. | `Invoke-WebRequest -Uri "http://127.0.0.1:5173"` | Returned HTTP `200 OK`. |
| **17** | Browser Subagent Verification | Attempt headless browser navigation and record visual session. | Browser subagent execution | Sandbox network restricted Playwright driver download (404); CLI HTTP tests confirmed both servers operational. |
| **18** | Create Root `.gitignore` | Prevent accidental commits of `.venv/`, `node_modules/`, environment secrets, or cache files. | Created [`.gitignore`](file:///e:/HelpWise-AI/.gitignore) | Configured Python, Node, and environment exclusion rules. |
| **19** | Create Root `README.md` | Provide professional project presentation, architecture badges, folder tree, and quickstart. | Created [`README.md`](file:///e:/HelpWise-AI/README.md) | Formatted markdown with architecture diagram and command guide. |
| **20** | Create 5 Comprehensive Guides | Author thorough, step-by-step documentation, line-by-line code explanations, and 20 interview Q&As. | Created `guides/01` through `guides/05` | Complete educational materials covering architecture, setup, backend, frontend, and deployment. |
| **21** | Git Initialization & Initial Commit | Initialize version control and save a pristine baseline commit. | `git init; git add .; git commit -m "..."` | Committed 25 files on branch `master` with clean working tree. |
| **22** | User Local Browser & Port Collision Audit | User opened `http://127.0.0.1:8000` and `http://localhost:5173` successfully; diagnosed `[WinError 10013]` (occupied port 8000) and `npm ENOENT` (wrong working directory). | Audited terminal logs and screenshots | Confirmed UI connected, 12ms latency, and clarified directory paths. |
| **23** | Terminate Background Daemons | Safely cancelled background task-48 (uvicorn) and task-52 (vite) so the user has full exclusive ownership of ports 8000 and 5173 in their local PowerShell terminals. | `manage_task(kill, task-48)` and `manage_task(kill, task-52)` | Ports 8000 and 5173 verified free (`netstat` exit code 1). |
| **24** | Add MongoDB Driver Dependencies | Add `motor>=3.3.0` and `pymongo>=4.6.0` for asynchronous MongoDB Atlas connectivity. | Updated [`backend/requirements.txt`](file:///e:/HelpWise-AI/backend/requirements.txt) | Added official async MongoDB Python driver. |
| **25** | Install Motor and PyMongo in `.venv` | Install the newly declared packages into the isolated Python virtual environment. | `.venv\Scripts\pip.exe install -r requirements.txt` | Installed `motor-3.7.1`, `pymongo-4.19.0`, `dnspython-2.9.0`. |
| **26** | Create Environment Config Template | Provide a `.env.example` file showing the exact MongoDB Atlas connection string structure. | Created [`backend/.env.example`](file:///e:/HelpWise-AI/backend/.env.example) | Template with `MONGODB_URI` and `DATABASE_NAME`. |
| **27** | Create Pydantic Ticket Schemas | Define strict validation rules, data contracts, and enums for category and priority. | Created [`backend/schemas.py`](file:///e:/HelpWise-AI/backend/schemas.py) | Created `TicketCategory`, `TicketPriority`, `TicketCreate`, `TicketResponse`. |
| **28** | Implement Resilient Database Layer | Connect to MongoDB Atlas if `MONGODB_URI` is provided; safely fallback to in-memory store if unset. | Created [`backend/database.py`](file:///e:/HelpWise-AI/backend/database.py) | Dual-mode storage engine with zero crash risk and transparent reporting. |
| **29** | Add Ticket & Storage Routes to API | Register `POST /api/tickets`, `GET /api/tickets`, and `GET /api/storage-status`; preserve `GET /health`. | Updated [`backend/main.py`](file:///e:/HelpWise-AI/backend/main.py) | Lifespan database initialization and ticket CRUD routes active. |
| **30** | Test Ticket Logic via Python | Verify that database initialization, ticket creation (`INC-1003`), and retrieval work with 0 errors. | Python CLI verification command | 2 initial tickets + newly created `INC-1003` verified. |
| **31** | Add Ticket UI Styles to Design System | Style ticket form inputs, category selector pills, priority badges, and incident cards. | Updated [`frontend/src/index.css`](file:///e:/HelpWise-AI/frontend/src/index.css) | Custom enterprise styles with glowing tags and responsive filter bar. |
| **32** | Build Frontend Ticket Management UI | Add Create Ticket form with validation, incident feed, category/priority filters, and Atlas guide. | Updated [`frontend/src/App.jsx`](file:///e:/HelpWise-AI/frontend/src/App.jsx) | Full reactive UI wired to FastAPI backend endpoints. |
| **33** | Test Production Frontend Bundle | Verify that React JSX compiles and Vite production assets build with 0 syntax or lint errors. | `npm run build` (in `frontend/`) | Built successfully in 866ms with 0 errors. |
| **34** | Live HTTP Endpoint Verification | Probe `GET /health`, `GET /api/tickets`, and `POST /api/tickets` via PowerShell `Invoke-RestMethod`. | PowerShell HTTP requests | `POST` created `INC-1003`; `GET` returned 3 tickets; `GET /health` returned healthy. |
| **35** | Author Ticket & DB Guide | Write comprehensive technical documentation, architecture diagrams, and 10 interview Q&As. | Created [`guides/06_TICKET_MANAGEMENT_AND_DATABASE.md`](file:///e:/HelpWise-AI/guides/06_TICKET_MANAGEMENT_AND_DATABASE.md) | Full technical breakdown and MongoDB Atlas setup steps. |

---

## 🔒 Protocol for Subsequent Actions

To ensure you have full visibility and control over everything that happens in your project:
1. **Explain First, Then Act**: Before running any major command or file modification, I will explicitly state:
   - What action is about to take place.
   - Why it is necessary.
   - The exact command or code changes.
2. **Audit Logging**: Every action will be appended to this log so you can review the history at any time.
3. **Interactive Decisions**: For major technical options (e.g. database setup approaches, schema designs), I will present choices for you to review and confirm.
