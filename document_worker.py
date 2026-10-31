"""Bound document parsing by running it outside the Streamlit process."""
import multiprocessing
from dataclasses import dataclass
from file_reader import FileResult, MAX_FILE_BYTES, MAX_FILES, MAX_TOTAL_BYTES, extract_file


@dataclass
class UploadData:
    name: str
    raw: bytes

    @property
    def size(self):
        return len(self.raw)

    def getvalue(self):
        return self.raw


def _extract_child(connection, upload, ocr):
    try:
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
        except (ImportError, ValueError, OSError):
            pass  # Windows: wall-clock timeout only, not a hard memory guarantee.
        connection.send(extract_file(upload, ocr=ocr))
    except Exception:
        connection.send(FileResult(upload.name, scope="Belge ayrıştırma tamamlanamadı."))
    finally:
        connection.close()


def extract_bounded(upload, ocr=False, timeout=35):
    if upload.size > MAX_FILE_BYTES:
        return FileResult(upload.name, scope="10 MB sınırı aşıldı.")
    raw = upload.getvalue()
    if len(raw) > MAX_FILE_BYTES:
        return FileResult(upload.name, scope="10 MB sınırı aşıldı.")
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_extract_child, args=(sender, UploadData(upload.name, raw), ocr), daemon=True)
    try:
        process.start()
        sender.close()
        if receiver.poll(timeout):
            result = receiver.recv()
            return result if isinstance(result, FileResult) else FileResult(upload.name, scope="Geçersiz belge sonucu.")
        return FileResult(upload.name, scope="Belge okuma süre sınırını aştı. Daha küçük parçalara ayırın.")
    except Exception:
        return FileResult(upload.name, scope="Belge çalışma alanı başlatılamadı veya ayrıştırma durdu.")
    finally:
        receiver.close()
        sender.close()
        if process.pid is not None:
            process.join(0.2)
            if process.is_alive():
                process.terminate()
                process.join(1)
            if process.is_alive():
                process.kill()
                process.join(1)
            if not process.is_alive():
                process.close()


def load_saved_documents(file_store, saved_rows, max_files=MAX_FILES, max_total_bytes=MAX_TOTAL_BYTES, ocr=False):
    """Load a bounded batch from a user's private library; never exceed session limits."""
    loaded, skipped, total_bytes = [], [], 0
    file_limit = max(0, min(int(max_files), MAX_FILES))
    byte_limit = max(0, min(int(max_total_bytes), MAX_TOTAL_BYTES))
    seen = set()
    for row in saved_rows:
        name = str(row.get("file_name") or "").strip()
        path = row.get("object_path")
        if not name or not isinstance(path, str):
            skipped.append((name or "Adsız dosya", "Dosya kaydı geçersiz."))
            continue
        if name in seen:
            skipped.append((name, "Aynı adlı belge bu oturumda zaten seçildi."))
            continue
        seen.add(name)
        if len(loaded) >= file_limit:
            skipped.append((name, f"En fazla {file_limit} belge tek seferde yüklenebilir."))
            continue
        declared_size = row.get("file_size")
        if isinstance(declared_size, (int, float)) and declared_size > MAX_FILE_BYTES:
            skipped.append((name, "Dosya 10 MB sınırını aşıyor."))
            continue
        if isinstance(declared_size, (int, float)) and total_bytes + declared_size > byte_limit:
            skipped.append((name, f"Belirlenen toplam yükleme sınırı ({byte_limit} bayt) aşılacağı için atlandı."))
            continue
        try:
            raw = file_store.download(path)
            if not isinstance(raw, bytes) or not raw:
                skipped.append((name, "Dosya boş veya okunamadı."))
                continue
            if len(raw) > MAX_FILE_BYTES:
                skipped.append((name, "Dosya 10 MB sınırını aşıyor."))
                continue
            if total_bytes + len(raw) > byte_limit:
                skipped.append((name, f"Belirlenen toplam yükleme sınırı ({byte_limit} bayt) aşılacağı için atlandı."))
                continue
            result = extract_bounded(UploadData(name, raw), ocr=ocr)
            if result.text:
                loaded.append(result)
                total_bytes += len(raw)
            else:
                skipped.append((name, result.scope or "Belge metni çıkarılamadı."))
        except Exception:
            skipped.append((name, "Dosya indirilemedi veya okunamadı."))
    return loaded, skipped
