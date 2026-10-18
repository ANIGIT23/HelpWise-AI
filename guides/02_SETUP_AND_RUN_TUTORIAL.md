# Guide 02: Setup & PowerShell Run Tutorial

This tutorial provides step-by-step instructions for setting up, running, and testing **HelpWise AI** on Windows using Windows PowerShell.

---

## 1. Prerequisites Check

Before running the commands, verify that Python and Node.js are installed on your machine.

Open **Windows PowerShell** and run:
```powershell
python --version
node -v
npm -v
```

**Expected Minimum Versions:**
- Python: `3.10+` (Installed: `3.13.1`)
- Node.js: `18.0+` (Installed: `v22.18.0`)
- npm: `9.0+` (Installed: `10.9.3`)

---

## 2. Setting Up & Running the Backend (FastAPI)

### Step 2.1: Open PowerShell Terminal 1
Open Windows PowerShell and navigate to the backend directory:
```powershell
cd E:\HelpWise-AI\backend
```

### Step 2.2: Create Python Virtual Environment (One-time)
A virtual environment isolates project dependencies so they do not collide with global Python libraries:
```powershell
python -m venv .venv
```

### Step 2.3: Activate the Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```
> **Note for Windows Users**: If PowerShell gives an error saying `running scripts is disabled on this system`, run this command once to permit local scripts:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Once activated, your terminal prompt will show `(.venv)` at the beginning.

### Step 2.4: Install Python Dependencies
```powershell
pip install -r requirements.txt
```
This installs `fastapi`, `uvicorn[standard]`, `pydantic`, and `python-dotenv`.

### Step 2.5: Start the FastAPI Server
```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Command Flags Explained:**
- `main:app`: Look in `main.py` for the variable named `app` (which is our FastAPI instance).
- `--reload`: Enables hot-reload. Whenever you save a `.py` file, Uvicorn will automatically restart the server.
- `--host 127.0.0.1`: Binds the server to loopback address (localhost).
- `--port 8000`: Runs the backend on HTTP port 8000.

**Success Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process using WatchFiles
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## 3. Setting Up & Running the Frontend (React + Vite)

### Step 3.1: Open PowerShell Terminal 2
Keep the backend terminal running! Open a **new** PowerShell window and navigate to the frontend directory:
```powershell
cd E:\HelpWise-AI\frontend
```

### Step 3.2: Install Node Dependencies (One-time)
```powershell
npm install
```
This downloads React, Vite, and development dependencies into `frontend/node_modules/`.

### Step 3.3: Start the Vite Development Server
```powershell
npm run dev
```

**Success Output:**
```
  VITE v8.3.4  ready in 180 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

---

## 4. Verification & Testing

### Verification 1: Open the Frontend in Browser
Visit [http://localhost:5173](http://localhost:5173) in Chrome, Edge, or Firefox.
You will see:
1. Header: `"HelpWise AI — ITSM Helpdesk"`
2. A green pulse dot showing **"Connected"**.
3. Telemetry card showing `"HEALTHY"`, latency in milliseconds, and service name.
4. Clicking `"Ping Backend"` re-queries the backend and updates the round-trip latency.

### Verification 2: Check the Backend Directly in Browser
Visit [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health). You will receive this JSON payload:
```json
{
  "status": "healthy",
  "app": "HelpWise AI — ITSM Helpdesk",
  "version": "1.0.0",
  "timestamp": "2026-10-18T12:38:20.217159Z",
  "environment": "development"
}
```

### Verification 3: Explore Interactive OpenAPI (Swagger) Documentation
FastAPI automatically generates an interactive documentation UI. Visit:
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

From Swagger UI, click **GET /health** > **Try it out** > **Execute** to run live tests directly from your browser without writing code.

### Verification 4: Test via PowerShell Terminal Command
You can test the endpoint directly via PowerShell without a browser:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get | ConvertTo-Json
```

---

## 5. Common Windows Troubleshooting & FAQ

### Issue A: `Activate.ps1 cannot be loaded because running scripts is disabled`
- **Cause**: PowerShell execution policy is set to `Restricted` by default on Windows.
- **Fix**: Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` in PowerShell.

### Issue B: `Error: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): only one usage of each socket address is normally permitted`
- **Cause**: Another process or background terminal is already using port 8000.
- **Fix**: Find and kill the process:
  ```powershell
  # Find the PID using port 8000:
  netstat -ano | findstr :8000
  # Kill the process by PID (e.g., if PID is 1234):
  taskkill /PID 1234 /F
  ```
  Or simply specify a different port when launching:
  ```powershell
  uvicorn main:app --reload --port 8001
  ```

### Issue C: `Failed to fetch` or CORS error in browser console
- **Cause**: Backend server is not running, or frontend is running on a port not listed in `origins` in `backend/main.py`.
- **Fix**: Check that `uvicorn` is running and that your frontend URL (e.g., `http://localhost:5173`) is listed in the `origins` list in `backend/main.py`.
