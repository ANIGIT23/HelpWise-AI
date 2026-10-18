# Guide 03: Backend Architecture & Line-by-Line Code Explanation

This document breaks down the **HelpWise AI** backend architecture, walks through every line of code in [`backend/main.py`](file:///e:/HelpWise-AI/backend/main.py), and prepares you to answer technical interview questions with confidence.

---

## 1. Backend Directory Structure

```
backend/
├── .venv/               # Isolated Python virtual environment (ignored in git)
├── main.py              # Application entrypoint, FastAPI instance, routes, CORS
└── requirements.txt     # Locked production dependencies
```

### Why This Minimal Structure for Step 1?
In enterprise software engineering, premature complexity is a common antipattern. Instead of introducing dozens of empty folders (`models/`, `controllers/`, `services/`, `repositories/`) before there is any database or business logic, we follow the **YAGNI (You Aren't Gonna Need It)** and **Single Responsibility** principles:
- Establish a working, tested API server first.
- In Step 2 (MongoDB), we will introduce modular routers (`api/v1/`), database connections (`core/database.py`), and domain models (`schemas/`).

---

## 2. Line-by-Line Code Explanation of `backend/main.py`

Here is the complete source code of [`backend/main.py`](file:///e:/HelpWise-AI/backend/main.py) with detailed, line-by-line technical commentary:

```python
1: from datetime import datetime
2: from typing import Dict, Any
3: from fastapi import FastAPI, status
4: from fastapi.middleware.cors import CORSMiddleware
5: from pydantic import BaseModel
```
- **Line 1 (`from datetime import datetime`)**: Imports Python's built-in date and time manipulation class. We use this to generate the UTC timestamp in our health check response.
- **Line 2 (`from typing import Dict, Any`)**: Imports standard type hints from Python's `typing` module. `Dict[str, Any]` tells Python and static analyzers that a function returns a dictionary whose keys are strings and whose values can be of any data type.
- **Line 3 (`from fastapi import FastAPI, status`)**:
  - `FastAPI`: The core Python class that provides all the routing, OpenAPI schema generation, and middleware orchestration.
  - `status`: An enumeration of HTTP status codes (e.g., `status.HTTP_200_OK`, `status.HTTP_404_NOT_FOUND`, `status.HTTP_500_INTERNAL_SERVER_ERROR`). Using `status.HTTP_200_OK` is preferred over typing the raw integer `200` because it prevents typos and improves code readability.
- **Line 4 (`from fastapi.middleware.cors import CORSMiddleware`)**: Imports the Cross-Origin Resource Sharing middleware.
- **Line 5 (`from pydantic import BaseModel`)**: Imports Pydantic's base data model class. In FastAPI, any data structure inheriting from `BaseModel` automatically gains data validation, serialization, and JSON schema extraction.

```python
7: # Initialize FastAPI application
8: # FastAPI automatically creates interactive OpenAPI documentation at /docs and /redoc
9: app = FastAPI(
10:     title="HelpWise AI — ITSM Helpdesk Backend",
11:     description="Core REST API service for HelpWise AI ITSM Helpdesk application",
12:     version="1.0.0",
13: )
```
- **Lines 9–13 (`app = FastAPI(...)`)**: Creates the global FastAPI application object.
  - `title`, `description`, and `version` are not just comments—FastAPI directly injects them into the generated OpenAPI specification and displays them at the top of the `/docs` (Swagger UI) page.

```python
15: # CORS (Cross-Origin Resource Sharing) Middleware Configuration
16: origins = [
17:     "http://localhost:5173",
18:     "http://127.0.0.1:5173",
19:     "http://localhost:3000",
20:     "http://127.0.0.1:3000",
21: ]
22: 
23: app.add_middleware(
24:     CORSMiddleware,
25:     allow_origins=origins,
26:     allow_credentials=True,
27:     allow_methods=["*"],
28:     allow_headers=["*"],
29: )
```
- **Lines 16–21 (`origins = [...]`)**: An explicit list of origins that are authorized to communicate with our backend.
  - `http://localhost:5173` and `http://127.0.0.1:5173` represent the default dev ports for Vite.
  - `http://localhost:3000` is included for compatibility with alternate frontends.
- **Lines 23–29 (`app.add_middleware(...)`)**: Hooks `CORSMiddleware` into FastAPI's request pipeline:
  - `allow_origins=origins`: Whitelists only the specified origins. (In production, you never use `["*"]` if `allow_credentials=True` because that is a security vulnerability).
  - `allow_credentials=True`: Allows cookies, authorization headers, or TLS client certificates in cross-origin requests.
  - `allow_methods=["*"]`: Permits all HTTP verbs (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `OPTIONS`).
  - `allow_headers=["*"]`: Permits all headers (`Content-Type`, `Authorization`, custom headers).

```python
32: # Pydantic schema for response validation and automatic API docs
33: class HealthResponse(BaseModel):
34:     status: str
35:     app: str
36:     version: str
37:     timestamp: str
38:     environment: str
```
- **Lines 33–38 (`class HealthResponse(BaseModel)`)**: Defines the contract (data transfer object) for our health check response.
  - Enforces that every response must contain these five string fields.
  - If a developer accidentally returns an integer or omits a field, Pydantic will raise a validation error before sending corrupted data to the client.
  - FastAPI uses this class to document the exact JSON schema in the `/docs` UI.

```python
40: @app.get(
41:     "/",
42:     tags=["Root"],
43:     summary="Root Welcome Endpoint",
44:     description="Returns welcome message and links to API documentation."
45: )
46: def root_endpoint() -> Dict[str, Any]:
47:     """Root endpoint to verify that the service is responsive."""
48:     return {
49:         "message": "Welcome to HelpWise AI — ITSM Helpdesk Backend API",
50:         "docs_url": "/docs",
51:         "health_check": "/health",
52:         "status": "operational"
53:     }
```
- **Line 40 (`@app.get("/")`)**: Route decorator. Tells FastAPI to execute `root_endpoint()` whenever an HTTP `GET` request hits the root path `/`.
- **Lines 42–44 (`tags`, `summary`, `description`)**: Metadata used by Swagger UI to categorize and explain this route.
- **Line 46 (`def root_endpoint() -> Dict[str, Any]:`)**: Standard Python function definition with return type annotation.
- **Lines 48–53**: Returns a Python dictionary. FastAPI automatically converts Python dictionaries into JSON formatted responses with header `application/json`.

```python
55: @app.get(
56:     "/health",
57:     response_model=HealthResponse,
58:     status_code=status.HTTP_200_OK,
59:     tags=["Monitoring"],
60:     summary="Health Check Endpoint",
61:     description="Returns operational status of the backend API for monitoring and readiness probes."
62: )
63: def health_check() -> HealthResponse:
64:     return HealthResponse(
65:         status="healthy",
66:         app="HelpWise AI — ITSM Helpdesk",
67:         version="1.0.0",
68:         timestamp=datetime.utcnow().isoformat() + "Z",
69:         environment="development"
70:     )
```
- **Line 55 (`@app.get("/health")`)**: Route decorator for the health probe.
- **Line 57 (`response_model=HealthResponse`)**: Tells FastAPI to filter and validate the return value through the `HealthResponse` Pydantic model.
- **Line 58 (`status_code=status.HTTP_200_OK`)**: Explicitly sets the HTTP response code to `200`.
- **Line 63 (`def health_check() -> HealthResponse:`)**: Route handler function.
- **Lines 64–70**: Instantiates and returns the `HealthResponse` object. `datetime.utcnow().isoformat() + "Z"` produces an ISO 8601 compliant UTC timestamp (e.g. `2026-10-18T12:38:20.217159Z`), which is the global standard for machine-readable time.

---

## 3. Why Health Check Endpoints Matter in Production

In interviews, junior developers often think `/health` is just a simple "hello world" route. Senior engineers know that `/health` is the **heartbeat of cloud infrastructure**:

1. **Cloud Load Balancers (AWS ALB, GCP Cloud Load Balancing, Azure App Gateway)**:
   - Load balancers poll `/health` every 10–30 seconds.
   - If an instance crashes or becomes unresponsive, the load balancer stops routing traffic to that instance and routes requests to healthy nodes.
2. **Kubernetes Probes**:
   - **Liveness Probe**: Checks if the container is alive. If `/health` returns 500 or times out, Kubernetes restarts the pod.
   - **Readiness Probe**: Checks if the container is ready to accept traffic (e.g. after database connections are established).
3. **Frontend Telemetry & Graceful Degradation**:
   - As implemented in our React frontend, polling `/health` allows the UI to display connection statuses, show latency metrics, and provide clear error messages to the user if the server goes down.

---

## 4. 10 Technical Interview Questions & Answers

### Q1: What is FastAPI, and why did you choose it over Flask or Django?
**Answer**:
"FastAPI is a modern, high-performance web framework for building APIs with Python 3.8+ based on standard Python type hints. I chose it over Flask because FastAPI provides native asynchronous support (ASGI via Starlette), automated data validation via Pydantic, and out-of-the-box interactive OpenAPI/Swagger documentation. Compared to Django, FastAPI is lightweight, has significantly lower latency, and doesn't force a monolithic ORM or template engine on us, which fits our decoupled React SPA architecture perfectly."

### Q2: What is the difference between WSGI and ASGI?
**Answer**:
"WSGI (Web Server Gateway Interface) is synchronous. It processes one request per worker thread at a time, making it inefficient for long-lived connections like WebSockets or high-concurrency I/O. ASGI (Asynchronous Server Gateway Interface) is the asynchronous successor to WSGI. It supports `async` and `await`, allowing a single process to handle thousands of concurrent requests while waiting for slow I/O operations (like database queries or external LLM API calls) without blocking the thread."

### Q3: What is CORS and why is it necessary?
**Answer**:
"CORS stands for Cross-Origin Resource Sharing. For security reasons, browsers enforce the Same-Origin Policy (SOP), preventing a web application on one origin (e.g., `http://localhost:5173`) from making AJAX/fetch requests to a different origin (e.g., `http://127.0.0.1:8000`). By configuring FastAPI's `CORSMiddleware`, we instruct the backend to send HTTP headers like `Access-Control-Allow-Origin: http://localhost:5173`, telling the browser to permit our React frontend to read the API responses."

### Q4: Why did you define a Pydantic `HealthResponse` model instead of returning a plain dictionary?
**Answer**:
"Using a Pydantic `BaseModel` provides type safety, runtime schema validation, automatic serialization, and automatic documentation in OpenAPI/Swagger. If someone modifies the return data with missing or incorrectly typed fields, Pydantic catches it immediately. Plain dictionaries offer none of these guarantees."

### Q5: In `main.py`, why is the function defined as `def health_check()` rather than `async def health_check()`?
**Answer**:
"In FastAPI, if a function does not perform asynchronous I/O (like awaiting an `httpx` request or an async database query), declaring it with `def` allows FastAPI to execute it inside an external threadpool, preventing blocking of the main event loop. If we don't have an `await` statement inside the function, using `def` is clean and idiomatic."

### Q6: How does FastAPI generate Swagger UI documentation automatically?
**Answer**:
"FastAPI analyzes the Python type annotations, Pydantic models, and path operation decorators on each route to construct a standard OpenAPI JSON schema document at `/openapi.json`. It then serves Swagger UI (HTML/JS) at `/docs` and ReDoc at `/redoc`, which consume that JSON schema and render an interactive testing console."

### Q7: What does the `--reload` flag do in Uvicorn?
**Answer**:
"`--reload` enables hot-reloading during local development using a file-watcher like `watchfiles`. Whenever any Python source file in the directory is changed and saved, Uvicorn gracefully reloads the worker process so code changes are reflected immediately without manually stopping and restarting the server."

### Q8: What is the purpose of the ISO 8601 timestamp in the health check?
**Answer**:
"ISO 8601 (`YYYY-MM-DDTHH:MM:SS.mmmmmmZ`) is the international standard format for representing date and time. Appending `Z` explicitly marks the timestamp as Coordinated Universal Time (UTC), avoiding timezone ambiguity across distributed clients and servers."

### Q9: How will we modularize `main.py` when adding MongoDB and ServiceNow integrations?
**Answer**:
"We will use FastAPI's `APIRouter`. Instead of placing all routes in `main.py`, we will create a dedicated `routers/` or `api/` directory (e.g. `routers/tickets.py`, `routers/servicenow.py`, `routers/auth.py`). Each router will manage its own endpoints and schemas, and we will include them in `main.py` using `app.include_router(tickets_router, prefix='/api/v1/tickets')`."

### Q10: How do you secure endpoints in FastAPI?
**Answer**:
"FastAPI provides `fastapi.security` utilities supporting OAuth2 with Password hashing, Bearer JWT tokens, and API Keys via dependency injection (`Depends()`). We can write dependency functions like `get_current_user` that validate tokens on incoming requests before executing protected business logic."
