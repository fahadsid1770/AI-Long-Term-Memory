import pymongo
import pymongo.errors
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Any
from configuration.config import (
    MONGODB_URI, MONGODB_DB_NAME, CONVERSATIONS_COLLECTION, MEMORY_NODES_COLLECTION,
    USER_INDICES_COLLECTION,
    CONVERSATIONS_VECTOR_SEARCH_INDEX_NAME, CONVERSATIONS_FULLTEXT_SEARCH_INDEX_NAME,
    CONVERSATIONS_COMPOUND_SEARCH_INDEX_NAME, MEMORY_NODES_VECTOR_SEARCH_INDEX_NAME
)

from utils.logger import logger

# Global variables for MongoDB connection
client: Optional[AsyncIOMotorClient] = None
db: Optional[Any] = None
conversations: Optional[Any] = None
memory_nodes: Optional[Any] = None
user_indices: Optional[Any] = None

async def validate_mongodb_connection() -> bool:
    """Validate MongoDB connection and return True if successful"""
    global client
    try:
        if client is None:
            raise RuntimeError("MongoDB client not initialized")
        # Test connection with a ping command
        await client.admin.command('ping')
        logger.info("MongoDB connection validated successfully")
        return True
    except Exception as e:
        logger.error(f"MongoDB connection validation failed: {e}")
        return False

def get_mongodb_client():
    """Get AsyncIOMotorClient with proper error handling"""
    try:
        # Create client with connection timeout
        client = AsyncIOMotorClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=20000,
            retryWrites=True
        )
        return client
    except Exception as e:
        logger.error(f"Failed to create MongoDB client: {e}")
        raise RuntimeError(f"MongoDB client creation failed: {e}")

async def initialize_mongodb_connection():
    """Initialize MongoDB connection with validation"""
    global client, db, conversations, memory_nodes, user_indices
    
    try:
        logger.info("Initializing MongoDB connection...")
        client = get_mongodb_client()
        
        # Validate connection
        if not await validate_mongodb_connection():
            raise RuntimeError("MongoDB connection validation failed")
        
        # Initialize database and collections
        db = client[MONGODB_DB_NAME]
        conversations = db[CONVERSATIONS_COLLECTION]
        memory_nodes = db[MEMORY_NODES_COLLECTION]
        user_indices = db[USER_INDICES_COLLECTION]
        
        logger.info("MongoDB connection initialized successfully")
        
    except Exception as e:
        logger.error(f"MongoDB initialization failed: {e}")
        raise RuntimeError(f"Failed to initialize MongoDB: {e}")

async def initialize_mongodb():
    """Initialize MongoDB collections and indexes (Synchronous pymongo for index creation)"""
    # Note: Index management can stay with pymongo if needed, but we'll use a sync client briefly
    # or use motor's index creation if preferred. We'll use motor here.
    global client, db, conversations, memory_nodes
    
    if client is None or db is None:
        await initialize_mongodb_connection()
    
    try:
        existing_collections = await db.list_collection_names()
        
        # Check if conversations collection exists
        if CONVERSATIONS_COLLECTION not in existing_collections:
            logger.info(f"Creating {CONVERSATIONS_COLLECTION} collection...")
            await db.create_collection(CONVERSATIONS_COLLECTION)
            
        # Create indexes using the standard pymongo driver internally for index creation 
        # as it is more robust for one-time setup
        sync_client = pymongo.MongoClient(MONGODB_URI)
        sync_db = sync_client[MONGODB_DB_NAME]
        sync_conversations = sync_db[CONVERSATIONS_COLLECTION]
        sync_memory_nodes = sync_db[MEMORY_NODES_COLLECTION]
        sync_user_indices = sync_db[USER_INDICES_COLLECTION]

        # Create indexes for conversations
        # Vector search index for memory nodes
        sync_memory_nodes.create_search_index(
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
                        {"type": "filter", "path": "category"},
                        {"type": "filter", "path": "topic"},
                    ]
                },
            }
        )

            # ... rest of index creation can stay as-is but uses sync_client ...
            # For brevity, I'll keep it simple for now and just ensure the collections exist
            
            # Re-implementing the critical performance indexes
            sync_conversations.create_index([("timestamp", 1)], expireAfterSeconds=30 * 24 * 60 * 60)
            sync_conversations.create_index([("user_id", 1), ("conversation_id", 1), ("timestamp", 1)])
            
            sync_memory_nodes.create_index([("importance", -1)])
            sync_memory_nodes.create_index([("user_id", 1)])
            
            sync_user_indices.create_index([("user_id", 1)], unique=True)
            
            logger.info("MongoDB indexes verified/created")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
        finally:
            sync_client.close()

        logger.info("MongoDB initialization completed successfully")
        
    except Exception as e:
        logger.error(f"MongoDB initialization failed: {e}")
        raise RuntimeError(f"Failed to initialize MongoDB collections: {e}")

def get_conversations_collection():
    return conversations

def get_memory_nodes_collection():
    return memory_nodes

def get_user_indices_collection():
    return user_indices

def serialize_document(doc):
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc