import numpy as np
from typing import List

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    Returns 0.0 if either vector is zero vector to avoid division by zero.
    """
    if not a or not b:
        return 0.0
    
    a_array = np.array(a, dtype=np.float64)
    b_array = np.array(b, dtype=np.float64)
    
    # Calculate norms
    norm_a = np.linalg.norm(a_array)
    norm_b = np.linalg.norm(b_array)
    
    # Check for zero vectors to avoid division by zero
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    
    # Calculate dot product and return cosine similarity
    dot_product = np.dot(a_array, b_array)
    return dot_product / (norm_a * norm_b)