import json
import pymongo
from bson.objectid import ObjectId
from bson import json_util
from database.mongodb import conversations
from database.models import Message
from services.embedding_service import generate_embedding, get_chat_response
from models.pydantic_models import RememberRequest
from services.memory_service import remember_content
from utils.logger import logger
import configuration.config as config

def get_conversations_collection():
    """Get conversations collection with validation"""
    if conversations is None:
        raise RuntimeError("Conversations collection not initialized")
    return conversations

def optimized_hybrid_search(query, vector_query, user_id, weight=0.8, top_n=5):
    """Optimized hybrid search with better performance and caching considerations"""
    try:
        collection = get_conversations_collection()
        
        # Simplified pipeline with better performance
        pipeline = [
            {
                "$search": {
                    "index": "conversations_compound_search_index",  # Needs to be created
                    "compound": {
                        "should": [
                            {
                                "text": {
                                    "query": query,
                                    "path": "text"
                                }
                            },
                            {
                                "knnBeta": {
                                    "vector": vector_query,
                                    "path": "embeddings",
                                    "k": top_n * 2  # Get more candidates for better results
                                }
                            }
                        ]
                    },
                    "filter": {"user_id": user_id}
                }
            },
            {
                "$addFields": {
                    "score": {"$meta": "searchScore"},
                    "search_highlights": {"$meta": "searchHighlights"}
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
        
        results = list(collection.aggregate(pipeline))
        logger.debug(f"Hybrid search returned {len(results)} results for user {user_id}")
        return results
        
    except Exception as e:
        logger.error(f"Error in optimized hybrid search: {e}")
        # Fallback to simpler vector search if compound search fails
        return fallback_vector_search(vector_query, user_id, top_n)

def fallback_vector_search(vector_query, user_id, top_n=5):
    """Fallback vector search if compound search is not available"""
    try:
        collection = get_conversations_collection()
        
        pipeline = [
            {
                "$vectorSearch": {
                    "index": config.CONVERSATIONS_VECTOR_SEARCH_INDEX_NAME,
                    "queryVector": vector_query,
                    "path": "embeddings",
                    "numCandidates": min(top_n * 10, 100),  # Optimized candidates
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
        
        results = list(collection.aggregate(pipeline))
        logger.info(f"Fallback vector search returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Error in fallback vector search: {e}")
        raise

# Keep original function for backwards compatibility
def hybrid_search(query, vector_query, user_id, weight=0.8, top_n=5):
    """Original hybrid search - now calls optimized version"""
    return optimized_hybrid_search(query, vector_query, user_id, weight, top_n)

async def add_conversation_message(message_input):
    try:
        collection = get_conversations_collection()
        new_message = await Message.create(message_input)
        result = collection.insert_one(new_message.to_dict())
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
                logger.error(f"Error creating memory: {str(memory_error)}")
                raise
        return {"message": "Message added successfully"}
    except Exception as error:
        logger.error(str(error))
        raise

async def search_memory(user_id, query):
    try:
        vector_query = await generate_embedding(query)
        documents = hybrid_search(query, vector_query, user_id, weight=0.8, top_n=5)
        relevant_results = [doc for doc in documents if doc["score"] >= 0.70]
        if not relevant_results:
            return {"documents": "No documents found"}
        else:
            return {"documents": [serialize_document(doc) for doc in relevant_results]}
    except Exception as error:
        logger.error(str(error))
        raise

async def get_conversation_context(_id):
    try:
        collection = get_conversations_collection()
        conversation_record = collection.find_one(
            {"_id": ObjectId(_id)},
            projection={
                "_id": 0,
                "embeddings": 0,
            },
        )
        if not conversation_record:
            return {"documents": "No documents found"}
        # Extract metadata
        user_id = conversation_record["user_id"]
        conversation_id = conversation_record["conversation_id"]
        timestamp = conversation_record["timestamp"]
        message_type = conversation_record["type"]
        if message_type == "ai":
            # Get more preceding context for AI messages
            prev_limit = 4
            next_limit = 2
        else:
            # Balance for human messages
            prev_limit = 3
            next_limit = 3
        # Get messages before target
        prev_cursor = (
            collection.find(
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "timestamp": {"$lte": timestamp},
                },
                projection={
                    "_id": 0,
                    "embeddings": 0,
                },
            )
            .sort("timestamp", pymongo.DESCENDING)
            .limit(prev_limit)
        )
        context = list(prev_cursor)
        # Get messages after target
        next_cursor = (
            collection.find(
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "timestamp": {"$gt": timestamp},
                },
                projection={
                    "_id": 0,
                    "embeddings": 0,
                },
            )
            .sort("timestamp", pymongo.ASCENDING)
            .limit(next_limit)
        )
        context_after = list(next_cursor)
        # Combine and sort all messages by timestamp
        conversation_with_context = sorted(
            context + context_after,
            key=lambda x: x["timestamp"],
        )
        return {"documents": conversation_with_context}
    except Exception as error:
        logger.error(str(error))
        raise

async def generate_conversation_summary(documents):
    try:
        prompt = (
            f"You are an advanced AI assistant skilled in analyzing and summarizing conversation histories while preserving all essential details.\n"
            f"Given the following conversation data in JSON format, generate a detailed and structured summary that captures all key points, topics discussed, decisions made, and relevant insights.\n\n"
            f"Ensure your summary follows these guidelines:\n"
            f"- **Maintain Clarity & Accuracy:** Include all significant details, technical discussions, and conclusions.\n"
            f"- **Preserve Context & Meaning:** Avoid omitting important points that could alter the conversation's intent.\n"
            f"- **Organized Structure:** Present the summary in a logical flow or chronological order.\n"
            f"- **Key Highlights:** Explicitly state major questions asked, AI responses, decisions made, and follow-up discussions.\n"
            f"- **Avoid Redundancy:** Summarize effectively without unnecessary repetition.\n\n"
            f"### Output Format:\n"
            f"- **Topic:** Briefly describe the conversation's purpose.\n"
            f"- **Key Discussion Points:** Outline the main topics covered.\n"
            f"- **Decisions & Takeaways:** Highlight key conclusions or next steps.\n"
            f"- **Unresolved Questions (if any):** Mention pending queries or areas needing further clarification.\n\n"
            f"Provide a **clear, structured, and comprehensive** summary ensuring no critical detail is overlooked.\n\n"
            f"Input JSON: {json.dumps(documents, default=json_util.default)}"
        )
        summary = await get_chat_response(prompt)
        return {"summary": summary}
    except Exception as error:
        logger.error(str(error))
        raise

def serialize_document(doc):
    doc["_id"] = str(doc["_id"])
    return doc
