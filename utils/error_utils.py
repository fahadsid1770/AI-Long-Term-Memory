import traceback
import sys
from typing import Dict, Any, Optional
from fastapi import HTTPException, Request
import configuration.config as config
from utils.logger import logger
from datetime import datetime
import uuid

# Custom exception classes for better error handling
class AIMemoryException(Exception):
    """Base exception for AI Memory service"""
    def __init__(self, message: str, error_code: str = "GENERAL_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()
        self.error_id = str(uuid.uuid4())[:8]
        super().__init__(message)

class DatabaseException(AIMemoryException):
    """Database related errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATABASE_ERROR", details)

class EmbeddingException(AIMemoryException):
    """Embedding generation errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "EMBEDDING_ERROR", details)

class ValidationException(AIMemoryException):
    """Input validation errors"""
    def __init__(self, message: str, field: str = "", details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["field"] = field
        super().__init__(message, "VALIDATION_ERROR", details)

class AuthenticationException(AIMemoryException):
    """Authentication errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTH_ERROR", details)

class RateLimitException(AIMemoryException):
    """Rate limiting errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "RATE_LIMIT_ERROR", details)

def get_request_context(request: Optional[Request] = None) -> Dict[str, Any]:
    """Extract context information from request"""
    context = {}
    if request:
        context.update({
            "method": request.method,
            "url": str(request.url),
            "client_ip": getattr(request.client, 'host', 'unknown') if request.client else 'unknown',
            "user_agent": request.headers.get("user-agent", "unknown"),
            "request_id": getattr(request.state, 'request_id', None)
        })
    return context

def format_error_response(
    error: Exception,
    request: Optional[Request] = None,
    include_context: bool = True
) -> Dict[str, Any]:
    """
    Format an error as a standard API response with enhanced context.
    
    Args:
        error: The exception to format
        request: Optional FastAPI request object for context
        include_context: Whether to include request context
        
    Returns:
        Dict: A standardized error response
    """
    error_id = str(uuid.uuid4())[:8]
    
    # Handle custom exceptions
    if isinstance(error, AIMemoryException):
        error_detail = error.message
        error_code = error.error_code
        details = error.details
        error_id = error.error_id
    else:
        error_detail = str(error)
        error_code = "INTERNAL_ERROR"
        details = {}
    
    # Log the error with context
    context = get_request_context(request) if include_context and request else {}
    logger.error(
        f"Error [{error_id}]: {error_detail}",
        extra={
            "error_id": error_id,
            "error_code": error_code,
            "error_type": type(error).__name__,
            "context": context,
            "details": details
        }
    )

    response = {
        "success": False,
        "error": error_detail,
        "error_code": error_code,
        "error_id": error_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add details if available
    if details:
        response["details"] = details
    
    # Add context in debug mode
    if config.DEBUG:
        response["traceback"] = traceback.format_exc()
        if context:
            response["context"] = context

    return response

def handle_exception(
    error: Exception,
    request: Optional[Request] = None,
    operation: str = "unknown"
) -> Dict[str, Any]:
    """
    Handle an exception and return an appropriate response with enhanced logging.
    
    Args:
        error: The exception to handle
        request: Optional FastAPI request object for context
        operation: Description of the operation that failed
        
    Returns:
        Dict: A standardized error response
    """
    # Don't handle HTTPExceptions - let FastAPI handle them
    if isinstance(error, HTTPException):
        logger.warning(f"HTTP Exception in {operation}: {error.status_code} - {error.detail}")
        raise error
    
    # Log performance impact for certain errors
    if isinstance(error, (DatabaseException, EmbeddingException)):
        logger.warning(f"Performance impacting error in {operation}: {type(error).__name__}")
    
    # Enhanced error logging
    logger.error(
        f"Exception in {operation}: {str(error)}",
        extra={
            "operation": operation,
            "error_type": type(error).__name__,
            "traceback": traceback.format_exc()
        }
    )

    return format_error_response(error, request)

def log_performance_metric(operation: str, duration: float, success: bool = True, **kwargs):
    """Log performance metrics for monitoring"""
    logger.info(
        f"Performance: {operation}",
        extra={
            "metric_type": "performance",
            "operation": operation,
            "duration_ms": duration * 1000,
            "success": success,
            **kwargs
        }
    )

def log_business_event(event: str, user_id: Optional[str] = None, **kwargs):
    """Log business events for analytics"""
    logger.info(
        f"Business Event: {event}",
        extra={
            "metric_type": "business_event",
            "event": event,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
    )