import os
from dotenv import load_dotenv

load_dotenv()

# Constants
MAX_DEPTH = 5
SIMILARITY_THRESHOLD = 0.7
DECAY_FACTOR = 0.99
REINFORCEMENT_FACTOR = 1.1

# Application settings
APP_NAME = "AI-Long-Term-Memory-Service"
APP_VERSION = "1.0"
APP_DESCRIPTION = "AI Memory Service"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Service configuration
SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8182"))

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = "ai-long-term-memory"
CONVERSATIONS_COLLECTION = "conversations"
MEMORY_NODES_COLLECTION = "memory_nodes"
CONVERSATIONS_VECTOR_SEARCH_INDEX_NAME = "conversations_vector_search_index"
CONVERSATIONS_FULLTEXT_SEARCH_INDEX_NAME = "conversations_fulltext_search_index"
MEMORY_NODES_VECTOR_SEARCH_INDEX_NAME = "memory_nodes_vector_search_index"