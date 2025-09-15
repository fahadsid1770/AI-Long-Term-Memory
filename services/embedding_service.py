import json
import asyncio
import hashlib
import httpx
from fastapi import HTTPException
from dotenv import load_dotenv
load_dotenv()
import requests
import os
from sentence_transformers import SentenceTransformer
from utils.logger import logger

# Initialize the Sentence-Transformers model once for efficiency.
# Allow configuration of the model via environment variable
MODEL_NAME = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')

try:
    embedding_model = SentenceTransformer(MODEL_NAME)
    logger.info(f"Sentence-Transformers model '{MODEL_NAME}' loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load Sentence-Transformers model '{MODEL_NAME}': {e}")
    # Fallback to default model
    try:
        MODEL_NAME = 'all-MiniLM-L6-v2'
        embedding_model = SentenceTransformer(MODEL_NAME)
        logger.info(f"Fallback: Sentence-Transformers model '{MODEL_NAME}' loaded successfully.")
    except Exception as fallback_e:
        logger.error(f"Failed to load fallback model: {fallback_e}")
        embedding_model = None

# Simple LRU cache for embeddings
EMBEDDING_CACHE = {}
CACHE_MAX_SIZE = 1000  # Maximum number of cached embeddings

def _get_cache_key(text: str) -> str:
    """Generate a cache key for the text"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def _manage_cache_size():
    """Ensure cache doesn't exceed maximum size by removing oldest entries"""
    if len(EMBEDDING_CACHE) > CACHE_MAX_SIZE:
        # Remove oldest 10% of entries (simple LRU approximation)
        items_to_remove = len(EMBEDDING_CACHE) - CACHE_MAX_SIZE + int(CACHE_MAX_SIZE * 0.1)
        keys_to_remove = list(EMBEDDING_CACHE.keys())[:items_to_remove]
        for key in keys_to_remove:
            del EMBEDDING_CACHE[key]
        logger.info(f"Cache size managed: removed {items_to_remove} entries")


async def generate_embedding(text: str):
    """
    Generates an embedding for the given text using the local all-MiniLM-L6-v2 model.
    Uses caching to avoid recomputation for repeated texts.
    """
    if not embedding_model:
        raise RuntimeError("Sentence-Transformers model is not available.")

    if not text.strip():
        raise ValueError("Input text cannot be empty")

    # Check cache first
    cache_key = _get_cache_key(text)
    if cache_key in EMBEDDING_CACHE:
        logger.debug("Embedding cache hit")
        return EMBEDDING_CACHE[cache_key]

    try:
        # Run the synchronous embedding generation in a thread pool to avoid blocking
        embedding = await asyncio.to_thread(embedding_model.encode, text)
        # Convert the numpy array to a standard Python list.
        embedding_list = embedding.tolist()

        # Cache the result
        EMBEDDING_CACHE[cache_key] = embedding_list
        _manage_cache_size()

        return embedding_list
    except Exception as e:
        logger.error(f"Failed to generate Sentence-Transformers embedding: {e}")
        raise

async def generate_embeddings_batch(texts: list):
    """
    Generates embeddings for multiple texts in batch using the local all-MiniLM-L6-v2 model.
    Uses caching to avoid recomputation for repeated texts.
    This is more efficient than calling generate_embedding multiple times.
    """
    if not embedding_model:
        raise RuntimeError("Sentence-Transformers model is not available.")

    if not texts or not all(text.strip() for text in texts):
        raise ValueError("Input texts cannot be empty")

    # Check cache for each text
    cached_embeddings = []
    uncached_texts = []
    uncached_indices = []

    for i, text in enumerate(texts):
        cache_key = _get_cache_key(text)
        if cache_key in EMBEDDING_CACHE:
            cached_embeddings.append((i, EMBEDDING_CACHE[cache_key]))
        else:
            uncached_texts.append(text)
            uncached_indices.append(i)

    # If all texts are cached, return them directly
    if not uncached_texts:
        return [emb for _, emb in sorted(cached_embeddings, key=lambda x: x[0])]

    try:
        # Generate embeddings for uncached texts in batch
        new_embeddings = await asyncio.to_thread(embedding_model.encode, uncached_texts)
        new_embeddings_list = new_embeddings.tolist()

        # Cache the new embeddings
        for text, embedding in zip(uncached_texts, new_embeddings_list):
            cache_key = _get_cache_key(text)
            EMBEDDING_CACHE[cache_key] = embedding
        _manage_cache_size()

        # Combine cached and new embeddings in original order
        result = [None] * len(texts)
        for i, emb in cached_embeddings:
            result[i] = emb
        for idx, emb in zip(uncached_indices, new_embeddings_list):
            result[idx] = emb

        return result
    except Exception as e:
        logger.error(f"Failed to generate batch Sentence-Transformers embeddings: {e}")
        raise

async def get_chat_response(prompt: str):
    """
    Sends a prompt to OpenRouter to get a chat completion using a free model.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY environment variable not set.")
        raise ValueError("API key for OpenRouter is missing.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "deepseek/deepseek-chat-v3.1:free",
        "messages": [
            {
                "role":"system",
                "content": "Your are a helpful assistant that helps people find information. If you don't know the answer, just say that you don't know, don't try to make up an answer."
            },
            {   "role": "user", 
                "content": prompt
            }
        ],
    }

    response = None  # Initialize response to None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            )
        
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        response_data = response.json()
        choices = response_data.get('choices', [])
        if choices and 'message' in choices[0]:
            return choices[0]['message']['content']
        else:
            raise HTTPException(status_code=500, detail="Invalid response structure from OpenRouter.")
        
    except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Error communicating with LLM provider: {e}")
    except (KeyError, IndexError) as err:
        logger.error(f"Unexpected response format from OpenRouter: {err}")
        if response is not None:
            logger.error(f"Full response: {response.text}")
        raise

