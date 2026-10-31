# nesilai Web (Cloudflare Pages)

Türkçe öncelikli, mobil uyumlu web istemcisi.

## Entegre edilen özellikler
- Supabase e-posta/parola kayıt, giriş, şifre sıfırlama ve kalıcı oturum.
- Kullanıcıya özel sohbet geçmişi; arama, yeniden adlandırma, sabitleme ve arşivleme.
- Sohbeti TXT olarak dışa aktarma.
- Composer model seçimi: Groq Edge Function veya kullanıcının kendi bilgisayarındaki Ollama.
- Belgelerim: özel Storage bucket, kullanıcı klasörü, 10 MB/dosya sınırı, SHA-256 özeti ve işlem kayıtlı yükleme/silme.
- Hafıza: kullanıcıya ait kayıt ekleme, listeleme ve silme; sohbet yanıtlarında ilgili hafıza bağlamı.
- Mevcut koyu tema ve mobil yerleşim korunmuştur.

## Supabase doğrulama durumu
Hedef Supabase projesinde şu anda `nesil_documents`, `nesil_document_operations`, `nesil_memory_items`, sohbet tabloları ve `nesil-user-files` özel bucket'ı bulunmaktadır. Bucket 10 MB sınırıyla ve authenticated kullanıcı klasör politikalarıyla yapılandırılmıştır. Sohbet, belge, hafıza ve Storage RLS politikaları kontrol edilmiştir.

Supabase Advisor şu konuları raporlamıştır:
- Dört belge işlem RPC fonksiyonu `public` şemasında SECURITY DEFINER olarak authenticated rolüne açık. Bu PR'da bunları `private` şemasına taşıyan ve public tarafta SECURITY INVOKER sarmalayıcıları bırakan `20261101000100_secure_document_rpc_schema.sql` migration'ı eklendi. Bu migration henüz hedef projeye uygulanmadı.
- Usage/login yardımcı tablolarında doğrudan kullanıcı politikası yoktur; bunlar istemciye açılmamalı, yalnızca sunucu tarafında kullanılmalıdır.
- Auth için sızdırılmış parola koruması kapalıdır; Supabase Auth ayarlarından ayrıca etkinleştirilmesi önerilir.

Migration'ı canlı Supabase projesine uygulamadan önce veritabanı yedeği alınmalı, migration staging/yerel ortamda test edilmeli ve advisor yeniden çalıştırılmalıdır. Bu web istemcisi canlı şema değişikliği yapmaz.

## Dosya işleme sınırları
- Dosyalar yalnızca özel bucket'a, oturum sahibinin klasörüne yüklenir.
- Şu an dosya yükleme, listeleme, indirme ve onaylı silme vardır. TXT ve CSV belgeleri için sınırlı metin çıkarma ve sohbet içinde bağlamlı analiz eklendi; metin AI isteğine en fazla 16.000 karakter olarak aktarılır.
- PDF/DOCX/XLSX metin çıkarma, OCR, dosya içeriğini sohbet bağlamına aktarma henüz web sürümüne taşınmamıştır.
- Bir seferde en fazla 5 dosya; dosya başına 10 MB. Desteklenen türler PDF, DOC/DOCX, XLS/XLSX, CSV, TXT, PNG, JPEG ve WEBP'dir.

## Yerel Ollama
Ollama, Cloudflare sunucusunda değil kullanıcının kendi bilgisayarında çalışır. Tarayıcı yalnızca localhost/127.0.0.1 servisine bağlanır. Ollama'da `OLLAMA_ORIGINS=https://nesilai.pages.dev` (yerel geliştirmede kullanılan localhost origin'i de) yapılandırılmalıdır. Bu ayar başka bir bilgisayara proxy sağlamaz.

## Henüz tamamlanmayanlar
- Web araması ve kaynak doğrulamalı derin araştırma.
- PDF/Office metin çıkarma, OCR ve sohbet içi belge analizi.
- DOCX/PDF rapor dışa aktarma.
- Güvenli, izole Python çalışma alanı.
- Gerçek görsel üretim servisi entegrasyonu.
- Yönetici paneli ve kota yönetimi.

Eski Streamlit/Python kodu doğrudan tarayıcıya kopyalanmamıştır. Bu özellikler ayrı, güvenli servisler olarak uyarlanmalıdır.

## Cloudflare Pages
- Framework preset: None
- Build command: boş
- Build output directory: `web`
- Root directory: boş
- Preview branch: `integration/full-platform-20261101`

Canlı domain veya production branch ayarı, tüm testler ve kullanıcı kabulü tamamlanmadan değiştirilmez.
