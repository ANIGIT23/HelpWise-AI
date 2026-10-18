# HelpWise AI — ITSM Helpdesk

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![MongoDB](https://img.shields.io/badge/Database-MongoDB%20Atlas-47A248?style=flat&logo=mongodb&logoColor=white)](https://www.mongodb.com/atlas)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An intelligent, next-generation IT Service Management (ITSM) helpdesk platform engineered with a decoupled architecture: a modern **React + Vite** client and a high-performance **Python FastAPI** REST backend with asynchronous **MongoDB Atlas** persistence and resilient in-memory fallback.

---

## 🌟 Key Features

- **⚡ Real-time Incident Ingestion**: Full support for submitting IT incident tickets with categorization (Hardware, Software, Network, Access, Other) and urgency prioritization (Low, Medium, High, Critical).
- **🛡️ Strict Pydantic Validation**: Runtime input validation and data sanitization preventing malformed inputs.
- **🍃 Dual-Mode Database Engine**: Asynchronous MongoDB Atlas storage with automatic, resilient in-memory development fallback.
- **📊 Live System Telemetry**: Built-in health probe (`GET /health`) tracking server status, database state, and round-trip latency.
- **📋 Reactive Incident Feed**: Interactive ticket board with instant client-side category and priority filters.
- **🎨 Enterprise Dark Mode UI**: Custom-built design system with modern glassmorphism, responsive grids, and zero CSS framework overhead.

---

## 🏗️ Architecture Overview

```
HelpWise-AI/
├── frontend/             # React 18 Single-Page Application (SPA) built with Vite
│   ├── src/
│   │   ├── App.jsx       # Incident management dashboard & telemetry
│   │   ├── index.css     # Dark mode enterprise design system (Vanilla CSS)
│   │   └── main.jsx      # React DOM entrypoint
│   ├── index.html        # HTML5 entry & Google Fonts
│   └── package.json
│
├── backend/              # Python FastAPI REST API service
│   ├── main.py           # FastAPI routes, CORS middleware, /health probe
│   ├── database.py       # Asynchronous Motor client & in-memory fallback
│   ├── schemas.py        # Pydantic models & ITSM Enums
│   ├── requirements.txt  # FastAPI, Uvicorn, Motor, PyMongo, Pydantic
│   ├── .env.example      # Environment configuration template
│   └── .venv/            # Isolated virtual environment (git-ignored)
│
└── .gitignore            # Clean git exclusion rules
```

---

## 🚀 Quickstart Guide (Windows PowerShell)

### 1. Start the Backend API
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
- API Base: `http://127.0.0.1:8000`
- Health Endpoint: `http://127.0.0.1:8000/health`
- Interactive Swagger UI Docs: `http://127.0.0.1:8000/docs`

### 2. Start the Frontend Client
Open a second terminal:
```powershell
cd frontend
npm install
npm run dev
```
- Frontend Web UI: `http://localhost:5173`

---

## 📡 REST API Specification

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health monitoring & active storage mode probe |
| `GET` | `/api/tickets` | Retrieve all incident tickets (sorted newest first) |
| `POST` | `/api/tickets` | Create a new validated support ticket (`201 Created`) |
| `GET` | `/api/storage-status` | Report database connection status and storage mode |
| `GET` | `/docs` | Interactive OpenAPI / Swagger UI testing suite |

---

## 🍃 MongoDB Atlas Configuration (Optional)

To enable permanent cloud persistence:
1. Copy `.env.example` to `.env`:
   ```powershell
   cd backend
   cp .env.example .env
   ```
2. Set your MongoDB Atlas connection URI:
   ```env
   MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority
   DATABASE_NAME=helpwise_db
   ```
3. Restart the backend server. The application will automatically detect Atlas and switch from in-memory fallback to cloud storage.
