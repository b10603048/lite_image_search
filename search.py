"""
Lite Image Search — Similarity Search
Pure Python cosine similarity. No PyTorch needed.
"""

import math


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def search(query_embedding: list[float], candidates: list[tuple[int, list[float]]], top_k: int = 50) -> list[tuple[int, float]]:
    """
    Search for most similar images.
    
    Args:
        query_embedding: embedding of the search query
        candidates: list of (image_id, embedding) tuples
        top_k: number of results to return
    
    Returns:
        List of (image_id, similarity_score) sorted by score descending
    """
    scored = []
    for img_id, emb in candidates:
        sim = cosine_similarity(query_embedding, emb)
        scored.append((img_id, sim))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
