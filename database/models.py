import datetime
from fastapi import HTTPException
from services.embedding_service import generate_embedding
from utils.logger import logger

class Message:
    def __init__(self, message_data, embeddings=None):
        self.user_id = message_data.user_id.strip()
        self.conversation_id = message_data.conversation_id.strip()
        self.type = message_data.type
        self.text = message_data.text.strip()
        self.timestamp = self.parse_timestamp(message_data.timestamp)
        self.embeddings = embeddings

    @classmethod
    async def create(cls, message_data):
        embeddings = await generate_embedding(message_data.text.strip())
        return cls(message_data, embeddings)
        
    def parse_timestamp(self, timestamp):
        if isinstance(timestamp, datetime.datetime):
            if timestamp.tzinfo is None:
                return timestamp.replace(tzinfo=datetime.timezone.utc)
            return timestamp
            
        if timestamp and isinstance(timestamp, str) and timestamp.strip():
            try:
                # Handle 'Z' suffix and other ISO formats
                return datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Invalid timestamp format: {timestamp}, defaulting to now.")
        
        return datetime.datetime.now(datetime.timezone.utc)
        
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "type": self.type,
            "text": self.text,
            "timestamp": self.timestamp,
            "embeddings": self.embeddings,
        }