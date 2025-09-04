import pymongo
import pymongo.errors
from ..configuration.config import (
    MONGODB_URI, MONGODB_DB_NAME, CONVERSATIONS_COLLECTION, MEMORY_NODES_COLLECTION,
    CONVERSATIONS_VECTOR_SEARCH_INDEX_NAME, CONVERSATIONS_FULLTEXT_SEARCH_INDEX_NAME,
    MEMORY_NODES_VECTOR_SEARCH_INDEX_NAME
)

from utils.logger import logger

# connecting to mongodb
client = pymongo.MongoClient("mongodb+srv://fahadsid1770:asdf1234@cluster0.t7qycpm.mongodb.net/")
db = client[MONGODB_DB_NAME]
conversations = db[CONVERSATIONS_COLLECTION]
memory_nodes = db[MEMORY_NODES_COLLECTION]