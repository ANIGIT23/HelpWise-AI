# Guide 05: Git & Deployment Roadmap

This guide covers preparing your project for GitHub, managing git commits cleanly, explaining your code to interviewers, and the future cloud hosting roadmap.

---

## 1. Initializing Git and Pushing to GitHub

### Step 1.1: Verify Root `.gitignore`
Before running any `git add` commands, verify that `.gitignore` is present at the root of `HelpWise-AI`.
It ensures:
- Python virtual environments (`.venv/`) are **never** committed.
- Node modules (`node_modules/`) are **never** committed.
- Secrets and `.env` files are protected.

### Step 1.2: Initialize Git Repository (Windows PowerShell)
Open PowerShell at `E:\HelpWise-AI`:
```powershell
cd E:\HelpWise-AI
git init
```

### Step 1.3: Stage and Commit the Initial Foundation
```powershell
git add .
git status
```
Ensure you do **not** see any files inside `.venv` or `node_modules` in the green staged list.

Commit with a descriptive, conventional commit message:
```powershell
git commit -m "feat: initialize HelpWise AI with React Vite frontend and FastAPI backend health check"
```

### Step 1.4: Link to GitHub Repository
Create a new public repository on [GitHub](https://github.com/new) named `HelpWise-AI` (do **not** check "Add a README" since we already have one).

Then run:
```powershell
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/HelpWise-AI.git
git push -u origin main
```

---

## 2. Best Practices for Git Commits During Technical Assessments

Hiring managers check your git history to evaluate:
1. **Granularity**: Are commits atomic (one logical change per commit), or did you dump the entire project in one giant commit?
2. **Conventional Commit Messages**:
   - `feat:` for new features (e.g. `feat: add GET /health endpoint`)
   - `fix:` for bug fixes (e.g. `fix: update CORS origins for port 5173`)
   - `docs:` for documentation updates (e.g. `docs: add comprehensive frontend & backend guides`)
   - `chore:` for tooling or config updates (e.g. `chore: configure root .gitignore`)
3. **Commit Cleanliness**: Never commit API keys, passwords, or temporary build caches.

---

## 3. Cloud Deployment Roadmap (Future Phase)

When you are ready to deploy HelpWise AI online for your assessment review, here is the recommended architecture:

```
+----------------------------+             +-----------------------------+
|    Vercel / Netlify        |             |       Render / Railway      |
|  (Frontend Static Hosting) |             |  (Python FastAPI Container) |
|                            |   HTTPS     |                             |
|  React 18 SPA (Vite build) | ----------> |  FastAPI + Uvicorn          |
|  URL: helpwise.vercel.app  |  REST API   |  URL: api.helpwise.onrender |
+----------------------------+             +--------------+--------------+
                                                          |
                                                          | MongoDB Driver
                                                          v
                                           +-----------------------------+
                                           |      MongoDB Atlas Cloud    |
                                           |  (Managed M0 Free Cluster)  |
                                           +-----------------------------+
```

### 1. Frontend Deployment (Vercel)
- Connect GitHub repo to Vercel.
- Root Directory: `frontend`
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment Variable: `VITE_API_URL=https://<your-backend-render-app>.onrender.com`

### 2. Backend Deployment (Render / Railway)
- Root Directory: `backend`
- Environment: Python 3
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Environment Variable: `ALLOWED_ORIGINS=https://helpwise.vercel.app`

---

## 4. How to Confidently Explain This Project in an Interview

In technical interviews, interviewers know that modern developers use AI tools. What they evaluate is **whether you actually understand the concepts and can defend your engineering decisions**.

### The 4-Step Answer Framework:
1. **Context & Problem Statement**:
   - *"I built HelpWise AI to solve the problem of enterprise IT ticket backlogs and slow MTTR through an AI-assisted ITSM helpdesk platform."*
2. **Architecture**:
   - *"I designed it with a clean decoupled architecture: a React 18 SPA built with Vite on the frontend, and a high-performance Python FastAPI service on the backend communicating over REST."*
3. **Why Decisions Were Made**:
   - *"I chose FastAPI over Flask because of native ASGI async support, automated Pydantic schema validation, and zero-config Swagger UI at `/docs`. For the frontend, I chose Vite over Create React App because of instant HMR via native ES modules."*
4. **Current Status & Verification**:
   - *"In Phase 1, I established the foundation with a live health check probe (`GET /health`) that provides telemetry metrics and verifies cross-origin communication between the client and server. Both services are fully running and tested."*
