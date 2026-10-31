-- Add PPTX and raster image OCR formats to the existing private document bucket.
-- Apply only after confirming migration 202610310003_private_document_storage.sql
-- has been applied in the target environment. No stored objects are changed.
update storage.buckets
set allowed_mime_types = array(
  select distinct allowed.mime
  from unnest(
    coalesce(allowed_mime_types, array[]::text[]) || array[
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'image/png', 'image/jpeg', 'image/tiff', 'image/bmp'
    ]::text[]
  ) as allowed(mime)
)
where id = 'nesil-user-files';
