import os
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from typing import Optional
from utils.logger import logger

security = HTTPBearer(auto_error=False)

class APIKeyAuth:
    """Simple API Key authentication for production use"""
    
    def __init__(self):
        self.api_key = os.getenv("API_KEY")
        if not self.api_key:
            logger.warning("API_KEY not set. Authentication will be disabled in debug mode.")
    
    async def verify_api_key(self, request: Request) -> Optional[str]:
        """
        Verify API key from Authorization header
        Returns API key if valid, raises HTTPException if invalid
        """
        # Skip authentication in debug mode if no API key is set
        debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        if debug_mode and not self.api_key:
            logger.debug("Debug mode: skipping API key authentication")
            return "debug_mode"
        
        # Check if API key is configured
        if not self.api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API key not configured on server"
            )
        
        # Get authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Parse the authorization header
        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (scheme and credentials):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check scheme
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization scheme. Use Bearer",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify API key
        if credentials != self.api_key:
            logger.warning(f"Invalid API key attempt from {request.client.host if request.client else 'unknown'}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.debug("API key authentication successful")
        return credentials

# Global instance
api_auth = APIKeyAuth()

# Dependency function for FastAPI
async def verify_api_key(request: Request) -> str:
    """FastAPI dependency for API key verification"""
    result = await api_auth.verify_api_key(request)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return result

# Optional authentication dependency (for endpoints that may or may not require auth)
async def optional_verify_api_key(request: Request) -> Optional[str]:
    """Optional API key verification - returns None if no auth provided in debug mode"""
    try:
        return await api_auth.verify_api_key(request)
    except HTTPException as e:
        debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        if debug_mode and e.status_code == status.HTTP_401_UNAUTHORIZED:
            logger.debug("Debug mode: allowing unauthenticated access")
            return None
        raise