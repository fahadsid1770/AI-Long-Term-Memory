# AI Long Term Memory Service

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-4EA94B?style=flat&logo=mongodb&logoColor=white)](https://www.mongodb.com/)

A smart AI service that remembers and retrieves your conversations intelligently using vector search and machine learning.

## ✨ What It Does

**Stores conversation memories** → **Finds similar discussions** → **Provides intelligent summaries**

Think of it as a "supercharged memory" for your AI conversations that:
- Remembers important details from past chats
- Finds related conversations automatically  
- Creates smart summaries of your discussions
- Learns what matters most to you over time

## 🚀 Quick Start

### 1. Install
```bash
pip install -r requirements.txt
```

### 2. Configure
```bash
cp sample.env .env
```

Edit `.env` with your settings:
```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 3. Run
```bash
python main.py
```

**Done!** Service runs on `http://localhost:8182`

## 📖 How It Works

```mermaid
graph LR
    A[Add Message] --> B[Generate Embeddings]
    B --> C[Store in MongoDB]
    C --> D[Create Memory if Important]
    E[Search Query] --> F[Find Similar Messages]
    F --> G[Get Context & Summary]
    G --> H[Return Results]
```

### Memory Intelligence
- **Smart Storage**: Only remembers important messages (longer than 30 characters)
- **Similarity Search**: Finds related conversations using AI embeddings
- **Importance Scoring**: Learns what matters most to you
- **Auto-Summarization**: Creates brief summaries of your conversations

## 🛠️ API Usage

### Store a Message
```bash
curl -X POST http://localhost:8182/conversation/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "conversation_id": "chat456", 
    "type": "human",
    "text": "I need to remember that our team meeting is at 3 PM on Fridays"
  }'
```

### Retrieve Memories
```bash
curl "http://localhost:8182/retrieve_memory/?user_id=user123&text=team meeting"
```

**Response:**
```json
{
  "related_conversation": [
    {
      "text": "I need to remember that our team meeting is at 3 PM on Fridays",
      "timestamp": "2023-11-02T08:26:29.829Z"
    }
  ],
  "conversation_summary": "User discussed team meeting schedule for Fridays at 3 PM",
  "similar_memories": [
    {
      "content": "Weekly team sync scheduled every Friday afternoon",
      "similarity": 0.85,
      "importance": 0.7
    }
  ]
}
```

## ⚙️ Configuration

### Required Settings
```env
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### Optional Settings
```env
# Performance
MAX_DEPTH=5                    # How many memories to keep per user
SIMILARITY_THRESHOLD=0.7       # How similar memories must be (0-1)
DECAY_FACTOR=0.99              # How quickly old memories lose importance

# Service
SERVICE_PORT=8182              # Port to run on
DEBUG=false                    # Enable debug mode
```

## 🔧 Python Example

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        # Store a conversation
        await client.post("http://localhost:8182/conversation/", json={
            "user_id": "alice",
            "conversation_id": "work_chat",
            "type": "human", 
            "text": "Remember that client presentation is next Tuesday at 2 PM"
        })
        
        # Find related memories
        result = await client.get(
            "http://localhost:8182/retrieve_memory/",
            params={"user_id": "alice", "text": "client presentation"}
        )
        
        print("Found memories:", result.json())

asyncio.run(main())
```

## 📊 Health Checks

Monitor your service with built-in health endpoints:

```bash
# Basic status
curl http://localhost:8182/health

# Detailed system info  
curl http://localhost:8182/health/detailed
```

## 🐳 Docker Deployment

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8182
CMD ["python", "main.py"]
```

```bash
docker build -t ai-memory .
docker run -p 8182:8182 --env-file .env ai-memory
```

## 🎯 Key Features

| Feature | Description |
|---------|-------------|
| **Vector Search** | Finds semantically similar conversations using AI embeddings |
| **Smart Summarization** | Creates concise summaries of your conversations |
| **Importance Learning** | Automatically identifies and prioritizes important information |
| **Context Awareness** | Provides surrounding conversation context for better understanding |
| **Memory Decay** | Intelligently manages storage by reducing importance of unused memories |
| **Real-time Processing** | Fast embeddings and search using optimized pipelines |
| **Production Ready** | Health checks, rate limiting, error handling, and monitoring |

## 📋 Requirements

- **Python 3.9+**
- **MongoDB** (with vector search - MongoDB 7.0+)
- **OpenRouter API Key** (for AI features like summarization)

## 🆘 Troubleshooting

**Service won't start?**
- Check MongoDB connection string
- Verify OpenRouter API key
- Ensure port 8182 is available

**Memories not being saved?**
- Messages must be >30 characters for automatic memory creation
- Check logs for embedding generation errors
- Verify MongoDB vector indexes exist

**Search not working well?**
- Try adjusting `SIMILARITY_THRESHOLD` (0.6-0.8 range)
- Ensure vector search indexes are created in MongoDB
- Check that embeddings are being generated correctly

## 🔗 Useful Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Basic health check |
| `GET /health/detailed` | System status with metrics |
| `POST /conversation/` | Store conversation messages |
| `GET /retrieve_memory/` | Search and retrieve memories |

## 📈 Performance

| Operation | Typical Time |
|-----------|-------------|
| Store Message | ~200ms |
| Search Memories | ~300ms |
| Health Check | ~20ms |

*Performance varies based on message length and system load*

## 📄 License

MIT License - feel free to use this in your projects!

---

**Built for personal AI memory management** 🤖💭

For full API documentation, visit `http://localhost:8182/docs` when running locally.