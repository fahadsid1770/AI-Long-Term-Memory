import time
import asyncio
from services.embedding_service import generate_embedding

def benchmark_single_embedding(text: str, iterations: int = 100):
    """Benchmark single embedding generation"""
    times = []
    for _ in range(iterations):
        start = time.time()
        embedding = generate_embedding(text)
        end = time.time()
        times.append(end - start)
    avg_time = sum(times) / len(times)
    print(f"Single embedding ({len(text)} chars): Avg {avg_time:.4f}s over {iterations} iterations")
    return avg_time

def benchmark_multiple_embeddings(texts: list, iterations: int = 10):
    """Benchmark multiple embeddings sequentially"""
    times = []
    for _ in range(iterations):
        start = time.time()
        embeddings = [generate_embedding(text) for text in texts]
        end = time.time()
        times.append(end - start)
    avg_time = sum(times) / len(times)
    print(f"Multiple embeddings ({len(texts)} texts): Avg {avg_time:.4f}s over {iterations} iterations")
    return avg_time

if __name__ == "__main__":
    # Test texts of different lengths
    short_text = "Hello world"
    medium_text = "This is a medium length text for testing embedding performance."
    long_text = "This is a much longer text that contains more words and should take longer to process when generating embeddings. It includes various topics and details to make it more realistic for benchmarking purposes."

    print("Benchmarking current embedding performance...")
    print("=" * 50)

    # Benchmark single embeddings
    benchmark_single_embedding(short_text)
    benchmark_single_embedding(medium_text)
    benchmark_single_embedding(long_text)

    # Benchmark multiple embeddings
    texts = [short_text, medium_text, long_text] * 5  # 15 texts
    benchmark_multiple_embeddings(texts)