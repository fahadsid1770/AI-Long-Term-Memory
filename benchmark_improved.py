import time
import asyncio
from services.embedding_service import generate_embedding, generate_embeddings_batch

async def benchmark_async_single_embedding(text: str, iterations: int = 100):
    """Benchmark async single embedding generation"""
    times = []
    for _ in range(iterations):
        start = time.time()
        embedding = await generate_embedding(text)
        end = time.time()
        times.append(end - start)
    avg_time = sum(times) / len(times)
    print(f"Async single embedding ({len(text)} chars): Avg {avg_time:.4f}s over {iterations} iterations")
    return avg_time

async def benchmark_async_multiple_embeddings(texts: list, iterations: int = 10):
    """Benchmark async multiple embeddings sequentially"""
    times = []
    for _ in range(iterations):
        start = time.time()
        embeddings = [await generate_embedding(text) for text in texts]
        end = time.time()
        times.append(end - start)
    avg_time = sum(times) / len(times)
    print(f"Async multiple embeddings sequential ({len(texts)} texts): Avg {avg_time:.4f}s over {iterations} iterations")
    return avg_time

async def benchmark_batch_embeddings(texts: list, iterations: int = 10):
    """Benchmark batch embedding generation"""
    times = []
    for _ in range(iterations):
        start = time.time()
        embeddings = await generate_embeddings_batch(texts)
        end = time.time()
        times.append(end - start)
    avg_time = sum(times) / len(times)
    print(f"Batch embeddings ({len(texts)} texts): Avg {avg_time:.4f}s over {iterations} iterations")
    return avg_time

async def benchmark_cache_performance():
    """Benchmark cache performance by repeating the same text"""
    test_text = "This is a test text for caching performance."

    # First call (cache miss)
    start = time.time()
    emb1 = await generate_embedding(test_text)
    first_call = time.time() - start

    # Second call (cache hit)
    start = time.time()
    emb2 = await generate_embedding(test_text)
    second_call = time.time() - start

    print(f"Cache performance - First call: {first_call:.4f}s, Second call: {second_call:.4f}s")
    print(f"Cache speedup: {first_call/second_call:.1f}x faster")
    return first_call, second_call

async def main():
    # Test texts of different lengths
    short_text = "Hello world"
    medium_text = "This is a medium length text for testing embedding performance."
    long_text = "This is a much longer text that contains more words and should take longer to process when generating embeddings. It includes various topics and details to make it more realistic for benchmarking purposes."

    print("Benchmarking improved embedding performance...")
    print("=" * 60)

    # Benchmark single embeddings
    await benchmark_async_single_embedding(short_text)
    await benchmark_async_single_embedding(medium_text)
    await benchmark_async_single_embedding(long_text)

    # Benchmark multiple embeddings
    texts = [short_text, medium_text, long_text] * 5  # 15 texts
    await benchmark_async_multiple_embeddings(texts)
    await benchmark_batch_embeddings(texts)

    # Benchmark cache performance
    await benchmark_cache_performance()

if __name__ == "__main__":
    asyncio.run(main())