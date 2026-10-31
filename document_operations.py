"""Recoverable coordination for Storage objects and user-owned metadata."""
import hashlib


def save_document(file_store, data_store, filename, raw, operation_id):
    """Write ledger first, then object, then atomically finalize metadata + ledger."""
    description = file_store.describe_upload(filename, raw, operation_id)
    data_store.begin_document_upload(operation_id, description["path"], description["name"],
                                     description["size"], description["content_type"], description["sha256"])
    file_store.upload(filename, raw, operation_id=operation_id)
    return data_store.finish_document_upload(operation_id)


def delete_document(file_store, data_store, operation_id, document_id, object_path):
    """Keep the operation pending until Storage deletion and metadata removal finish."""
    data_store.begin_document_delete(operation_id, document_id)
    file_store.delete(object_path)
    return data_store.finish_document_delete(operation_id)


def recover_upload(file_store, data_store, operation, filename, raw):
    """Only replay when the reselected file matches the original operation digest."""
    if (filename != operation.get("file_name") or len(raw) != int(operation.get("file_size", -1))
            or hashlib.sha256(raw).hexdigest() != operation.get("sha256")):
        raise ValueError("Kurtarma için aynı dosya seçilmelidir.")
    file_store.upload(filename, raw, operation_id=operation["operation_id"])
    return data_store.finish_document_upload(operation["operation_id"])


def recover_delete(file_store, data_store, operation):
    """Retry object removal idempotently, then complete catalog cleanup."""
    file_store.delete(operation["object_path"])
    return data_store.finish_document_delete(operation["operation_id"])
