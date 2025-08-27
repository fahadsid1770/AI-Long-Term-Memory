import json
import boto3
import asyncio
from botocore.exceptions import ClientError
from config import AWS_REGION, EMBEDDING_MODEL_ID, LLM_MODEL_ID
from utils.logger import logger

bedrock_client = boto3.client("bedrock-runtime", region_name= AWS_REGION)

def generate_emnbedding(text: str):
    if not text.strip():
        raise ValueError("Input text cannot be empty")
    try:
        max_tokens = 8000  #embedding model input token limit
        tokens = text.split() #splitting by space, converts into list
        text= " ".join(tokens[:max_tokens]) # keeping only the allowed tokens
        payload = {"inputText": text}
        response = bedrock_client.invoke_model(
            modelId = EMBEDDING_MODEL_ID, body=json.dumps(payload)
        )
        result = json.loads(response["body"].read())
        return result["embedding"]
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise

async def send_to_bedrock(promt):
    payload = [
        {
            "role":"user",
            "content": [{"text": promt}]
        }
    ]
    model_id = LLM_MODEL_ID
    try:
        response=
    except ClientError as e:
        