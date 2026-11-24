# Lyftr AI — Full-Stack Resilient LLM Gateway & Chatbot

A high-performance, resilient AI chatbot built with FastAPI, SQLite, LiteLLM, and React (Vite). Designed for mission-critical conversational workflows with automatic two-key failover, sub-millisecond response caching, and precise per-request token accounting.

---

## 1. Live URLs
- **GitHub Repository**: [https://github.com/Sidd-04/lyftr_ai_project](https://github.com/Sidd-04/lyftr_ai_project)
- **Frontend App**: [https://lyftr-ai-app.vercel.app](https://lyftr-ai-app.vercel.app)
- **Backend API**: [https://lyftr-ai-project.onrender.com](https://lyftr-ai-project.onrender.com)

---

## 2. Run locally: with Docker and without

### Prerequisites
- Node.js 18+ & npm
- Python 3.11+
- Docker & Docker Compose (optional for containerized run)

### Method A: With Docker Compose (Mandatory Specification)
Start the entire stack with a single command:
```bash
make up
```
- **Backend**: Runs on [http://localhost:8000](http://localhost:8000)
- **Frontend**: Runs on [http://localhost:3000](http://localhost:3000)
- **Data Volume**: Named volume `lyftr-data` mounted at `/data/app.db` ensuring chat history survives container restarts.

To stop the services:
```bash
make down
```

---

### Method B: Without Docker (Native Development)

#### 1. Setup Backend:
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
cp ../.env.example .env
```
Run tests:
```bash
PYTHONPATH=. pytest tests/test_api.py -v
```
Start backend server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Setup Frontend:
```bash
cd frontend
npm install
npm run dev -- --port 3000
```
Visit [http://localhost:3000](http://localhost:3000).

---

## 3. Design decisions: key fallback, caching, SQLite session storage

### Automatic Key Fallback & Resilience
- **Key Pool Architecture**: The gateway accepts a comma-delimited pool of API keys (`LLM_API_KEYS=key_1,key_2,...`).
- **Graceful Failover**: When any key triggers an HTTP 429 (Rate Limit / Quota Exceeded), 500, 502, or 503 error, LiteLLM automatically intercepts the exception, records the failure attempt count, and retries the exact query on the next key in the pool.
- **Fail-Safe Exhaustion**: If all keys in the pool fail, the server responds with a clean `503 {"detail": "all providers unavailable"}` without exposing internal stack traces or HTML errors. Crucially, failed requests are **never added to the SQLite history**.

### High-Speed Response Caching
- **Deterministic Cache Key**: Computed using a SHA-256 hash of the canonical JSON representation of `(model + full_messages_list)`:
  $$\text{Cache Key} = \text{SHA256}(\text{model} + [\{\text{role}, \text{content}\}_{\text{system} + \text{history} + \text{new\_msg}}])$$
- **Instantaneous Resolution**: When an identical conversation context is re-submitted (e.g., repeating the first message in a brand new session), the response is delivered from cache in `< 5ms`, tagged with `LLM_CACHE`, `key_id: null`, and identical token counts.
- Any change in system prompt, previous turns, or query immediately triggers `LIVE_INFERENCE`.

### SQLite Session Storage
- History is maintained in SQLite at the path designated by `DATABASE_URL` (default: `/data/app.db` under a Docker volume).
- Tables and indexes (`idx_messages_session_id`) are automatically verified and created on startup via FastAPI lifecycle handlers (`@asynccontextmanager lifespan`).
- The client only transmits the latest turn, preventing client tampering and reducing network overhead. Old messages are retrieved directly via `GET /sessions/{session_id}/messages`.

---

## 4. Verification: how to see failover, cache hits and per-message token usage

### 1. Verifying Automatic Failover with `X-Simulate-Failure`
You can trigger failure simulation directly from the frontend dropdown or using `curl`:

- **Fail key 1 (429 Rate Limit) ➔ Routes to key 2:**
  ```bash
  curl -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -H "X-Simulate-Failure: key_1=429" \
    -d '{"session_id": "test-failover", "message": "Explain quantum computing"}'
  ```
  *Response:* `200 OK`, `metadata.key_id = "key_2"`, `fallback_attempts = 1`.

- **Fail All Keys (*=429) ➔ Clean 503:**
  ```bash
  curl -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -H "X-Simulate-Failure: *=429" \
    -d '{"session_id": "test-exhaustion", "message": "Will this fail?"}'
  ```
  *Response:* `503 {"detail": "all providers unavailable"}`. Verified: nothing is written to SQLite history.

### 2. Verifying Response Caching
1. Send message: `"What is the speed of light?"` in a new session.
   - UI reports: `LIVE_INFERENCE`, `key_id: "key_1"`, Latency: `~600-900ms`.
2. Reload page (starts a new session) and send the exact same message: `"What is the speed of light?"`.
   - UI reports: `LLM_CACHE`, `key_id: null`, Latency: `< 5ms`.

### 3. Verifying Per-Message Token Usage
- Every reply metadata footer displays individual `input_tokens` and `output_tokens` computed specifically for that prompt + context, never a cumulative running total.

---

## 5. Setup Used: your editor and AI tools
- **Operating Environment**: Windows 11 / Linux Alpine containers
- **Editor / Workspace**: Visual Studio Code & Google Antigravity
- **AI Tooling**: Gemini 2.5 Pro / Flash models via LiteLLM
- **Frameworks**: FastAPI 0.110+, React 18, Vite 5, SQLite3, Nginx Alpine

---

## 6. Bonus features: what you added beyond the requirements and why
1. **Interactive Failure Simulator Toolbar**:
   - An intuitive header control in the UI allows evaluators and visitors to simulate key failures (`key_1=429`, `key_1=500`, `*=429`, or custom pairs) on the fly without needing terminal or Postman.
2. **Visual Status Diagnostics**:
   - Real-time connection badge verifying `/health`, live key pool count, and SQLite persistence status.
3. **Collapsible Session System Prompt Drawer**:
   - Accessible via standard `system-prompt-input` attribute, allowing dynamic customization of the model's persona per session.
4. **Instant Quick-Test Prompts**:
   - One-click interactive prompt cards on the landing page to demonstrate cache hits and failover immediately.
5. **Modern Cyber-Dark SaaS Theme**:
   - Custom Glassmorphism UI with violet/cyan gradients, JetBrains Mono typography, custom micro-interactions, and responsive layout.

---

## 7. Automated Test Suite
To run all tests locally:
```bash
make test-backend
```
Coverage includes:
- Health check verification (`GET /health`)
- Live inference execution (`POST /chat`)
- Cache hit verification (`LLM_CACHE`, identical reply, matching tokens, `null` key)
- Multi-turn conversation persistence in SQLite
- Session history retrieval (`GET /sessions/{session_id}/messages`)
- 404 handler on nonexistent sessions
- Failover simulation for `key_1=429` and `key_1=500`
- Provider exhaustion clean `503` without database pollution
- 422 input validation (empty message, length > 4000 chars, malformed JSON)
