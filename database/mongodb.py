import pymongo
import pymongo.errors
from typing import Optional, Any
from configuration.config import (
    MONGODB_URI, MONGODB_DB_NAME, CONVERSATIONS_COLLECTION, MEMORY_NODES_COLLECTION,
    CONVERSATIONS_VECTOR_SEARCH_INDEX_NAME, CONVERSATIONS_FULLTEXT_SEARCH_INDEX_NAME,
    MEMORY_NODES_VECTOR_SEARCH_INDEX_NAME
)

from utils.logger import logger

# Global variables for MongoDB connection
client: Optional[pymongo.MongoClient] = None
db: Optional[Any] = None  # Using Any to avoid type issues with pymongo database type
conversations: Optional[Any] = None  # Using Any to avoid type issues with pymongo collection type
memory_nodes: Optional[Any] = None  # Using Any to avoid type issues with pymongo collection type

def validate_mongodb_connection() -> bool:
    """Validate MongoDB connection and return True if successful"""
    global client
    try:
        if client is None:
            raise RuntimeError("MongoDB client not initialized")
        # Test connection with a ping command
        client.admin.command('ping')
        logger.info("MongoDB connection validated successfully")
        return True
    except Exception as e:
        logger.error(f"MongoDB connection validation failed: {e}")
        return False

def get_mongodb_client():
    """Get MongoDB client with proper error handling"""
    try:
        # Create client with connection timeout
        client = pymongo.MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=10000,         # 10 second connection timeout
            socketTimeoutMS=20000,          # 20 second socket timeout
            retryWrites=True
        )
        return client
    except Exception as e:
        logger.error(f"Failed to create MongoDB client: {e}")
        raise RuntimeError(f"MongoDB client creation failed: {e}")

def initialize_mongodb_connection():
    """Initialize MongoDB connection with validation"""
    global client, db, conversations, memory_nodes
    
    try:
        logger.info("Initializing MongoDB connection...")
        client = get_mongodb_client()
        
        # Validate connection
        if not validate_mongodb_connection():
            raise RuntimeError("MongoDB connection validation failed")
        
        # Initialize database and collections
        if client is not None:
            db = client[MONGODB_DB_NAME]
            conversations = db[CONVERSATIONS_COLLECTION]
            memory_nodes = db[MEMORY_NODES_COLLECTION]
        else:
            raise RuntimeError("MongoDB client is None after initialization")
        
        logger.info("MongoDB connection initialized successfully")
        
    except Exception as e:
        logger.error(f"MongoDB initialization failed: {e}")
        raise RuntimeError(f"Failed to initialize MongoDB: {e}")

def initialize_mongodb():
    """Initialize MongoDB collections and indexes"""
    global client, db, conversations, memory_nodes
    
    # Ensure connection is established
    if client is None or db is None:
        initialize_mongodb_connection()
    
    # Ensure all connections are properly initialized
    if client is None or db is None or conversations is None or memory_nodes is None:
        raise RuntimeError("MongoDB connection not properly initialized")
    
    try:
        # Check if conversations collection exists
        if CONVERSATIONS_COLLECTION not in db.list_collection_names():
            logger.info(f"Creating {CONVERSATIONS_COLLECTION} collection...")
            db.create_collection(CONVERSATIONS_COLLECTION)
            
        # Create indexes for conversations collection
        try:
            # Vector search index
            conversations.create_search_index(
                {
                    "name": CONVERSATIONS_VECTOR_SEARCH_INDEX_NAME,
                    "type": "vectorSearch",
                    "definition": {
                        "fields": [
                            {
                                "type": "vector",
                                "path": "embeddings",
                                "numDimensions": 384,
                                "similarity": "cosine",
                            },
                            {"type": "filter", "path": "user_id"}
                        ]
                    }
                }
            )
            logger.info(f"Created vector search index: {CONVERSATIONS_VECTOR_SEARCH_INDEX_NAME}")
            
            # Full-text search index
            conversations.create_search_index(
                {
                    "name": CONVERSATIONS_FULLTEXT_SEARCH_INDEX_NAME,
                    "type": "search",
                    "definition": {
                        "mappings": {
                            "dynamic": False,
                            "fields": {"text": {"type": "string"}},
                        }
                    },
                }
            )
            logger.info(f"Created full-text search index: {CONVERSATIONS_FULLTEXT_SEARCH_INDEX_NAME}")
            
            # TTL index for automatic data cleanup
            conversations.create_index(
                [("timestamp", 1)],
                expireAfterSeconds=30 * 24 * 60 * 60,  # 30 days
                name="timestamp_ttl_index"
            )
            logger.info("Created TTL index for conversations")
            
            # Additional performance indexes
            conversations.create_index(
                [("user_id", 1), ("conversation_id", 1), ("timestamp", 1)],
                name="user_conversation_timestamp_index"
            )
            logger.info("Created compound index for conversation queries")

        except pymongo.errors.PyMongoError as e:
            logger.error(f"Error creating conversation indexes: {e}")

        # Check if memory nodes collection exists
        if MEMORY_NODES_COLLECTION not in db.list_collection_names():
            logger.info(f"Creating {MEMORY_NODES_COLLECTION} collection...")
            db.create_collection(MEMORY_NODES_COLLECTION)
            
        # Create indexes for memory nodes collection
        try:
            # Performance indexes
            memory_nodes.create_index(
                [("importance", pymongo.DESCENDING)], name="importance_index"
            )
            memory_nodes.create_index(
                [("user_id", pymongo.ASCENDING)], name="user_id_index"
            )
            memory_nodes.create_index(
                [("user_id", 1), ("importance", -1), ("access_count", -1)],
                name="user_importance_access_index"
            )
            logger.info("Created performance indexes for memory nodes")
            
            # Vector search index
            memory_nodes.create_search_index(
                {
                    "name": MEMORY_NODES_VECTOR_SEARCH_INDEX_NAME,
                    "type": "vectorSearch",
                    "definition": {
                        "fields": [
                            {
                                "type": "vector",
                                "path": "embeddings",
                                "numDimensions": 384,
                                "similarity": "cosine",
                            },
                            {"type": "filter", "path": "user_id"},
                        ]
                    },
                }
            )
            logger.info(f"Created vector search index: {MEMORY_NODES_VECTOR_SEARCH_INDEX_NAME}")
            
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Error creating memory_nodes indexes: {e}")
            
        logger.info("MongoDB initialization completed successfully")
        
    except Exception as e:
        logger.error(f"MongoDB initialization failed: {e}")
        raise RuntimeError(f"Failed to initialize MongoDB collections: {e}")

def serialize_document(doc):
    doc["_id"] = str(doc["_id"])
    return doc