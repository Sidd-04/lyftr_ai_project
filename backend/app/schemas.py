from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=4000)
    system_prompt: Optional[str] = None

class MessageMetadata(BaseModel):
    resolution_source: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    key_id: Optional[str] = None
    fallback_attempts: int

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    metadata: MessageMetadata

class SessionMessageMetadata(BaseModel):
    resolution_source: str
    input_tokens: int
    output_tokens: int

class SessionMessageItem(BaseModel):
    role: str
    content: str
    metadata: Optional[SessionMessageMetadata] = None

class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: List[SessionMessageItem]

class HealthResponse(BaseModel):
    status: str
    keys_configured: int
    cache_enabled: bool
