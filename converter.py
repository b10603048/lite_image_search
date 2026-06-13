"""
Lite Image Search — File Converter
Converts AI/PSD/PDF/SVG/HEIC etc. to PNG for embedding.
Original files are ALWAYS preserved.
"""

import os
import subprocess
import shutil
from typing import Optional

from PIL import Image

import config


# Extensions that can be opened by Pillow directly
PILLOW_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

# Extensions that need conversion
CONVERT_EXTENSIONS = {".ai", ".eps", ".psd", ".pdf", ".svg", ".heic", ".heif"}


def needs_conversion(ext: str) -> bool:
    """Check if the file extension needs conversion before embedding."""
    return ext.lower() not in PILLOW_EXTENSIONS


def convert_to_png(input_path: str, output_dir: str) -> tuple[str, str]:
    """
    Convert a file to PNG. Returns (converted_path, mime_type).
    If file is already a standard image, just copy to output_dir.
    """
    ext = os.path.splitext(input_path)[1].lower()
    basename = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, basename + ".png")

    if ext in PILLOW_EXTENSIONS:
        # Standard image — just copy (don't re-encode)
        return input_path, _ext_to_mime(ext)

    # Need conversion
    if ext == ".psd":
        return _convert_psd(input_path, output_path), "image/png"
    elif ext == ".svg":
        return _convert_svg(input_path, output_path), "image/png"
    elif ext in (".ai", ".eps"):
        return _convert_ai_eps(input_path, output_path), "image/png"
    elif ext == ".pdf":
        return _convert_pdf(input_path, output_path), "image/png"
    elif ext in (".heic", ".heif"):
        return _convert_heic(input_path, output_path), "image/png"
    else:
        # Fallback: try Pillow
        try:
            img = Image.open(input_path)
            img.save(output_path, "PNG")
            return output_path, "image/png"
        except Exception:
            raise ValueError(f"Unsupported file format: {ext}")


def create_thumbnail(image_path: str, thumb_dir: str, max_size: int = None) -> str:
    """Create a thumbnail for the image. Returns thumbnail path."""
    if max_size is None:
        max_size = config.THUMBNAIL_MAX_SIZE

    basename = os.path.splitext(os.path.basename(image_path))[0]
    # Use a safe name to avoid collisions
    thumb_path = os.path.join(thumb_dir, basename + "_thumb.png")

    img = Image.open(image_path)
    img = img.convert("RGB")
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    img.save(thumb_path, "PNG", optimize=True)
    return thumb_path


def get_image_dimensions(image_path: str) -> tuple[int, int]:
    """Get width and height of an image."""
    with Image.open(image_path) as img:
        return img.size


# ── Private converters ──

def _convert_psd(input_path: str, output_path: str) -> str:
    """Convert PSD to PNG using psd-tools."""
    from psd_tools import PSDImage
    psd = PSDImage.open(input_path)
    img = psd.composite()
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    img.save(output_path, "PNG")
    return output_path


def _convert_svg(input_path: str, output_path: str) -> str:
    """Convert SVG to PNG.
    
    Pipeline: svglib → reportlab PDF (no Cairo needed) → PyMuPDF PNG
    Fallback: cairosvg (needs libcairo-2 DLL), then system tools.
    """
    svglib_error = ""
    cairosvg_error = ""
    tools_error = ""

    # ── Method 1: svglib + reportlab PDF + PyMuPDF (ZERO native dependencies) ──
    # reportlab's PDF backend does NOT need Cairo (only renderPM/bitmap does)
    # So: SVG → svglib → reportlab PDF → PyMuPDF → PNG
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPDF
        import tempfile
        drawing = svg2rlg(input_path)
        if drawing:
            # Step 1: SVG → PDF (pure Python, no Cairo)
            tmp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp_pdf_path = tmp_pdf.name
            tmp_pdf.close()
            try:
                renderPDF.drawToFile(drawing, tmp_pdf_path)
                # Step 2: PDF → PNG (PyMuPDF, already installed)
                import fitz
                doc = fitz.open(tmp_pdf_path)
                page = doc.load_page(0)
                mat = fitz.Matrix(300/72, 300/72)
                pix = page.get_pixmap(matrix=mat)
                pix.save(output_path)
                doc.close()
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    return output_path
                svglib_error = "svglib→PDF→PNG produced empty output"
            finally:
                if os.path.exists(tmp_pdf_path):
                    os.unlink(tmp_pdf_path)
        else:
            svglib_error = "svglib returned None (SVG may use unsupported features)"
    except Exception as e:
        svglib_error = f"svglib error: {e}"

    # ── Method 2: CairoSVG (needs libcairo-2.dll on Windows) ──
    try:
        import cairosvg
        cairosvg.svg2png(url=input_path, write_to=output_path, dpi=300)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
        cairosvg_error = "cairosvg rendered empty output"
    except Exception as e:
        cairosvg_error = f"cairosvg error: {e}"

    # ── Method 3: rsvg-convert or inkscape (system tools) ──
    try:
        import shutil as _shutil
        rsvg = _shutil.which("rsvg-convert")
        if rsvg:
            result = subprocess.run(
                [rsvg, "-w", "1024", "-h", "1024", "-f", "png", "-o", output_path, input_path],
                capture_output=True, timeout=30
            )
            if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            tools_error = "rsvg-convert failed"
        inkscape = _shutil.which("inkscape")
        if inkscape:
            result = subprocess.run(
                [inkscape, input_path, "--export-type=png", f"--export-filename={output_path}", "--export-dpi=300"],
                capture_output=True, timeout=30
            )
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            tools_error = "inkscape failed"
        if not rsvg and not inkscape:
            tools_error = "no system SVG tools found"
    except Exception as e:
        tools_error = f"system tools error: {e}"

    # Combine all errors for diagnosis
    errors = [e for e in [svglib_error, cairosvg_error, tools_error] if e]
    detail = "; ".join(errors)
    raise RuntimeError(
        f"Cannot convert SVG file: {detail}. "
        "Try: pip install svglib reportlab, or pip install cairosvg, or install rsvg-convert / inkscape."
    )


def _convert_ai_eps(input_path: str, output_path: str) -> str:
    """Convert AI/EPS to PNG. Uses PyMuPDF (AI is PDF-based) or Ghostscript as fallback."""
    # Try PyMuPDF first (no external dependency needed)
    try:
        import fitz
        doc = fitz.open(input_path)
        page = doc.load_page(0)
        # Render at 300 DPI (zoom = 300/72)
        mat = fitz.Matrix(300/72, 300/72)
        pix = page.get_pixmap(matrix=mat, alpha=True)
        pix.save(output_path)
        doc.close()
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
    except Exception:
        pass

    # Fallback: try Ghostscript
    gs_cmd = _find_ghostscript()
    if gs_cmd:
        cmd = [
            gs_cmd, "-dNOPAUSE", "-dBATCH", "-dSAFER",
            "-sDEVICE=pngalpha",
            "-r300",
            f"-sOutputFile={output_path}",
            input_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(output_path):
            return output_path

    raise RuntimeError(
        "Cannot convert AI/EPS file. PyMuPDF failed and Ghostscript not found.\n"
        "Install Ghostscript from https://ghostscript.com for AI/EPS support."
    )


def _convert_pdf(input_path: str, output_path: str) -> str:
    """Convert first page of PDF to PNG. Uses PyMuPDF first, then pdf2image/poppler."""
    # Try PyMuPDF first (no external dependency)
    try:
        import fitz
        doc = fitz.open(input_path)
        page = doc.load_page(0)
        mat = fitz.Matrix(300/72, 300/72)
        pix = page.get_pixmap(matrix=mat)
        pix.save(output_path)
        doc.close()
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
    except Exception:
        pass

    # Fallback: pdf2image (requires poppler)
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(input_path, dpi=300, first_page=1, last_page=1)
        if images:
            images[0].save(output_path, "PNG")
            return output_path
    except Exception:
        pass

    raise RuntimeError("Cannot convert PDF. PyMuPDF failed and poppler not found.")


def _convert_heic(input_path: str, output_path: str) -> str:
    """Convert HEIC/HEIF to PNG using pillow-heif."""
    from pillow_heif import register_heif_opener
    register_heif_opener()
    img = Image.open(input_path)
    img = img.convert("RGB")
    img.save(output_path, "PNG")
    return output_path


def _find_ghostscript() -> Optional[str]:
    """Find Ghostscript executable. Checks runtime/ghostscript first, then PATH."""
    # Check portable Ghostscript in runtime directory
    # Look for the app's runtime/ghostscript relative to this file
    app_dir = os.path.dirname(os.path.abspath(__file__))
    runtime_gs = os.path.join(app_dir, "runtime", "ghostscript")
    if os.path.isdir(runtime_gs):
        for name in ["gswin64c.exe", "gswin32c.exe", "gs"]:
            path = os.path.join(runtime_gs, name)
            if os.path.isfile(path):
                return path
        # Check bin/ subdirectory (standard GS layout)
        bin_dir = os.path.join(runtime_gs, "bin")
        if os.path.isdir(bin_dir):
            for name in ["gswin64c.exe", "gswin32c.exe", "gs"]:
                path = os.path.join(bin_dir, name)
                if os.path.isfile(path):
                    return path

    # Check system PATH
    candidates = ["gs", "gswin64c", "gswin32c", "mgs"]
    for cmd in candidates:
        if shutil.which(cmd):
            return cmd
    return None


def _ext_to_mime(ext: str) -> str:
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".webp": "image/webp", ".bmp": "image/bmp",
        ".tiff": "image/tiff", ".tif": "image/tiff",
    }
    return mime_map.get(ext.lower(), "image/png")
