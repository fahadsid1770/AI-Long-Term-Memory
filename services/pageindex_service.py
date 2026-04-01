import json
import os
from typing import List, Dict, Optional
from database.mongodb import get_user_indices_collection
from services.embedding_service import get_chat_response
from utils.logger import logger

def get_indices_collection():
    """Get the master index collection"""
    return get_user_indices_collection()

async def get_user_master_index(user_id: str) -> Dict:
    """Retrieve the hierarchical map (Table of Contents) for a user"""
    try:
        collection = get_indices_collection()
        index = collection.find_one({"user_id": user_id})
        if not index:
            # Initialize empty index if not exists
            return {"user_id": user_id, "categories": {}}
        return index
    except Exception as e:
        logger.error(f"Error getting master index for user {user_id}: {e}")
        return {"user_id": user_id, "categories": {}}

def sanitize_mongodb_key(key: str) -> str:
    """Sanitize keys for MongoDB to prevent injection or invalid character errors"""
    if not key:
        return "General"
    # MongoDB keys cannot contain '.' or start with '$'
    # We also remove other potentially problematic characters
    sanitized = key.replace(".", "_").replace("$", "_").strip()
    return sanitized if sanitized else "General"

async def update_user_master_index(user_id: str, category: str, topic: str):
    """Update the master index when a new category or topic is used"""
    try:
        # Sanitize keys for MongoDB safety
        safe_category = sanitize_mongodb_key(category)
        safe_topic = topic.strip() if topic else "Uncategorized"
        
        collection = get_indices_collection()
        # Using dot notation to update specific fields in the categories map
        update_query = {
            "$addToSet": {
                f"categories.{safe_category}": safe_topic
            }
        }
        await collection.update_one({"user_id": user_id}, update_query, upsert=True)
        logger.info(f"Updated Master Index for user {user_id}: {safe_category} -> {safe_topic}")
    except Exception as e:
        logger.error(f"Error updating master index for user {user_id}: {e}")

def extract_json_from_llm(text: str) -> Optional[Dict]:
    """Robustly extract JSON from potentially messy LLM output"""
    if not text:
        return None
    
    # Try to find JSON block
    import re
    json_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
            
    # Try direct parsing
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None

async def categorize_content(user_id: str, content: str) -> Dict[str, str]:
    """Use LLM to categorize content based on the user's existing map"""
    try:
        # Get existing map to provide context to LLM
        master_index = await get_user_master_index(user_id)
        categories_context = json.dumps(master_index.get("categories", {}), indent=2)

        prompt = (
            f"You are a master archivist. File this text into a hierarchical system.\n\n"
            f"MAP:\n{categories_context}\n\n"
            f"TEXT:\n{content}\n\n"
            f"Respond ONLY with JSON: {{\"category\": \"string\", \"topic\": \"string\"}}"
        )

        response_text = await get_chat_response(prompt)
        result = extract_json_from_llm(response_text)
        
        if result:
            return {
                "category": result.get("category", "General"),
                "topic": result.get("topic", "Uncategorized")
            }
        return {"category": "General", "topic": "Uncategorized"}

    except Exception as e:
        logger.error(f"Error in categorize_content: {e}")
        return {"category": "General", "topic": "Uncategorized"}

async def agentic_router(user_id: str, query: str) -> Optional[Dict[str, str]]:
    """Determine which specific category/topic the query should search in"""
    try:
        master_index = await get_user_master_index(user_id)
        categories = master_index.get("categories", {})
        
        if not categories:
            return None

        prompt = (
            f"You are a search router. Given the following memory index map and a user query, "
            f"decide which specific Category and Topic (if any) are most relevant to search.\n\n"
            f"MEMORY INDEX MAP:\n{json.dumps(categories, indent=2)}\n\n"
            f"USER QUERY: {query}\n\n"
            f"INSTRUCTIONS:\n"
            f"- If the query is broad or doesn't match any category, respond with 'NONE'.\n"
            f"- If it matches, respond ONLY with a JSON object like: {{\"category\": \"string\", \"topic\": \"string\"}}\n"
        )

        response_text = await get_chat_response(prompt)
        
        if "NONE" in response_text.upper() or not response_text.strip():
            return None

        return extract_json_from_llm(response_text)

    except Exception as e:
        logger.error(f"Error in agentic_router: {e}")
        return None
