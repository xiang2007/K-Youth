# K-Youth Week 3 — Full-Stack AI Chat Application

> **Goal:** Build and containerize a full-stack chat application with a frontend, backend, and AI model integration.

---

## Project Overview

A containerized chat application that lets users upload PDFs (resumes) for skill-gap analysis against job postings, or simply chat with an AI model. The system consists of three Docker services:

- **Frontend** — A single-page Bootstrap chat UI with client-side PDF text extraction (PDF.js)
- **Backend** — A FastAPI server that proxies chat requests and performs skill-gap analysis using an LLM
- **Ollama** — A local AI model server (runs on CPU)

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (24+)
- [Docker Compose](https://docs.docker.com/compose/) (v2.20+)

---

## Setup Instructions

### 1. Clone and navigate

```bash
git clone <your-repo-url>
cd K-Youth/week_3
```

### 2. Configure environment variables

Copy the example file and adjust as needed:

```bash
cp .env.example .env
```

Edit `.env` to set:

| Variable | Default | Description |
|---|---|---|
| `BACKEND_URL` | `http://backend:8000` | URL of the backend service (used by the frontend container) |
| `OLLAMA_HOST` | `http://ollama:11434` | URL of the Ollama service (used by the backend container) |
| `OLLAMA_MODEL` | `llama3.2:latest` | Default Ollama model for chat |
| `JOBS_DB_PATH` | (see docker-compose.yml) | Path to the SQLite jobs database inside the backend container |

> **Note:** `BACKEND_URL` and `OLLAMA_HOST` are also set directly in `docker-compose.yml` under each service's `environment:` block. The `.env` file provides local-development overrides.

### 3. Install dependencies (optional, for local development)

Each service uses [`uv`](https://github.com/astral-sh/uv) for dependency management. To run a service outside Docker:

```bash
# Backend
cd backend
uv sync --locked
uv run uvicorn src.app:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
uv sync --locked
uv run uvicorn src.app:app --host 0.0.0.0 --port 8080
```

### 4. Pull the AI model

Before starting the application, pull the model(s) you want to use into the Ollama container:

```bash
# Pull the default model (llama3.2)
docker compose exec ollama ollama pull llama3.2

# Or pull a specific version
docker compose exec ollama ollama pull llama3.2:latest

# Or pull a different model (e.g., mistral, gemma, codellama)
docker compose exec ollama ollama pull mistral
```

> **Tip:** Check available models at <https://ollama.com/library>. Smaller models (e.g., `llama3.2`, `gemma:2b`) download faster and run on CPU. Larger models (e.g., `llama3.1:70b`) require more RAM and will be slower.

---

## Usage

### Start the application

```bash
docker compose up --build
```

This starts all three services:

| Service | Container Port | Host Port | Access |
|---|---|---|---|
| Frontend | 8080 | 8080 | http://localhost:8080 |
| Backend | 8000 | 8000 | http://localhost:8000 |
| Ollama | 11434 | 11435 | http://localhost:11435 |

### Stop the application

```bash
docker compose down
```

To also remove persisted Ollama data:

```bash
docker compose down -v
```

### Using the application

1. Open **http://localhost:8080** in your browser.
2. **Chat without a PDF:** Type a message and press Enter or click Send. The backend routes the message to Ollama (or Gemini, if configured) and returns the AI's response.
3. **Skill-gap analysis:** Click "Attach PDF" and select a resume PDF. PDF.js extracts the text client-side. Type a message (or leave it empty) and send. The backend compares the resume's skills against job postings in the SQLite database and returns a formatted skill-gap report.

#### Expected input/output

- **Chat:**
  - Input: `{ "message": "Explain Docker networking" }`
  - Output: `{ "reply": "Docker networking allows containers to communicate..." }`

- **Skill-gap analysis:**
  - Input: `{ "message": "Analyze this resume", "pdf_text": "Python, Docker, SQL..." }`
  - Output: `{ "reply": "Missing skills: kubernetes, tensorflow Matching skills: python, docker, sql" }`

---

## API / Function Reference

### Backend — `POST /chat`

**Endpoint:** `http://localhost:8000/chat`

**Request body (JSON):**

```json
{
  "message": "string",       // required — user's chat message
  "pdf_text": "string | null", // optional — extracted PDF text for skill analysis
  "model": "llama3.2:latest"   // optional — AI model to use
}
```

**Response (JSON):**

```json
{
  "reply": "string"   // AI response or skill-gap analysis result
}
```

**Behavior:**
- If `pdf_text` is provided: extracts skills from the text via Ollama, compares against the jobs database, and returns missing/matching skills.
- If `pdf_text` is absent: forwards the message to the configured AI model (Ollama or Gemini) and returns the response.

### Frontend — `GET /` and `POST /chat`

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Serves the chat UI (`index.html`) |
| `/chat` | POST | Proxies requests to the backend service |

The frontend proxy forwards the JSON payload to `BACKEND_URL/chat` using `httpx.AsyncClient` with a 120-second timeout. Errors from the backend are wrapped as `{"error": detail}` and returned with the original status code.

### Frontend JavaScript — Key Functions

| Function | Location | Purpose |
|---|---|---|
| `send()` | `index.html` | Sends the user's message (+ optional PDF text) to the backend via `fetch('/chat', ...)` |
| `addMessage(role, text)` | `index.html` | Appends a chat bubble to the history div |
| `escHtml(str)` | `index.html` | Escapes HTML entities to prevent XSS |
| PDF extraction (inline) | `index.html` | Uses PDF.js to read uploaded PDFs and extract text client-side |

### Docker Network Communication

The frontend and backend communicate over the default Docker bridge network. The frontend container resolves `backend` (the service name) to the backend container's IP and connects on port 8000. Similarly, the backend resolves `ollama` to the Ollama container on port 11434.

---

## Data / Assumptions

### Data Flow

```
Browser → Frontend (port 8080) → Backend (port 8000) → Ollama (port 11434)
```

1. User selects a PDF → PDF.js extracts text in the browser
2. User types a message and clicks Send → `POST /chat` with `{ message, pdf_text }`
3. Frontend proxies the request to the backend service via `http://backend:8000/chat`
4. Backend either:
   - Runs skill-gap analysis (if `pdf_text` present) → calls `find_skill_gaps_from_text()` → returns formatted result
   - Calls the AI model (if no `pdf_text`) → returns model response
5. Frontend receives the JSON response and displays it as a chat bubble

### Data Structures

**Chat request JSON:**
```json
{ "message": "string", "pdf_text": "string | null", "model": "string" }
```

**Chat response JSON:**
```json
{ "reply": "string" }
```

### Assumptions

- **PDF content:** PDFs are processed client-side by PDF.js. Only text layers are extracted (scanned/image PDFs without OCR will yield empty text).
- **PDF size:** No explicit size limit is enforced. Very large PDFs may cause timeout or memory issues.
- **Message length:** No maximum message length is enforced.
- **AI model:** The default model is `llama3.2:latest` via Ollama. Gemini is supported as a fallback if `GOOGLE_API_KEY` is set (not included in docker-compose for security).
- **Database:** The jobs database (`jobs_d3_eval.db`) contains 8 sample Malaysian job postings. It is bundled inside the backend container.
- **No persistence:** Chat history is not saved. Each page load starts fresh.

---

## Testing

### Test Cases

#### Frontend Tests

| # | Scenario | Steps | Expected Result |
|---|----------|-------|-----------------|
| F1 | Send a chat message (no PDF) | 1. Open http://localhost:8080<br>2. Type a message<br>3. Click Send | Message bubble appears; AI reply appears after a short delay |
| F2 | Attach a PDF and send a message | 1. Open http://localhost:8080<br>2. Click "Attach PDF", select a resume<br>3. Click Send | Skill-gap report appears in the format `Missing skills: ...\nMatching skills: ...` |
| F3 | Send a message after clearing PDF | 1. Attach a PDF, send a message<br>2. Send another message without attaching a new PDF | AI chat response (not a skill-gap report) — the PDF text is cleared after each message |
| F4 | Frontend proxy error handling | 1. Stop the backend container (`docker compose stop backend`)<br>2. Send a message from the frontend | An error toast appears saying the backend is unavailable |

#### Backend Tests (Postman / curl)

The backend runs at **http://localhost:8000**. You can test it with **Postman** or **curl**.

##### Postman Setup

1. Create a new **POST** request to `http://localhost:8000/chat`
2. **Headers** tab → add `Content-Type: application/json`
3. **Body** tab → select **raw** + **JSON** → paste one of the payloads below
4. Click **Send**

##### Test Cases

| # | Scenario | Request Body | Expected Response |
|---|----------|-------------|-------------------|
| B1 | Chat with default model (llama3.2) | `{"message": "What is Docker?"}` | `{"reply": "..."}` with an AI-generated answer |
| B2 | Chat with a specific model | `{"message": "Explain REST", "model": "llama3.2:latest"}` | `{"reply": "..."}` |
| B3 | Skill-gap analysis with PDF text | `{"message": "Analyze", "pdf_text": "Python, Docker, SQL"}` | `{"reply": "Missing skills: ...\nMatching skills: python, docker, sql"}` |
| B4 | Missing jobs database | `{"message": "test", "pdf_text": "Python"}` (when DB is absent) | `{"detail": "Jobs database not found"}` (HTTP 500) |
| B5 | Ollama unavailable | `{"message": "Hello"}` (when Ollama is stopped) | `{"detail": "Model unavailable"}` (HTTP 503) |

##### Equivalent curl Commands

```bash
# B1 — Chat (no PDF)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, explain quantum computing"}'

# B3 — Skill-gap analysis
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze", "pdf_text": "Python, Docker, SQL, Machine Learning"}'

# B5 — Test with a different model
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "model": "mistral"}'
```

#### Docker Network Verification

The frontend and backend communicate over Docker's default bridge network using service names as hostnames. Here's how to verify the connections:

```bash
# 1. Verify all three containers are running
docker compose ps

# 2. From the frontend container, ping the backend
docker compose exec frontend curl -s -o /dev/null -w "%{http_code}" http://backend:8000/chat \
  -X POST -H "Content-Type: application/json" \
  -d '{"message": "health check"}'

# 3. From the backend container, ping Ollama
docker compose exec backend curl -s http://ollama:11434/api/tags

# 4. From the host, verify the frontend proxy works end-to-end
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello via frontend proxy"}'
```

**Expected results:**

| Connection | Command | Expected |
|---|---|---|
| Frontend → Backend | `curl` from frontend container to `http://backend:8000` | HTTP 200 with `{"reply": "..."}` |
| Backend → Ollama | `curl` from backend container to `http://ollama:11434/api/tags` | JSON list of loaded models |
| Browser → Frontend proxy | `curl` from host to `http://localhost:8080/chat` | Response proxied from backend |

To reproduce the full test flow:

1. **Start the application:**
   ```bash
   cd week_3
   docker compose up --build
   ```

2. **Wait for all services to be healthy** (check with `docker compose ps`)

3. **Run the backend tests** (section B1–B5 above) to verify the API layer

4. **Run the frontend tests** (section F1–F4) to verify the UI and proxy layer

5. **Run the Docker network verification** to confirm inter-container connectivity

---

## Limitations

- **No user authentication** — anyone with access to the frontend can send messages.
- **No chat history persistence** — messages are not saved between sessions or page reloads.
- **No conversation context** — each message is independent; the model does not receive prior messages.
- **PDF processing is client-side only** — scanned/image PDFs without a text layer will produce empty results. No server-side PDF parsing is implemented.
- **Ollama model performance** — `llama3.2:latest` is a small model. Responses may be short or inaccurate for complex queries.
- **No Gemini configuration in docker-compose** — the Gemini fallback requires a `GOOGLE_API_KEY` set outside the compose file (for security).
- **Single-user deployment** — the system is designed for local use; no load balancing or horizontal scaling is configured.
- **No temp files** — PDF text is passed as a string directly to `find_skill_gaps_from_text()`, avoiding file I/O entirely.

---

## Architecture Reflection

### Design Choices

**Microservices (frontend/backend separation):** The application is split into two independent services — a frontend that serves the UI and proxies API calls, and a backend that handles business logic (skill-gap analysis, AI model routing). This separation allows each service to be developed, tested, and scaled independently.

**Containerization with Docker Compose:** Each service runs in its own container with isolated dependencies. Docker Compose orchestrates the three services (frontend, backend, Ollama) on a shared bridge network, enabling inter-service communication via service names (e.g., `http://backend:8000`). This makes the application portable — it runs identically on any machine with Docker.

**Local AI with Ollama:** Rather than relying on external APIs, the application uses Ollama to run models locally. This keeps data private (resumes never leave the machine) and avoids API costs.

### Trade-offs

- **Docker Compose simplicity vs. production readiness:** Docker Compose is excellent for local development and small deployments, but lacks health checks, rolling updates, and auto-scaling that a Kubernetes cluster would provide. For this project, Compose was the right choice — it keeps the setup simple and reproducible.
- **Bootstrap + vanilla JS vs. a frontend framework:** The frontend uses Bootstrap 5 and vanilla JavaScript rather than React or Vue. This minimizes build complexity and keeps the Dockerfile lightweight (Python + FastAPI serving static HTML, no Node.js build step). The trade-off is reduced interactivity and state management compared to a SPA framework.
- **Client-side PDF extraction vs. server-side:** PDF.js runs in the browser, which avoids uploading sensitive resume files to the server. The trade-off is that large PDFs increase browser memory usage and scanned PDFs without text layers are not supported.

### Improvements

If given more time, the following changes would be made:

1. **Server-side PDF parsing** — Add a backend endpoint that accepts PDF file uploads and parses them with a library like `pypdf` or `pdfplumber`, supporting scanned documents via OCR.
2. **Conversation history** — Store messages in a database (e.g., SQLite or PostgreSQL) and pass conversation context to the AI model for coherent multi-turn interactions.
3. **Authentication** — Add user login (JWT or session-based) to protect the API and persist user-specific data.
4. **Cloud deployment** — Deploy the application to a cloud provider (e.g., AWS, GCP, or Railway) with proper CI/CD, monitoring, and scaling.
5. **Health checks** — Add Docker health checks to the compose file so services only start when their dependencies are truly ready.
6. **Better error handling** — Wrap Ollama and Gemini calls in retry logic with exponential backoff instead of failing immediately.