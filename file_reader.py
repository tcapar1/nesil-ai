"""Bounded document extraction with explicit scope and per-file status."""
import csv
import io
import zipfile
from dataclasses import dataclass

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024
MAX_FILES = 5
MAX_TEXT = 12000
ALLOWED = ("txt", "md", "json", "py", "log", "csv", "pdf", "docx", "xlsx", "xlsm")


@dataclass
class FileResult:
    name: str
    text: str = ""
    status: str = "okunamadı"
    scope: str = ""


def extract_file(upload):
    name = upload.name
    if upload.size > MAX_FILE_BYTES:
        return FileResult(name, scope="10 MB sınırı aşıldı.")
    ext = name.lower().rsplit(".", 1)[-1]
    if ext not in ALLOWED:
        return FileResult(name, scope="Desteklenmeyen dosya türü.")
    raw = upload.getvalue()
    if len(raw) > MAX_FILE_BYTES:
        return FileResult(name, scope="10 MB sınırı aşıldı.")
    parts, scope = [], ""
    sampled = False
    try:
        if ext in ("docx", "xlsx", "xlsm"):
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                entries = archive.infolist()
                if len(entries) > 2000 or sum(e.file_size for e in entries) > 50 * 1024 * 1024:
                    return FileResult(name, scope="Belgenin açılmış boyutu veya öğe sayısı güvenlik sınırını aşıyor.")
        if ext in ("txt", "md", "json", "py", "log"):
            text = raw.decode("utf-8-sig", errors="replace")
            parts = [text[:MAX_TEXT + 1]]
            scope = "UTF-8 metni; çözülemeyen karakterler değiştirilir."
        elif ext == "csv":
            decoded = raw.decode("utf-8-sig", errors="replace")
            try:
                dialect = csv.Sniffer().sniff(decoded[:8192], delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel
            reader = csv.reader(io.StringIO(decoded), dialect)
            total = 0
            for index, row in enumerate(reader, 1):
                if index > 200:
                    sampled = True
                    break
                if len(row) > 50:
                    sampled = True
                line = f"Satır {index}: " + " | ".join(cell[:500] for cell in row[:50])
                sampled = sampled or any(len(cell) > 500 for cell in row[:50])
                parts.append(line)
                total += len(line)
                if total > MAX_TEXT:
                    sampled = True
                    break
            scope = "En fazla 200 satır, 50 sütun ve hücre başına 500 karakter."
        elif ext == "pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            sampled = len(reader.pages) > 30
            total = 0
            for index, page in enumerate(reader.pages[:30], 1):
                text = f"[Sayfa {index}]\n" + (page.extract_text() or "")
                parts.append(text[:MAX_TEXT + 1])
                total += len(text)
                if total > MAX_TEXT:
                    sampled = True
                    break
            scope = f"PDF: toplam {len(reader.pages)} sayfa; en fazla ilk 30 sayfa. OCR yok."
        elif ext == "docx":
            from docx import Document
            doc = Document(io.BytesIO(raw))
            total = 0
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    parts.append(paragraph.text[:MAX_TEXT + 1])
                    total += len(paragraph.text)
                if total > MAX_TEXT:
                    break
            for index, table in enumerate(doc.tables[:10], 1):
                if total > MAX_TEXT:
                    break
                for row_index, row in enumerate(table.rows[:100], 1):
                    text = f"[Tablo {index}, satır {row_index}] " + " | ".join(c.text[:500] for c in row.cells[:50])
                    parts.append(text)
                    total += len(text)
                    if total > MAX_TEXT:
                        break
            sampled = True
            scope = "Word ana metni ve en fazla 10 tablodan ilk 100 satır/50 sütun. Üstbilgi, metin kutusu ve görseller kapsam dışı."
        else:
            from openpyxl import load_workbook
            wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            try:
                for ws in wb.worksheets[:8]:
                    parts.append(f"[Sayfa: {ws.title}]")
                    sheet_chars = 0
                    for row_index, row in enumerate(ws.iter_rows(min_row=1, max_row=200, max_col=50, values_only=True), 1):
                        values = [str(v)[:500] if v is not None else "" for v in row]
                        if any(values):
                            line = f"[Sayfa: {ws.title}, satır {row_index}, sütunlar A:AX] " + " | ".join(values)
                            parts.append(line)
                            sheet_chars += len(line)
                            if sheet_chars > 2000:
                                break
            finally:
                wb.close()
            sampled = True
            scope = "Excel: ilk 8 sayfadan en fazla 200 satır/50 sütun ve sayfa başına yaklaşık 2.000 karakter. Formüller hesaplanmaz; kayıtlı sonuçlar okunur, boş/eski olabilir. Makrolar çalıştırılmaz."
        text = "\n".join(parts)
        sampled = sampled or len(text) > MAX_TEXT
        text = text[:MAX_TEXT]
        if not text.strip() or (ext == "pdf" and not any((p.split("\n", 1)[-1]).strip() for p in parts)):
            return FileResult(name, scope="Okunabilir metin bulunamadı. Taranmış PDF için OCR gerekebilir.")
        return FileResult(name, text, "kısmen okundu" if sampled else "okundu", scope + f" Çıkarılan kesit: {len(text)} karakter.")
    except Exception:
        return FileResult(name, scope="Dosya okunamadı. Biçim, bozulma veya parola korumasını kontrol edin.")


def select_context(results, prompt, limit=5000):
    """Deterministic excerpts, shared fairly; no paid embedding or API calls."""
    import re
    valid = [r for r in results if r.text]
    if not valid:
        return ""
    terms = set(re.findall(r"\w{3,}", prompt.casefold()))
    chunks = []
    per_file = max(100, (limit - 500) // len(valid))
    for result in valid:
        blocks = [result.text[i:i + 700] for i in range(0, len(result.text), 700)]
        ranked = sorted(enumerate(blocks), key=lambda pair: (-sum(t in pair[1].casefold() for t in terms), pair[0]))
        selected, remaining = [], per_file
        for index, block in ranked:
            if remaining <= 0:
                break
            selected.append((index, block[:remaining]))
            remaining -= len(block)
        chunks.append(f"DOSYA: {result.name[:120]} — {result.status}; seçilmiş kesitler, tüm belge değil.\n" + "\n[…]\n".join(b for _, b in sorted(selected)))
    return "\n\n".join(chunks)[:limit]
