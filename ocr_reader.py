"""Optional local OCR. No image/document is uploaded to an OCR service."""
import os


def ocr_page(raw, page_number):
    import pypdfium2 as pdfium
    import pytesseract
    with pdfium.PdfDocument(raw) as document:
        page = document[page_number]
        try:
            scale = min(1.5, 2000 / max(page.get_size()))
            bitmap = page.render(scale=scale)
            try:
                image = bitmap.to_pil()
                try:
                    return pytesseract.image_to_string(image, lang=os.environ.get("NESIL_OCR_LANG", "tur+eng"), timeout=8)
                finally:
                    image.close()
            finally:
                bitmap.close()
        finally:
            page.close()
