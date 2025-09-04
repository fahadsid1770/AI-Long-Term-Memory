import pymongo
import pymongo.errors
from configuration.config import (
    MONGODB_URI, MONGODB_DB_NAME, CONVERSATIONS_COLLECTION, MEMORY_NODES_COLLECTION,
    CONVERSATIONS_VECTOR_SEARCH_INDEX_NAME, CONVERSATIONS_FULLTEXT_SEARCH_INDEX_NAME,
    MEMORY_NODES_VECTOR_SEARCH_INDEX_NAME
)

from utils.logger import logger

# connecting to mongodb
client = pymongo.MongoClient(MONGODB_URI)
db = client[MONGODB_DB_NAME]
conversations = db[CONVERSATIONS_COLLECTION]
memory_nodes = db[MEMORY_NODES_COLLECTION]

def initialize_mongodb():
    if CONVERSATIONS_COLLECTION not in db.list_collection_names():
        db.create_collection(CONVERSATIONS_COLLECTION)
        try:
            conversations.create_search_index(
                {
                    "name": CONVERSATIONS_VECTOR_SEARCH_INDEX_NAME ,
                    "type": "vectorSearch",
                    "definition": {
                        "fields": [
                            {
                                "type": "vector",
                                "path": "embeddings",
                                "numDimensions": 1024,
                                "similarity": "cosine",
                            },
                            {"type": "filter", "path": "user_id"}
                        ]
                    }
                }
            )
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
            conversations.create_index(
                [("timestamp",1)],
                expireAfterSeconds = 30 * 24 * 60 * 60,  # 30 days
                name = "timestamp_ttl_index"
            )

        except pymongo.errors.PyMongoError as e:
            logger.error(f"Error creating indexes: {e}")

    # memory nodes
    if MEMORY_NODES_COLLECTION not in db.list_collection_names():
        db.create_collection(MEMORY_NODES_COLLECTION)
        try:
            memory_nodes.create_index(
                [("importance", pymongo.DESCENDING)], name="importance_index"
            )
            memory_nodes.create_index(
                [("user_id", pymongo.ASCENDING)], name="user_id_index"
            )
            memory_nodes.create_search_index(
                {
                    "name": MEMORY_NODES_VECTOR_SEARCH_INDEX_NAME,
                    "type": "vectorSearch",
                    "definition": {
                        "fields": [
                            {
                                "type": "vector",
                                "path": "embeddings",
                                "numDimensions": 1536,
                                "similarity": "cosine",
                            },
                            {"type": "filter", "path": "user_id"},
                        ]
                    },
                }
            )
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Error creating memory_nodes indexes: {e}")

def serialize_document(doc):
    doc["_id"] = str(doc["_id"])
    return doc