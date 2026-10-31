"""Optional local OCR. No image/document is uploaded to an OCR service."""
import os
import io
import shutil
import subprocess
import re


def _run_tesseract(png_bytes):
    executable = shutil.which("tesseract")
    if not executable:
        raise RuntimeError("Tesseract is not installed")
    language = os.environ.get("NESIL_OCR_LANG", "tur+eng")
    if not re.fullmatch(r"[A-Za-z0-9_+]{1,80}", language):
        raise ValueError("Invalid OCR language")
    result = subprocess.run([executable, "stdin", "stdout", "-l", language, "--dpi", "150"],
        input=png_bytes, capture_output=True, timeout=8, check=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    return result.stdout[:240000].decode("utf-8", errors="replace")


def ocr_page(raw, page_number):
    import pypdfium2 as pdfium
    with pdfium.PdfDocument(raw) as document:
        page = document[page_number]
        try:
            scale = min(1.5, 2000 / max(page.get_size()))
            bitmap = page.render(scale=scale)
            try:
                image = bitmap.to_pil()
                try:
                    png = io.BytesIO()
                    image.save(png, format="PNG")
                    return _run_tesseract(png.getvalue())
                finally:
                    image.close()
            finally:
                bitmap.close()
        finally:
            page.close()


def ocr_image(raw):
    """OCR only the first bounded frame of a raster image, locally."""
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(raw)) as source:
        if source.width < 1 or source.height < 1 or source.width * source.height > 20_000_000:
            raise ValueError("Image pixel limit exceeded")
        source.seek(0)
        image = ImageOps.exif_transpose(source).convert("RGB")
        try:
            image.thumbnail((2000, 2000))
            png = io.BytesIO()
            image.save(png, format="PNG")
            return _run_tesseract(png.getvalue())
        finally:
            image.close()
