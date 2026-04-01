import json
import pymongo
from bson.objectid import ObjectId
from bson import json_util
from bson.errors import InvalidId
from fastapi import HTTPException, status
from database.mongodb import get_conversations_collection
from database.models import Message
from services.embedding_service import generate_embedding, get_chat_response
from models.pydantic_models import RememberRequest
from services.memory_service import remember_content
from utils.logger import logger
import configuration.config as config

async def optimized_hybrid_search(query, vector_query, user_id, weight=0.8, top_n=5):
    """Optimized hybrid search with better performance and weight-based boosting"""
    try:
        collection = get_conversations_collection()
        
        # Calculate boosts based on weight
        vector_boost = weight * 10.0
        text_boost = (1.0 - weight) * 2.0
        
        pipeline = [
            {
                "$search": {
                    "index": config.CONVERSATIONS_COMPOUND_SEARCH_INDEX_NAME,
                    "compound": {
                        "should": [
                            {
                                "text": {
                                    "query": query,
                                    "path": "text",
                                    "score": {"boost": {"value": text_boost}}
                                }
                            },
                            {
                                "vector": {
                                    "vector": vector_query,
                                    "path": "embeddings",
                                    "numCandidates": top_n * 10,
                                    "score": {"boost": {"value": vector_boost}}
                                }
                            }
                        ],
                        "filter": [
                            {
                                "text": {
                                    "query": user_id,
                                    "path": "user_id"
                                }
                            }
                        ]
                    }
                }
            },
            {
                "$addFields": {
                    "score": {"$meta": "searchScore"}
                }
            },
            {"$limit": top_n},
            {
                "$project": {
                    "_id": 1,
                    "text": 1,
                    "type": 1,
                    "timestamp": 1,
                    "conversation_id": 1,
                    "user_id": 1,
                    "score": 1
                }
            }
        ]
        
        # Use motor (async) aggregate
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=top_n)
        logger.debug(f"Hybrid search returned {len(results)} results for user {user_id}")
        return results
        
    except Exception as e:
        logger.error(f"Error in optimized hybrid search: {e}")
        return await fallback_vector_search(vector_query, user_id, top_n)

async def fallback_vector_search(vector_query, user_id, top_n=5):
    """Fallback vector search if compound search is not available"""
    try:
        collection = get_conversations_collection()
        
        pipeline = [
            {
                "$vectorSearch": {
                    "index": config.CONVERSATIONS_VECTOR_SEARCH_INDEX_NAME,
                    "queryVector": vector_query,
                    "path": "embeddings",
                    "numCandidates": min(top_n * 10, 100),
                    "limit": top_n,
                    "filter": {"user_id": user_id}
                }
            },
            {
                "$addFields": {
                    "score": {"$meta": "vectorSearchScore"}
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "text": 1,
                    "type": 1,
                    "timestamp": 1,
                    "conversation_id": 1,
                    "user_id": 1,
                    "score": 1
                }
            }
        ]
        
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=top_n)
        logger.info(f"Fallback vector search returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Error in fallback vector search: {e}")
        raise

async def add_conversation_message(message_input):
    try:
        collection = get_conversations_collection()
        new_message = await Message.create(message_input)
        result = await collection.insert_one(new_message.to_dict())
        logger.debug(f"Inserted message with ID: {result.inserted_id}")
        if message_input.type == "human" and len(message_input.text) > 30:
            try:
                memory_content = (
                    f"From conversation {message_input.conversation_id}: {message_input.text}"
                )
                logger.info(f"Creating memory for user {message_input.user_id}: {memory_content}")
                await remember_content(
                    RememberRequest(user_id=message_input.user_id, content=memory_content)
                )
            except Exception as memory_error:
                logger.error(f"Failed to create memory for message: {str(memory_error)}")
        return {"message": "Message added successfully"}
    except Exception as error:
        logger.error(str(error))
        raise

async def search_memory(user_id, query):
    try:
        vector_query = await generate_embedding(query)
        documents = await optimized_hybrid_search(query, vector_query, user_id, weight=0.8, top_n=5)
        relevant_results = [doc for doc in documents if doc.get("score", 0) >= config.SIMILARITY_THRESHOLD]
        if not relevant_results:
            return {"documents": []}
        else:
            return {"documents": [serialize_document(doc) for doc in relevant_results]}
    except Exception as error:
        logger.error(str(error))
        raise

async def get_conversation_context(_id):
    try:
        # Validate ObjectId
        try:
            object_id = ObjectId(_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid conversation record ID format: {_id}"
            )

        collection = get_conversations_collection()
        conversation_record = await collection.find_one(
            {"_id": object_id},
            projection={
                "_id": 0,
                "embeddings": 0,
            },
        )
        if not conversation_record:
            return {"documents": "No documents found"}
            
        user_id = conversation_record["user_id"]
        conversation_id = conversation_record["conversation_id"]
        timestamp = conversation_record["timestamp"]
        message_type = conversation_record["type"]
        
        if message_type == "ai":
            prev_limit = 4
            next_limit = 2
        else:
            prev_limit = 3
            next_limit = 3

        # Get messages before
        prev_cursor = collection.find(
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "timestamp": {"$lte": timestamp},
            },
            projection={"_id": 0, "embeddings": 0}
        ).sort([("timestamp", pymongo.DESCENDING), ("_id", pymongo.DESCENDING)]).limit(prev_limit)
        
        context = await prev_cursor.to_list(length=prev_limit)
        
        # Get messages after
        next_cursor = collection.find(
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "timestamp": {"$gt": timestamp},
            },
            projection={"_id": 0, "embeddings": 0}
        ).sort([("timestamp", pymongo.ASCENDING), ("_id", pymongo.ASCENDING)]).limit(next_limit)
        
        context_after = await next_cursor.to_list(length=next_limit)
        
        conversation_with_context = sorted(
            context + context_after,
            key=lambda x: x["timestamp"],
        )
        return {"documents": conversation_with_context}
    except HTTPException:
        raise
    except Exception as error:
        logger.error(str(error))
        raise

async def generate_conversation_summary(documents):
    try:
        prompt = (
            f"Summarize this conversation details:\n\n"
            f"Input JSON: {json.dumps(documents, default=json_util.default)}"
        )
        summary = await get_chat_response(prompt)
        return {"summary": summary}
    except Exception as error:
        logger.error(str(error))
        raise

def serialize_document(doc):
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc
