import uvicorn
import time
import sys
from datetime import datetime
from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import configuration.config as config
from database.mongodb import initialize_mongodb, initialize_mongodb_connection

# Import models and services
from models.pydantic_models import ErrorResponse, MessageInput
from services.embedding_service import generate_embedding
from services.conversation_service import (
    add_conversation_message,
    generate_conversation_summary,
    get_conversation_context,
    search_memory,
)
from services.memory_service import find_similar_memories
from services.pageindex_service import agentic_router
from utils import error_utils
from utils.logger import logger
# Authentication removed - no longer needed

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

from contextlib import asynccontextmanager

# Define lifespan for async initialization/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    try:
        await initialize_mongodb_connection()
        await initialize_mongodb()
        logger.info("MongoDB initialized successfully during startup")
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB during startup: {e}")
        # In a real production app, you might want to exit here
        # raise RuntimeError(f"Application startup failed: {e}")
    
    yield
    
    # Shutdown logic
    from database.mongodb import client
    if client:
        client.close()
        logger.info("MongoDB connection closed during shutdown")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description=config.APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


@app.get("/health")
async def basic_health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": config.APP_NAME,
        "version": config.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check with dependency validation"""
    from datetime import datetime
    from database.mongodb import client, validate_mongodb_connection
    from services.embedding_service import generate_embedding, get_chat_response
    
    health_status = {
        "status": "healthy",
        "service": config.APP_NAME,
        "version": config.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    overall_healthy = True
    
    # MongoDB Health Check
    try:
        if validate_mongodb_connection():
            health_status["checks"]["mongodb"] = {
                "status": "healthy",
                "response_time_ms": 0  # Could add timing
            }
            logger.debug("MongoDB health check passed")
        else:
            raise Exception("Connection validation failed")
    except Exception as e:
        health_status["checks"]["mongodb"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
        logger.error(f"MongoDB health check failed: {e}")
    
    # Embedding Model Health Check
    try:
        start_time = time.time()
        await generate_embedding("health check test")
        response_time = (time.time() - start_time) * 1000
        
        health_status["checks"]["embedding_model"] = {
            "status": "healthy",
            "response_time_ms": round(response_time, 2)
        }
        logger.debug(f"Embedding model health check passed in {response_time:.2f}ms")
    except Exception as e:
        health_status["checks"]["embedding_model"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
        logger.error(f"Embedding model health check failed: {e}")
    
    # OpenRouter API Health Check
    try:
        start_time = time.time()
        response = await get_chat_response("test")
        response_time = (time.time() - start_time) * 1000
        
        health_status["checks"]["openrouter_api"] = {
            "status": "healthy",
            "response_time_ms": round(response_time, 2)
        }
        logger.debug(f"OpenRouter API health check passed in {response_time:.2f}ms")
    except Exception as e:
        health_status["checks"]["openrouter_api"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
        logger.error(f"OpenRouter API health check failed: {e}")
    
    # System Resources Check
    try:
        import psutil
        health_status["checks"]["system_resources"] = {
            "status": "healthy",
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent if sys.platform != 'win32' else psutil.disk_usage('C:').percent
        }
    except ImportError:
        health_status["checks"]["system_resources"] = {
            "status": "unavailable",
            "message": "psutil not installed"
        }
    except Exception as e:
        health_status["checks"]["system_resources"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Set overall status
    if not overall_healthy:
        health_status["status"] = "degraded"
    
    return health_status

@app.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe - checks if service is ready to accept traffic"""
    try:
        from database.mongodb import validate_mongodb_connection
        
        # Check critical dependencies
        if not validate_mongodb_connection():
            raise HTTPException(status_code=503, detail="MongoDB not ready")
        
        # Quick embedding test
        await generate_embedding("ready")
        
        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service not ready: {str(e)}"
        )

@app.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe - checks if service is running"""
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": time.time() - app_start_time
    }


@app.post("/conversation/")
@limiter.limit("30/minute")  # Allow 30 requests per minute per IP
async def add_message(
    request: Request,
    message: MessageInput
):
    """Add a message to the conversation history"""
    try:
        logger.info(f"Adding message for user {message.user_id}")
        return await add_conversation_message(message)
    except Exception as error:
        logger.error(f"Error adding message: {str(error)}")
        error_response = error_utils.handle_exception(error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response["error"],
        )


@app.get("/retrieve_memory/")
@limiter.limit("60/minute")  # Allow 60 retrieval requests per minute per IP
async def retrieve_memory(
    request: Request,
    user_id: str,
    text: str,
    use_pageindex: bool = False
):
    """
    Retrieve memory items, context, summary, and similar memory nodes in a single request.
    Supports PageIndex for structured navigation if use_pageindex=True.
    """
    try:
        # Validate input parameters
        if not user_id or not user_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id cannot be empty"
            )
        if not text or not text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="text cannot be empty"
            )
        
        # Additional input validation
        if len(text.strip()) > 5000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="text is too long (max 5000 characters)"
            )
        
        user_id = user_id.strip()
        text = text.strip()
        
        logger.info(f"Retrieving memory for user {user_id}")
        
        # Generate embedding for the query text
        vector_query = await generate_embedding(text)

        # NEW: PageIndex Logic
        filter_dict = None
        if use_pageindex:
            logger.info(f"Using PageIndex reasoning for user {user_id}")
            route = await agentic_router(user_id, text)
            if route:
                filter_dict = route
                logger.info(f"PageIndex narrowed search to: {filter_dict}")

        # Search for relevant memory items
        memory_items = await search_memory(user_id, text)

        # Get similar memory nodes from the memory tree (with optional PageIndex filter)
        similar_memories = await find_similar_memories(user_id, vector_query, filter_dict=filter_dict)

        if not memory_items.get("documents"):
            return {
                "related_conversation": "No conversation found",
                "conversation_summary": "No summary found",
                "similar_memories": (
                    similar_memories
                    if similar_memories
                    else "No similar memories found"
                ),
            }

        # Extract conversation ID from the first memory item
        documents = memory_items["documents"]
        if not isinstance(documents, list) or not documents:
            return {
                "related_conversation": "No valid documents found",
                "conversation_summary": "No summary found",
                "similar_memories": (
                    similar_memories
                    if similar_memories
                    else "No similar memories found"
                ),
            }
        object_id = documents[0]["_id"]

        # Retrieve conversation context around the matching memory item
        context = await get_conversation_context(object_id)

        # Generate a detailed summary for the conversation
        summary = await generate_conversation_summary(context["documents"])

        memories = [
            {
                "content": memory["content"],
                "summary": memory["summary"],
                "similarity": memory["similarity"],
                "importance": memory["effective_importance"],
            }
            for memory in similar_memories
        ]

        result = {
            "related_conversation": context["documents"],
            "conversation_summary": summary["summary"],
            "similar_memories": memories if memories else "No similar memories found",
        }

        return result
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as error:
        logger.error(f"Error retrieving memory: {str(error)}")
        error_response = error_utils.handle_exception(error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response["error"],
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.SERVICE_HOST,
        port=config.SERVICE_PORT,
        reload=config.DEBUG,
    )
