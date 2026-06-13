"""
Lite Image Search — SQLite Database
Stores image metadata + embedding vectors as BLOB.
"""

import sqlite3
import struct
import time
from typing import Optional

import config

# ── Vector serialization ──

def vec_to_blob(vec: list[float]) -> bytes:
    """Convert float32 list to BLOB."""
    return struct.pack(f"{len(vec)}f", *vec)


def blob_to_vec(blob: bytes) -> list[float]:
    """Convert BLOB back to float32 list."""
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


# ── Database init ──

def get_db() -> sqlite3.Connection:
    config.ensure_dirs()
    db = sqlite3.connect(config.DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    _init_tables(db)
    return db


def _init_tables(db: sqlite3.Connection):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS images (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filename    TEXT NOT NULL,           -- original filename
            file_ext    TEXT NOT NULL,           -- e.g. '.ai', '.psd', '.jpg'
            original_path  TEXT NOT NULL,        -- path under data/original/
            converted_path TEXT,                 -- path under data/converted/ (None if standard image)
            thumbnail_path TEXT,                 -- path under data/thumbnails/
            file_size   INTEGER DEFAULT 0,
            width       INTEGER DEFAULT 0,      -- converted image width
            height      INTEGER DEFAULT 0,      -- converted image height
            embedding   BLOB,                   -- float32 vector
            upload_time REAL NOT NULL,           -- unix timestamp
            download_count INTEGER DEFAULT 0,
            favorite    INTEGER DEFAULT 0        -- 0=not fav, 1=fav
        );

        CREATE INDEX IF NOT EXISTS idx_upload_time ON images(upload_time);
        CREATE INDEX IF NOT EXISTS idx_download_count ON images(download_count);
    """)
    # Migrate: add favorite column if missing (existing DB)
    try:
        db.execute("ALTER TABLE images ADD COLUMN favorite INTEGER DEFAULT 0")
        db.commit()
    except Exception:
        pass
    # Create favorite index (safe now — column guaranteed to exist)
    db.execute("CREATE INDEX IF NOT EXISTS idx_favorite ON images(favorite)")
    db.commit()


# ── CRUD ──

def insert_image(
    filename: str,
    file_ext: str,
    original_path: str,
    converted_path: Optional[str],
    thumbnail_path: Optional[str],
    file_size: int,
    width: int,
    height: int,
    embedding: list[float],
) -> int:
    """Insert an image record. Returns the new row id."""
    db = get_db()
    try:
        cur = db.execute(
            """INSERT INTO images
               (filename, file_ext, original_path, converted_path, thumbnail_path,
                file_size, width, height, embedding, upload_time, download_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (filename, file_ext, original_path, converted_path, thumbnail_path,
             file_size, width, height, vec_to_blob(embedding), time.time()),
        )
        db.commit()
        return cur.lastrowid
    finally:
        db.close()


def get_all_images(sort: str = "newest", favorites_only: bool = False) -> list[dict]:
    """Get all images for homepage, sorted. Optionally filter favorites."""
    db = get_db()
    try:
        order = {
            "newest": "upload_time DESC",
            "oldest": "upload_time ASC",
            "downloads": "download_count DESC",
        }.get(sort, "upload_time DESC")

        if favorites_only:
            rows = db.execute(f"SELECT * FROM images WHERE favorite = 1 ORDER BY {order}").fetchall()
        else:
            rows = db.execute(f"SELECT * FROM images ORDER BY {order}").fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        db.close()


def get_image_by_id(image_id: int) -> Optional[dict]:
    db = get_db()
    try:
        row = db.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        db.close()


def increment_download(image_id: int):
    db = get_db()
    try:
        db.execute("UPDATE images SET download_count = download_count + 1 WHERE id = ?", (image_id,))
        db.commit()
    finally:
        db.close()


def get_all_embeddings() -> list[tuple[int, list[float]]]:
    """Return list of (id, embedding) for similarity search."""
    db = get_db()
    try:
        rows = db.execute("SELECT id, embedding FROM images WHERE embedding IS NOT NULL").fetchall()
        return [(r["id"], blob_to_vec(r["embedding"])) for r in rows]
    finally:
        db.close()


def delete_image(image_id: int) -> Optional[dict]:
    db = get_db()
    try:
        row = db.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
        if row:
            db.execute("DELETE FROM images WHERE id = ?", (image_id,))
            db.commit()
            return _row_to_dict(row)
        return None
    finally:
        db.close()


def get_image_count() -> int:
    db = get_db()
    try:
        row = db.execute("SELECT COUNT(*) as cnt FROM images").fetchone()
        return row["cnt"]
    finally:
        db.close()


def toggle_favorite(image_id: int) -> Optional[dict]:
    """Toggle favorite status. Returns updated image or None."""
    db = get_db()
    try:
        row = db.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
        if not row:
            return None
        new_val = 0 if row["favorite"] else 1
        db.execute("UPDATE images SET favorite = ? WHERE id = ?", (new_val, image_id))
        db.commit()
        row = db.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        db.close()


def update_embedding(image_id: int, embedding: list[float]) -> bool:
    """Update the embedding vector for an image. Returns True if updated."""
    db = get_db()
    try:
        row = db.execute("SELECT id FROM images WHERE id = ?", (image_id,)).fetchone()
        if not row:
            return False
        db.execute("UPDATE images SET embedding = ? WHERE id = ?",
                   (vec_to_blob(embedding), image_id))
        db.commit()
        return True
    finally:
        db.close()


# ── Helpers ──

def _row_to_dict(r: sqlite3.Row) -> dict:
    d = dict(r)
    # Don't include raw embedding bytes in API responses
    d.pop("embedding", None)
    d["has_embedding"] = r["embedding"] is not None
    return d
