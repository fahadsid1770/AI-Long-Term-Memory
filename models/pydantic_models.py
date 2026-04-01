import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class MessageInput(BaseModel):
    user_id: str = Field(..., min_length=1, description="User ID cannot be empty")
    conversation_id: str = Field(..., min_length=1, description="Conversation ID cannot be empty")
    type: str = Field(..., pattern="^(human|ai)$", description="Must be 'human' or 'ai'")
    text: str = Field(..., min_length=1, max_length=10000, description="Message text (max 10000 chars)")
    timestamp: Optional[str] = Field(None, description="UTC timestamp (optional)")

class SearchRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    query: str = Field(..., description="Search query")

class RememberRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    content: str = Field(..., description="Content to remember")

class MemoryNode(BaseModel):
    id: Optional[str] = None
    user_id: str
    content: str
    summary: str = ""
    category: str = "General"
    topic: str = "Uncategorized"
    index_path: str = "/General/Uncategorized"
    importance: float = 1.0
    access_count: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    embeddings: List[float]


class ErrorResponse(BaseModel):
    success: bool = Field(False, description="Operation failed")
    error: str = Field(..., description="Error message")
    traceback: Optional[str] = Field(None, description="Error traceback (debug only)")