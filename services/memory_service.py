import datetime
from bson.objectid import ObjectId
import pymongo
from configuration.config import MAX_DEPTH, SIMILARITY_THRESHOLD, REINFORCEMENT_FACTOR, DECAY_FACTOR
from database.mongodb import get_memory_nodes_collection
from services.embedding_service import generate_embedding, get_chat_response
from services.pageindex_service import categorize_content, update_user_master_index
from utils.helpers import cosine_similarity
from typing import List, Dict, Optional
from configuration.config import MEMORY_NODES_VECTOR_SEARCH_INDEX_NAME
from utils.logger import logger

def get_memory_collection():
    """Get initialized memory nodes collection"""
    return get_memory_nodes_collection()

async def find_similar_memories(
    user_id: str, embedding: List[float], top_n: int = 3, filter_dict: Optional[Dict] = None
) -> List[Dict]:
    """
    Find most similar memory nodes from the memory tree using vector search.
    """
    try:
        collection = get_memory_collection()
        
        search_filter = {"user_id": user_id}
        if filter_dict:
            search_filter.update(filter_dict)
            
        pipeline = [
            {
                "$vectorSearch": {
                    "index": MEMORY_NODES_VECTOR_SEARCH_INDEX_NAME,
                    "path": "embeddings",
                    "queryVector": embedding,
                    "numCandidates": 100,
                    "limit": top_n,
                    "filter": search_filter,
                }
            },
            {"$addFields": {"similarity": {"$meta": "vectorSearchScore"}}},
            {
                "$project": {
                    "_id": 1,
                    "content": 1,
                    "summary": 1,
                    "importance": 1,
                    "effective_importance": {
                        "$multiply": [
                            "$importance",
                            {"$add": [1, {"$ln": {"$add": ["$access_count", 1]}}]},
                        ]
                    },
                    "similarity": 1,
                    "access_count": 1,
                    "timestamp": 1,
                    "embeddings": 1,
                }
            },
        ]

        cursor = collection.aggregate(pipeline)
        results = []
        async for doc in cursor:
            doc_id = str(doc.pop("_id"))
            doc["id"] = doc_id
            results.append(doc)

        return results
    except Exception as e:
        logger.error(f"Error finding similar memory nodes: {str(e)}")
        raise

async def update_importance_batch(user_id, embedding):
    """Update importance of memories using cursor iteration to prevent OOM"""
    try:
        collection = get_memory_collection()
        
        # Use cursor instead of list(find()) to prevent memory exhaustion
        cursor = collection.find(
            {"user_id": user_id},
            {"_id": 1, "embeddings": 1, "importance": 1, "access_count": 1}
        )
        
        bulk_operations = []
        async for doc in cursor:
            doc_id = doc["_id"]
            memory_embedding = doc["embeddings"]
            
            similarity = cosine_similarity(embedding, memory_embedding)
            
            if similarity > SIMILARITY_THRESHOLD:
                new_importance = min(doc["importance"] * REINFORCEMENT_FACTOR, 1.0)
                new_access_count = doc["access_count"] + 1
            else:
                new_importance = max(doc["importance"] * DECAY_FACTOR, 0.1)
                new_access_count = doc["access_count"]
            
            bulk_operations.append(
                pymongo.UpdateOne(
                    {"_id": doc_id},
                    {
                        "$set": {
                            "importance": new_importance,
                            "access_count": new_access_count,
                            "last_accessed": datetime.datetime.now(datetime.timezone.utc)
                        }
                    }
                )
            )
            
            # Execute in chunks to keep memory usage low
            if len(bulk_operations) >= 100:
                await collection.bulk_write(bulk_operations, ordered=False)
                bulk_operations = []
        
        if bulk_operations:
            await collection.bulk_write(bulk_operations, ordered=False)
            
    except Exception as e:
        logger.error(f"Error in batch importance update: {str(e)}")
        raise

async def prune_memories(user_id):
    """Prune memories asynchronously"""
    collection = get_memory_collection()
    count = await collection.count_documents({"user_id": user_id})
    if count > MAX_DEPTH:
        cursor = collection.find({"user_id": user_id}).sort("importance", pymongo.ASCENDING).limit(count - MAX_DEPTH)
        ids_to_delete = [doc["_id"] async for doc in cursor]
        if ids_to_delete:
            await collection.delete_many({"_id": {"$in": ids_to_delete}})

async def remember_content(request):
    """Stored new memory asynchronously"""
    try:
        if not request.content.strip():
            return {"message": "Cannot remember empty content"}
            
        embeddings = await generate_embedding(request.content)
        similar_memories = await find_similar_memories(request.user_id, embeddings)
        
        collection = get_memory_collection()
        
        for memory in similar_memories:
            if memory["similarity"] > 0.85:
                await collection.update_one(
                    {"_id": ObjectId(memory["id"])},
                    {
                        "$set": {
                            "importance": min(memory["importance"] * REINFORCEMENT_FACTOR, 1.0),
                            "access_count": memory["access_count"] + 1,
                            "last_accessed": datetime.datetime.now(datetime.timezone.utc),
                        }
                    },
                )
                return {"message": "Reinforced existing memory", "memory_id": memory["id"]}

        # Assessment and summary
        importance_rating_text = await get_chat_response(f"Rate 1-10 importance: {request.content}")
        try:
            importance_rating = float("".join(c for c in importance_rating_text if c.isdigit() or c == "."))
            importance_score = min(max(importance_rating / 10, 0.1), 1.0)
        except ValueError:
            importance_score = 0.5
            
        summary = await get_chat_response(f"One-sentence summary: {request.content}")

        categorization = await categorize_content(request.user_id, request.content)
        category = categorization.get("category", "General")
        topic = categorization.get("topic", "Uncategorized")

        new_memory = {
            "user_id": request.user_id,
            "content": request.content,
            "summary": summary,
            "category": category,
            "topic": topic,
            "index_path": f"/{category}/{topic}",
            "importance": importance_score,
            "access_count": 0,
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "last_accessed": datetime.datetime.now(datetime.timezone.utc),
            "embeddings": embeddings,
        }
        
        result = await collection.insert_one(new_memory)
        memory_id = str(result.inserted_id)

        await update_user_master_index(request.user_id, category, topic)
        
        # Merge logic
        for memory in similar_memories:
            if memory["id"] != memory_id and 0.7 < memory["similarity"] < 0.85:
                # Combine content using AI
                combined_content = await get_chat_response(f"Combine: {new_memory['content']} AND {memory['content']}")
                
                # Check for vector dimension mismatch before averaging
                if len(embeddings) != len(memory["embeddings"]):
                    logger.error(f"Vector dimension mismatch during merge: {len(embeddings)} vs {len(memory['embeddings'])}")
                    # Use the new embedding as a safer fallback
                    updated_embeddings = embeddings
                else:
                    # Average embeddings safely
                    updated_embeddings = [(a + b) / 2 for a, b in zip(embeddings, memory["embeddings"])]
                
                updated_importance = min(max(new_memory["importance"], memory["importance"]) * 1.1, 1.0)
                new_summary = await get_chat_response(f"Summary: {combined_content}")
                
                await collection.update_one(
                    {"_id": ObjectId(memory_id)},
                    {
                        "$set": {
                            "content": combined_content,
                            "summary": new_summary,
                            "importance": updated_importance,
                            "embeddings": updated_embeddings,
                        }
                    },
                )
                await collection.delete_one({"_id": ObjectId(memory["id"])})
                break
                
        await update_importance_batch(request.user_id, embeddings)
        await prune_memories(request.user_id)
        return {"message": f"Remembered: {summary}", "memory_id": memory_id}
    except Exception as error:
        logger.error(f"Error remembering content: {error}")
        raise
