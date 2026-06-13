"""
Lite Image Search — Gemini Embedding API Client
Calls gemini-embedding-2 for both image and text embedding.
"""

import base64
import requests

import config


def _handle_api_error(resp: requests.Response):
    """Raise a clear error for API failures, especially rate limits."""
    if resp.status_code == 429:
        raise ValueError("Gemini API 用量已達上限 (429 Rate Limit)，請稍後再試或等待隔天重置")
    if resp.status_code == 403:
        raise ValueError("Gemini API Key 無效或已停用 (403 Forbidden)")
    if resp.status_code == 400:
        try:
            detail = resp.json().get("error", {}).get("message", resp.text[:200])
        except Exception:
            detail = resp.text[:200]
        raise ValueError(f"Gemini API 請求格式錯誤 (400): {detail}")
    resp.raise_for_status()


def embed_text(text: str) -> list[float]:
    """Embed a text query using Gemini Embedding API."""
    api_key = config.get_api_key()
    if not api_key:
        raise ValueError("Gemini API key not set")

    url = f"{config.GEMINI_BASE_URL}/models/{config.GEMINI_MODEL}:embedContent?key={api_key}"

    payload = {
        "model": f"models/{config.GEMINI_MODEL}",
        "content": {
            "parts": [{"text": text}]
        },
        "outputDimensionality": config.EMBEDDING_DIMENSION,
    }

    resp = requests.post(url, json=payload, timeout=30)
    _handle_api_error(resp)
    data = resp.json()
    return data["embedding"]["values"]


def embed_image(image_bytes: bytes, mime_type: str = "image/png") -> list[float]:
    """Embed an image using Gemini Embedding API."""
    api_key = config.get_api_key()
    if not api_key:
        raise ValueError("Gemini API key not set")

    url = f"{config.GEMINI_BASE_URL}/models/{config.GEMINI_MODEL}:embedContent?key={api_key}"

    b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": f"models/{config.GEMINI_MODEL}",
        "content": {
            "parts": [
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": b64,
                    }
                }
            ]
        },
        "outputDimensionality": config.EMBEDDING_DIMENSION,
    }

    resp = requests.post(url, json=payload, timeout=60)
    _handle_api_error(resp)
    data = resp.json()
    return data["embedding"]["values"]


def embed_image_file(file_path: str) -> list[float]:
    """Read an image file and embed it."""
    import os
    ext = os.path.splitext(file_path)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }
    mime_type = mime_map.get(ext, "image/png")
    with open(file_path, "rb") as f:
        return embed_image(f.read(), mime_type)
