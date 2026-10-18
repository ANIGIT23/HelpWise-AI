# HelpWise AI — ITSM Helpdesk

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An intelligent, next-generation IT Service Management (ITSM) helpdesk platform engineered with a decoupled architecture: a modern **React + Vite** client and a high-performance **Python FastAPI** REST backend.

---

## 🌟 Architecture Overview

```
HelpWise-AI/
├── frontend/             # React.js SPA built with Vite
│   ├── src/
│   │   ├── App.jsx       # Main dashboard & live health probe
│   │   ├── index.css     # Dark mode enterprise design system
│   │   └── main.jsx      # React DOM entrypoint
│   └── package.json
│
├── backend/              # Python FastAPI REST API service
│   ├── main.py           # FastAPI app, CORS middleware, /health probe
│   ├── requirements.txt  # Python backend dependencies
│   └── .venv/            # Isolated virtual environment
│
├── guides/               # Complete step-by-step developer documentation
│   ├── 01_PROJECT_OVERVIEW_AND_ARCHITECTURE.md
│   ├── 02_SETUP_AND_RUN_TUTORIAL.md
│   ├── 03_BACKEND_EXPLAINED.md
│   ├── 04_FRONTEND_EXPLAINED.md
│   └── 05_GIT_AND_DEPLOYMENT_ROADMAP.md
│
└── .gitignore            # Clean git exclusion rules
```

---

## 🚀 Quickstart Guide (Windows PowerShell)

### 1. Start the Backend API
Open a PowerShell window:
```powershell
cd E:\HelpWise-AI\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
- API Base: `http://127.0.0.1:8000`
- Health Endpoint: `http://127.0.0.1:8000/health`
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`

### 2. Start the Frontend Client
Open a second PowerShell window:
```powershell
cd E:\HelpWise-AI\frontend
npm install
npm run dev
```
- Frontend UI: `http://127.0.0.1:5173`

---

## 📚 Complete Guides & Interview Preparation

Comprehensive documentation has been prepared in the [`guides/`](guides/) folder:
- [00: Project Execution & Command Journal](guides/00_PROJECT_EXECUTION_LOG.md) *(Audit log of every command & move)*
- [00: Conversation & Learning Reference](guides/00_CONVERSATION_AND_LEARNING_REFERENCE.md) *(Chat archive, prompts, & Q&A)*
- [01: Project Overview & Architecture](guides/01_PROJECT_OVERVIEW_AND_ARCHITECTURE.md)
- [02: Setup & PowerShell Run Tutorial](guides/02_SETUP_AND_RUN_TUTORIAL.md)
- [03: Backend Deep-Dive & Line-by-Line Code Explanation](guides/03_BACKEND_EXPLAINED.md)
- [04: Frontend Deep-Dive & Line-by-Line Code Explanation](guides/04_FRONTEND_EXPLAINED.md)
- [05: Git & Deployment Roadmap](guides/05_GIT_AND_DEPLOYMENT_ROADMAP.md)
- [06: ITSM Ticket Management & Database Architecture](guides/06_TICKET_MANAGEMENT_AND_DATABASE.md) *(MongoDB Atlas + In-Memory Fallback)*
