"""Bound document parsing by running it outside the Streamlit process."""
import multiprocessing
from dataclasses import dataclass
from file_reader import FileResult, MAX_FILE_BYTES, extract_file


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
            process.close()
