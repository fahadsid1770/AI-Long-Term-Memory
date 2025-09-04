import json
import asyncio
import httpx
from fastapi import HTTPException
from dotenv import load_dotenv
load_dotenv() 
import requests  
import os        
from sentence_transformers import SentenceTransformer
from utils.logger import logger

# Initialize the Sentence-Transformers model once for efficiency.
try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("Sentence-Transformers model 'all-MiniLM-L6-v2' loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load Sentence-Transformers model: {e}")
    embedding_model = None


def generate_embedding(text: str):
    """
    Generates an embedding for the given text using the local all-MiniLM-L6-v2 model.
    """
    if not embedding_model:
        raise RuntimeError("Sentence-Transformers model is not available.")
        
    if not text.strip():
        raise ValueError("Input text cannot be empty")
        
    try:
        # The .encode() method returns a numpy array.
        embedding = embedding_model.encode(text)
        # Convert the numpy array to a standard Python list.
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Failed to generate Sentence-Transformers embedding: {e}")
        raise

async def get_chat_response(prompt: str):
    """
    Sends a prompt to OpenRouter to get a chat completion using a free model.
    """
    api_key = "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"  # os.getenv("OPENROUTER_API_KEY")
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

