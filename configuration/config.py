import os
import sys
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing"""
    pass

class Config:
    """Configuration management with validation"""
    
    def __init__(self):
        self._validated = False
        self._load_config()
    
    def _load_config(self):
        """Load all configuration values"""
        # Memory System Parameters
        self.MAX_DEPTH = int(os.getenv("MAX_DEPTH", "5"))
        self.SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
        self.DECAY_FACTOR = float(os.getenv("DECAY_FACTOR", "0.99"))
        self.REINFORCEMENT_FACTOR = float(os.getenv("REINFORCEMENT_FACTOR", "1.1"))
        
        # Application settings
        self.APP_NAME = "AI-Long-Term-Memory-Service"
        self.APP_VERSION = "1.0.1"
        self.APP_DESCRIPTION = "AI Memory Service for Long-term Conversational Memory"
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"
        
        # Service configuration
        self.SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")
        self.SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8182"))
        
        # Security settings
        self.ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
        
        # MongoDB Configuration
        self.MONGODB_URI = os.getenv("MONGODB_URI")
        self.MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "ai-long-term-memory")
        self.CONVERSATIONS_COLLECTION = "conversations"
        self.MEMORY_NODES_COLLECTION = "memory_nodes"
        self.CONVERSATIONS_VECTOR_SEARCH_INDEX_NAME = "conversations_vector_search_index"
        self.CONVERSATIONS_FULLTEXT_SEARCH_INDEX_NAME = "conversations_fulltext_search_index"
        self.MEMORY_NODES_VECTOR_SEARCH_INDEX_NAME = "memory_nodes_vector_search_index"
        
        # External API Configuration
        self.OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
        self.EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        
        # Performance settings
        self.EMBEDDING_CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "1000"))
        self.EMBEDDING_CACHE_TTL = int(os.getenv("EMBEDDING_CACHE_TTL", "3600"))
        self.MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "5000"))
        
        # Rate limiting
        self.RATE_LIMIT_CONVERSATION = os.getenv("RATE_LIMIT_CONVERSATION", "30/minute")
        self.RATE_LIMIT_MEMORY = os.getenv("RATE_LIMIT_MEMORY", "60/minute")
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Required settings
        if not self.MONGODB_URI:
            errors.append("MONGODB_URI environment variable must be set")
        
        if not self.OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY environment variable must be set")
        
        # Production-specific validations
        if not self.DEBUG:
            if self.SERVICE_HOST == "0.0.0.0" and not os.getenv("DOCKER_ENV"):
                errors.append("SERVICE_HOST should not be 0.0.0.0 in production unless in Docker")
        
        # Validate numeric ranges
        if not (1 <= self.MAX_DEPTH <= 100):
            errors.append("MAX_DEPTH must be between 1 and 100")
        
        if not (0.0 <= self.SIMILARITY_THRESHOLD <= 1.0):
            errors.append("SIMILARITY_THRESHOLD must be between 0.0 and 1.0")
        
        if not (0.0 <= self.DECAY_FACTOR <= 1.0):
            errors.append("DECAY_FACTOR must be between 0.0 and 1.0")
        
        if not (1.0 <= self.REINFORCEMENT_FACTOR <= 2.0):
            errors.append("REINFORCEMENT_FACTOR must be between 1.0 and 2.0")
        
        if not (1 <= self.SERVICE_PORT <= 65535):
            errors.append("SERVICE_PORT must be between 1 and 65535")
        
        # Validate cache settings
        if not (100 <= self.EMBEDDING_CACHE_SIZE <= 10000):
            errors.append("EMBEDDING_CACHE_SIZE must be between 100 and 10000")
        
        if not (300 <= self.EMBEDDING_CACHE_TTL <= 86400):
            errors.append("EMBEDDING_CACHE_TTL must be between 300 and 86400 seconds")
        
        return errors
    
    def validate_and_exit_on_error(self):
        """Validate configuration and exit if there are errors"""
        if self._validated:
            return
        
        errors = self.validate()
        if errors:
            print("❌ Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        
        self._validated = True
        print("✅ Configuration validation successful")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get configuration summary for debugging"""
        return {
            "app": {
                "name": self.APP_NAME,
                "version": self.APP_VERSION,
                "debug": self.DEBUG,
                "host": self.SERVICE_HOST,
                "port": self.SERVICE_PORT
            },
            "database": {
                "uri_configured": bool(self.MONGODB_URI),
                "database_name": self.MONGODB_DB_NAME
            },
            "security": {
                "allowed_origins": len(self.ALLOWED_ORIGINS)
            },
            "memory_system": {
                "max_depth": self.MAX_DEPTH,
                "similarity_threshold": self.SIMILARITY_THRESHOLD,
                "decay_factor": self.DECAY_FACTOR,
                "reinforcement_factor": self.REINFORCEMENT_FACTOR
            },
            "performance": {
                "embedding_cache_size": self.EMBEDDING_CACHE_SIZE,
                "embedding_cache_ttl": self.EMBEDDING_CACHE_TTL,
                "max_request_size": self.MAX_REQUEST_SIZE
            }
        }

# Global configuration instance
config = Config()

# Backwards compatibility - export individual variables
MAX_DEPTH = config.MAX_DEPTH
SIMILARITY_THRESHOLD = config.SIMILARITY_THRESHOLD
DECAY_FACTOR = config.DECAY_FACTOR
REINFORCEMENT_FACTOR = config.REINFORCEMENT_FACTOR
APP_NAME = config.APP_NAME
APP_VERSION = config.APP_VERSION
APP_DESCRIPTION = config.APP_DESCRIPTION
DEBUG = config.DEBUG
SERVICE_HOST = config.SERVICE_HOST
SERVICE_PORT = config.SERVICE_PORT
MONGODB_URI = config.MONGODB_URI
MONGODB_DB_NAME = config.MONGODB_DB_NAME
CONVERSATIONS_COLLECTION = config.CONVERSATIONS_COLLECTION
MEMORY_NODES_COLLECTION = config.MEMORY_NODES_COLLECTION
CONVERSATIONS_VECTOR_SEARCH_INDEX_NAME = config.CONVERSATIONS_VECTOR_SEARCH_INDEX_NAME
CONVERSATIONS_FULLTEXT_SEARCH_INDEX_NAME = config.CONVERSATIONS_FULLTEXT_SEARCH_INDEX_NAME
MEMORY_NODES_VECTOR_SEARCH_INDEX_NAME = config.MEMORY_NODES_VECTOR_SEARCH_INDEX_NAME

# Validate configuration on import
if __name__ != "__main__":
    config.validate_and_exit_on_error()