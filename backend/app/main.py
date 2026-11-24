import os
import json
from contextlib import asynccontextmanager
from typing import Optional
from dotenv import load_dotenv

# Automatically load .env from root or current directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv()

from fastapi import FastAPI, Header, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.database import init_db, save_message, get_session_messages, session_exists, get_db_connection
from app.gateway import gateway
from app.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    SessionMessagesResponse,
    SessionMessageItem,
    SessionMessageMetadata
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Lyftr AI API",
    version="1.0.0",
    lifespan=lifespan
)

# Custom exception handler to return clean JSON {"detail": ...} without HTML or tracebacks
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)}
    )

# Configure CORS
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
if not origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
def health():
    # Verify DB connection
    conn = get_db_connection()
    try:
        conn.execute("SELECT 1")
    finally:
        conn.close()

    return HealthResponse(
        status="ok",
        keys_configured=gateway.keys_configured,
        cache_enabled=True
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    x_simulate_failure: Optional[str] = Header(None, alias="X-Simulate-Failure")
):
    trimmed_msg = payload.message.strip()
    if not trimmed_msg:
        raise HTTPException(status_code=422, detail="Message cannot be empty or whitespace only")
    if len(trimmed_msg) > 4000:
        raise HTTPException(status_code=422, detail="Message exceeds 4000 characters")

    # Fetch existing conversation history from SQLite
    existing_msgs = get_session_messages(payload.session_id)

    # Build prompt messages for the LLM gateway
    llm_messages = []
    # If custom system prompt provided, use it; else default system prompt
    default_sys = "You are Lyftr AI, an exceptionally smart, capable, and helpful AI assistant."
    system_prompt = payload.system_prompt if payload.system_prompt else default_sys
    llm_messages.append({"role": "system", "content": system_prompt})

    for m in existing_msgs:
        llm_messages.append({"role": m["role"], "content": m["content"]})

    llm_messages.append({"role": "user", "content": trimmed_msg})

    try:
        result = await gateway.generate_reply(
            messages=llm_messages,
            simulate_header=x_simulate_failure
        )
    except RuntimeError as e:
        if str(e) == "all providers unavailable":
            raise HTTPException(status_code=503, detail="all providers unavailable")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail="all providers unavailable")

    # Only save to SQLite upon successful completion
    save_message(payload.session_id, "user", trimmed_msg)
    assistant_meta = {
        "resolution_source": result["metadata"]["resolution_source"],
        "input_tokens": result["metadata"]["input_tokens"],
        "output_tokens": result["metadata"]["output_tokens"]
    }
    save_message(payload.session_id, "assistant", result["reply"], assistant_meta)

    return ChatResponse(
        session_id=payload.session_id,
        reply=result["reply"],
        metadata=result["metadata"]
    )

@app.get("/sessions/{session_id}/messages", response_model=SessionMessagesResponse)
def get_messages(session_id: str):
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail="session not found")

    raw_msgs = get_session_messages(session_id)
    items = []
    for m in raw_msgs:
        meta = None
        if "metadata" in m and m["metadata"]:
            meta = SessionMessageMetadata(
                resolution_source=m["metadata"]["resolution_source"],
                input_tokens=m["metadata"]["input_tokens"],
                output_tokens=m["metadata"]["output_tokens"]
            )
        items.append(SessionMessageItem(
            role=m["role"],
            content=m["content"],
            metadata=meta
        ))

    return SessionMessagesResponse(
        session_id=session_id,
        messages=items
    )
