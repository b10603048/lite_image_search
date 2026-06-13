"""
Lite Image Search — FastAPI Backend
"""

import os
import sys
import uuid
import sqlite3

# Ensure app directory is in sys.path (for embeddable Python / PyInstaller)
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
os.chdir(APP_DIR)
import config
import database
import gemini_client
import converter
import search

from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel


@asynccontextmanager
async def lifespan(app):
    config.ensure_dirs()
    yield

app = FastAPI(title="Lite Image Search", lifespan=lifespan)


# ── Placeholder image generator ──

def _placeholder_image(file_ext: str):
    """Generate a placeholder PNG with the file extension text."""
    from io import BytesIO
    from PIL import Image, ImageDraw, ImageFont

    w, h = 300, 300
    img = Image.new("RGB", (w, h), "#f0f0f0")
    draw = ImageDraw.Draw(img)

    # Draw file icon outline
    icon_x, icon_y = 100, 50
    icon_w, icon_h = 100, 130
    # Folded corner
    draw.rectangle([icon_x, icon_y, icon_x + icon_w, icon_y + icon_h], fill="#e0e0e0", outline="#bbb", width=2)
    # Triangle corner (fold)
    fold = 30
    draw.polygon([
        (icon_x + icon_w - fold, icon_y),
        (icon_x + icon_w, icon_y + fold),
        (icon_x + icon_w - fold, icon_y + fold),
    ], fill="#ccc", outline="#bbb")
    draw.line([(icon_x + icon_w - fold, icon_y), (icon_x + icon_w, icon_y + fold)], fill="#bbb", width=2)

    # Draw extension text
    ext_text = file_ext.upper().lstrip(".") or "FILE"
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        except Exception:
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), ext_text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (w - tw) // 2
    ty = icon_y + icon_h + 20
    draw.text((tx, ty), ext_text, fill="#555", font=font)

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return Response(content=buf.getvalue(), media_type="image/png")


# ── API Key ──

class ApiKeyRequest(BaseModel):
    api_key: str

@app.post("/api/key")
def set_api_key(req: ApiKeyRequest):
    config.set_api_key(req.api_key.strip())
    return {"ok": True}

@app.get("/api/key")
def get_api_key_status():
    key = config.get_api_key()
    return {"configured": bool(key), "masked": key[:8] + "..." if len(key) > 8 else ""}


# ── Upload ──

@app.post("/api/upload")
async def upload_images(files: list[UploadFile] = File(...)):
    """Upload one or more images, convert if needed, and create embeddings."""
    results = []
    errors = []

    for file in files:
        try:
            # Save original file
            ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".bin"
            safe_name = f"{uuid.uuid4().hex}{ext}"
            original_path = os.path.join(config.ORIGINAL_DIR, safe_name)

            with open(original_path, "wb") as f:
                content = await file.read()
                f.write(content)

            file_size = len(content)
            original_filename = file.filename or safe_name

            # Convert to PNG if needed
            converted_path = None
            conversion_error = ""
            try:
                img_path_for_embedding, mime_type = converter.convert_to_png(
                    original_path, config.CONVERTED_DIR
                )
                if img_path_for_embedding != original_path:
                    converted_path = img_path_for_embedding
            except Exception as e:
                conversion_error = str(e)
                try:
                    from PIL import Image
                    img = Image.open(original_path)
                    fallback_path = os.path.join(config.CONVERTED_DIR, f"{uuid.uuid4().hex}.png")
                    img.save(fallback_path, "PNG")
                    converted_path = fallback_path
                    img_path_for_embedding = fallback_path
                    mime_type = "image/png"
                except Exception as pillow_err:
                    # Pillow can't open it either (e.g. SVG, AI, EPS)
                    # Don't send raw vector files to Gemini — it only accepts raster formats
                    img_path_for_embedding = None
                    conversion_error = f"{conversion_error}; Pillow fallback also failed: {pillow_err}"

            # Create thumbnail
            thumb_source = converted_path or original_path
            thumb_path = None
            try:
                if thumb_source and os.path.exists(thumb_source):
                    thumb_path = converter.create_thumbnail(thumb_source, config.THUMBNAIL_DIR)
            except Exception:
                thumb_path = None

            # Get dimensions
            w, h = 0, 0
            try:
                if thumb_source and os.path.exists(thumb_source):
                    w, h = converter.get_image_dimensions(thumb_source)
            except Exception:
                w, h = 0, 0

            # Create embedding via Gemini API
            embedding = []
            embed_error = ""
            if img_path_for_embedding:
                try:
                    embedding = gemini_client.embed_image_file(img_path_for_embedding)
                except Exception as e:
                    embed_error = str(e)
                    embedding = []

            # If embedding failed, don't add to database — clean up and skip
            if not embedding:
                # Clean up saved files since we're not keeping this image
                for p in [original_path, converted_path, thumb_path]:
                    if p and os.path.exists(p):
                        try:
                            os.remove(p)
                        except Exception:
                            pass
                # Show the most specific error: API error > conversion error > generic
                reason = embed_error or conversion_error or "no image available for embedding"
                errors.append({"filename": original_filename, "error": f"Image not added: {reason}"})
                continue

            # Determine paths relative to data dir (normalize to forward slashes)
            rel_converted = config.norm_path(os.path.relpath(converted_path, config.BASE_DIR)) if converted_path else None
            rel_thumbnail = config.norm_path(os.path.relpath(thumb_path, config.BASE_DIR)) if thumb_path else None
            rel_original = config.norm_path(os.path.relpath(original_path, config.BASE_DIR))

            img_id = database.insert_image(
                filename=original_filename,
                file_ext=ext,
                original_path=rel_original,
                converted_path=rel_converted,
                thumbnail_path=rel_thumbnail,
                file_size=file_size,
                width=w,
                height=h,
                embedding=embedding,
            )
            result_info = {"id": img_id, "filename": original_filename, "has_embedding": bool(embedding)}
            if not img_path_for_embedding:
                result_info["warning"] = "Preview not available (converter missing)"
            results.append(result_info)

        except Exception as e:
            errors.append({"filename": getattr(file, "filename", "unknown"), "error": str(e)})

    return {"uploaded": results, "errors": errors}


# ── Search ──

class SearchRequest(BaseModel):
    query: str
    top_k: int = 50

@app.post("/api/search")
def search_images(req: SearchRequest):
    """Search images by text query using Gemini embedding + cosine similarity."""
    try:
        query_embedding = gemini_client.embed_text(req.query)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Embedding API error: {e}")

    candidates = database.get_all_embeddings()
    if not candidates:
        return {"results": []}

    scored = search.search(query_embedding, candidates, top_k=req.top_k)

    # Build result list with image info
    result_list = []
    for img_id, score in scored:
        img = database.get_image_by_id(img_id)
        if img:
            img["similarity"] = round(score, 4)
            result_list.append(img)

    return {"results": result_list}


# ── Homepage / Browse ──

@app.get("/api/images")
def list_images(sort: str = Query("newest", enum=["newest", "oldest", "downloads"]),
               fav: bool = Query(False)):
    """List all images for homepage. fav=true shows only favorites."""
    images = database.get_all_images(sort=sort, favorites_only=fav)
    return {"images": images, "total": len(images)}


# ── Single image ──

@app.get("/api/images/{image_id}")
def get_image(image_id: int):
    img = database.get_image_by_id(image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    return img


@app.delete("/api/images/{image_id}")
def delete_image(image_id: int):
    img = database.delete_image(image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    # Clean up files
    for path_key in ["original_path", "converted_path", "thumbnail_path"]:
        p = img.get(path_key)
        if p:
            full = os.path.join(config.BASE_DIR, p)
            if os.path.exists(full):
                try:
                    os.remove(full)
                except Exception:
                    pass
    return {"ok": True}


# ── Favorite ──

@app.post("/api/favorite/{image_id}")
def toggle_favorite(image_id: int):
    """Toggle favorite status for an image."""
    img = database.toggle_favorite(image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"ok": True, "favorite": img["favorite"]}


# ── Re-embed ──

@app.post("/api/reembed/{image_id}")
def reembed_image(image_id: int):
    """Re-embed an image using Gemini API. Updates the embedding vector."""
    img = database.get_image_by_id(image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    # Find the best file to embed from
    embed_path = None
    if img.get("converted_path"):
        full = os.path.join(config.BASE_DIR, img["converted_path"])
        if os.path.exists(full):
            embed_path = full
    if not embed_path and img.get("original_path"):
        full = os.path.join(config.BASE_DIR, img["original_path"])
        if os.path.exists(full):
            # Try converting first
            try:
                embed_path, _ = converter.convert_to_png(full, config.CONVERTED_DIR)
            except Exception:
                pass
            if not embed_path:
                embed_path = full

    if not embed_path:
        raise HTTPException(status_code=404, detail="No image file found on disk for embedding")

    try:
        embedding = gemini_client.embed_image_file(embed_path)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Embedding failed: {e}")

    if not embedding:
        raise HTTPException(status_code=502, detail="Embedding returned empty result")

    database.update_embedding(image_id, embedding)
    return {"ok": True, "has_embedding": True}


# ── Download ──

@app.get("/api/download/{image_id}")
def download_image(image_id: int):
    """Download original file. Increments download counter."""
    img = database.get_image_by_id(image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    # Always download original file
    rel_path = img.get("original_path")
    if not rel_path:
        raise HTTPException(status_code=404, detail="File not found")

    full_path = os.path.join(config.BASE_DIR, rel_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Determine mime type from extension
    ext = img.get("file_ext", "").lower()
    mime_map = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
        ".pdf": "application/pdf", ".psd": "image/vnd.adobe.photoshop",
        ".ai": "application/pdf", ".eps": "application/postscript",
        ".heic": "image/heic", ".heif": "image/heif",
        ".bmp": "image/bmp", ".tiff": "image/tiff", ".tif": "image/tiff",
    }
    mime = mime_map.get(ext, "application/octet-stream")
    download_name = img["filename"]
    return FileResponse(full_path, media_type=mime, filename=download_name, headers={
        "Cache-Control": "no-store",
    })


@app.post("/api/download-count/{image_id}")
def count_download(image_id: int):
    """Increment download counter. Called explicitly by UI, not by FileResponse."""
    img = database.get_image_by_id(image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    database.increment_download(image_id)
    return {"ok": True}


# ── Thumbnail ──

@app.get("/api/thumb/{image_id}")
def get_thumbnail(image_id: int):
    """Serve thumbnail image."""
    img = database.get_image_by_id(image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    thumb_path = img.get("thumbnail_path")
    if thumb_path and os.path.exists(os.path.join(config.BASE_DIR, thumb_path)):
        return FileResponse(os.path.join(config.BASE_DIR, thumb_path), media_type="image/png")

    # Fallback: serve converted or original
    rel_path = img.get("converted_path") or img.get("original_path")
    if rel_path and os.path.exists(os.path.join(config.BASE_DIR, rel_path)):
        return FileResponse(os.path.join(config.BASE_DIR, rel_path), media_type="image/png")

    # No preview available — generate a placeholder with file extension
    return _placeholder_image(img.get("file_ext", ""))


# ── Batch download ──

class BatchDownloadRequest(BaseModel):
    ids: list[int]

@app.post("/api/download-batch")
async def download_batch(req: BatchDownloadRequest):
    """Download multiple images as a ZIP file."""
    import zipfile

    # Use data/ dir instead of temp (more reliable in PyInstaller frozen mode)
    zip_path = os.path.join(config.DATA_DIR, "_batch_download.zip")
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for img_id in req.ids:
                img = database.get_image_by_id(img_id)
                if not img:
                    continue
                database.increment_download(img_id)
                # Always download original file
                rel_path = img.get("original_path")
                if not rel_path:
                    continue
                full_path = os.path.join(config.BASE_DIR, rel_path)
                if not os.path.exists(full_path):
                    continue
                zf.write(full_path, img["filename"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch download failed: {e}")

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="lite_image_search_batch.zip",
    )


@app.get("/api/download-batch-zip")
def download_batch_get(ids: str = Query(..., description="Comma-separated image IDs")):
    """Download multiple images as a ZIP file (GET version for window.open)."""
    import zipfile

    try:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IDs format")

    zip_path = os.path.join(config.DATA_DIR, "_batch_download.zip")
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for img_id in id_list:
                img = database.get_image_by_id(img_id)
                if not img:
                    continue
                database.increment_download(img_id)
                rel_path = img.get("original_path")
                if not rel_path:
                    continue
                full_path = os.path.join(config.BASE_DIR, rel_path)
                if not os.path.exists(full_path):
                    continue
                zf.write(full_path, img["filename"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch download failed: {e}")

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="lite_image_search_batch.zip",
    )


# ── Batch delete ──

class BatchDeleteRequest(BaseModel):
    ids: list[int]

@app.post("/api/delete-batch")
def delete_batch(req: BatchDeleteRequest):
    """Delete multiple images."""
    deleted = 0
    for img_id in req.ids:
        img = database.delete_image(img_id)
        if img:
            deleted += 1
            for path_key in ["original_path", "converted_path", "thumbnail_path"]:
                p = img.get(path_key)
                if p:
                    full = os.path.join(config.BASE_DIR, p)
                    if os.path.exists(full):
                        try:
                            os.remove(full)
                        except Exception:
                            pass
    return {"ok": True, "deleted": deleted}


# ── Stats ──

@app.get("/api/stats")
def stats():
    return {"total_images": database.get_image_count()}


# ── Export ──

@app.get("/api/export")
def export_gallery():
    """Export entire gallery (database + originals + thumbnails + converted) as ZIP."""
    import zipfile

    # Use data/ dir instead of temp (more reliable in PyInstaller frozen mode)
    zip_path = os.path.join(config.DATA_DIR, "_export.zip")
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. Database
            if os.path.exists(config.DB_PATH):
                zf.write(config.DB_PATH, "images.db")

            # 2. All files under data/
            for subdir in ["original", "converted", "thumbnails"]:
                dir_path = os.path.join(config.DATA_DIR, subdir)
                if not os.path.isdir(dir_path):
                    continue
                for fname in os.listdir(dir_path):
                    fpath = os.path.join(dir_path, fname)
                    if os.path.isfile(fpath):
                        zf.write(fpath, f"{subdir}/{fname}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="lite_image_search_export.zip",
    )


# ── Import ──

@app.post("/api/import")
async def import_gallery(file: UploadFile = File(...)):
    """Import gallery from a ZIP file (created by /api/export).
    Merges images by filename — skips duplicates."""
    import zipfile
    import shutil

    # Use data/ dir instead of temp (more reliable in PyInstaller frozen mode)
    zip_path = os.path.join(config.DATA_DIR, "_import_tmp.zip")
    extract_dir = os.path.join(config.DATA_DIR, "_import_tmp")
    try:
        content = await file.read()
        with open(zip_path, "wb") as f:
            f.write(content)

        # Clean up any previous extract
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

            # Read the imported database
            imported_db_path = os.path.join(extract_dir, "images.db")
            if not os.path.exists(imported_db_path):
                raise HTTPException(status_code=400, detail="Invalid export file: no images.db found")

            imported_db = sqlite3.connect(imported_db_path)
            imported_db.row_factory = sqlite3.Row
            imported_rows = imported_db.execute("SELECT * FROM images").fetchall()
            imported_db.close()

            # Get current filenames to detect duplicates
            current_db = database.get_db()
            try:
                existing_filenames = {
                    r["filename"]
                    for r in current_db.execute("SELECT filename FROM images").fetchall()
                }
            finally:
                current_db.close()

            imported_count = 0
            skipped_count = 0
            thumb_generated = 0

            for row in imported_rows:
                row_dict = dict(row)
                filename = row_dict.get("filename", "")

                # Skip if already exists
                if filename in existing_filenames:
                    skipped_count += 1
                    continue

                # Copy files from extracted zip to data directory
                for path_key in ["original_path", "converted_path", "thumbnail_path"]:
                    rel_path = row_dict.get(path_key)
                    if not rel_path:
                        continue
                    # Normalize to forward slashes for cross-platform compatibility
                    rel_path_norm = config.norm_path(rel_path)
                    src = os.path.join(extract_dir, rel_path_norm.replace("data/", "", 1))
                    dst = os.path.join(config.BASE_DIR, rel_path_norm)
                    if os.path.exists(src):
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)

                # Check if thumbnail exists; if not, try to generate one
                thumb_rel = row_dict.get("thumbnail_path")
                thumb_exists = False
                if thumb_rel:
                    thumb_full = os.path.join(config.BASE_DIR, config.norm_path(thumb_rel))
                    thumb_exists = os.path.exists(thumb_full)

                if not thumb_exists:
                    # Try to generate thumbnail from converted or original
                    thumb_source_rel = row_dict.get("converted_path") or row_dict.get("original_path")
                    if thumb_source_rel:
                        thumb_source_full = os.path.join(config.BASE_DIR, config.norm_path(thumb_source_rel))
                        if os.path.exists(thumb_source_full):
                            try:
                                new_thumb_path = converter.create_thumbnail(thumb_source_full, config.THUMBNAIL_DIR)
                                row_dict["thumbnail_path"] = os.path.relpath(new_thumb_path, config.BASE_DIR)
                                thumb_generated += 1
                            except Exception:
                                pass

                # Insert into current database (normalize all paths)
                embedding_blob = row_dict.get("embedding")
                embedding = database.blob_to_vec(embedding_blob) if embedding_blob else []

                new_id = database.insert_image(
                    filename=filename,
                    file_ext=row_dict.get("file_ext", ""),
                    original_path=config.norm_path(row_dict.get("original_path", "")),
                    converted_path=config.norm_path(row_dict.get("converted_path")),
                    thumbnail_path=config.norm_path(row_dict.get("thumbnail_path")),
                    file_size=row_dict.get("file_size", 0),
                    width=row_dict.get("width", 0),
                    height=row_dict.get("height", 0),
                    embedding=embedding,
                )
                # Restore favorite status
                if row_dict.get("favorite"):
                    database.toggle_favorite(new_id)

                imported_count += 1
                existing_filenames.add(filename)

            return {
                "ok": True,
                "imported": imported_count,
                "skipped": skipped_count,
                "thumbnails_generated": thumb_generated,
            }

    finally:
        # Clean up temporary files
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except Exception:
                pass


# ── Static files & SPA ──

app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

@app.get("/")
def index():
    return FileResponse(os.path.join(config.STATIC_DIR, "index.html"))
