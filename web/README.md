# nesilai Web (Cloudflare Pages)

Türkçe öncelikli, mobil uyumlu web istemcisi.

## Canlı sürüm ve doğrulama
- Production adresi: https://nesilai.pages.dev
- GitHub PR #21, 68 commit ile `main` dalına birleştirildi.
- `main` commit'i `b42decdbd3a1808a24cb45382abe89be15d28102`; Ubuntu, Windows ve Supabase-local testleri başarılı.
- Supabase `nesil-chat` Edge Function v5 ACTIVE olarak dağıtıldı.
- `secure_document_rpc_schema` migration'ı canlı veritabanında mevcut.
- `nesil_document_operations(document_id)` performans indeksi ayrıca canlıya eklendi.
- Canlı sohbetten giriş yapıp mesaj/yanıt akışı kullanıcı tarafından doğrulandı.

## Entegre edilen özellikler
- Supabase e-posta/parola kayıt, giriş, şifre sıfırlama ve kalıcı oturum.
- Kullanıcıya özel sohbet geçmişi; arama, yeniden adlandırma, sabitleme ve arşivleme.
- Sohbeti TXT, PDF ve DOCX (Word) olarak dışa aktarma.
- Groq Edge Function veya kullanıcının kendi bilgisayarındaki Ollama modeli.
- Belgelerim: özel Storage bucket, kullanıcı klasörü, 10 MB/dosya sınırı, SHA-256 özeti ve işlem kayıtlı yükleme/silme.
- TXT, CSV, Markdown, PDF, DOCX ve XLS/XLSX dosyalarında metin çıkarma; OCR destekli taranmış PDF ve görsel okuma.
- Hafıza: kullanıcıya ait kayıt ekleme, listeleme ve silme; sohbet yanıtlarında ilgili hafıza bağlamı.
- Günlük ve dakikalık sunucu tarafı kullanım kotaları.
- Mevcut koyu tema ve mobil yerleşim.

## Supabase güvenlik durumu
- Belge RPC güvenliği için `20261101001342_secure_document_rpc_schema` canlı migration'ı uygulanmıştır.
- Kullanım kota tabloları RLS etkin ve doğrudan istemci erişimi kapalıdır; kota RPC'leri anon/authenticated rollerine açık değildir.
- Supabase Advisor, Auth için sızdırılmış parola korumasının kapalı olduğunu bildiriyor. Bu ayar Auth/Password Protection kontrol panelinden ayrıca etkinleştirilmelidir; bu entegrasyonda ilgili Auth ayarını değiştiren bir yönetim aracı bulunmamaktadır.
- Dört kullanım/login tablosunda RLS etkin ve politika yok uyarısı bilgi seviyesindedir; tablolar doğrudan istemciye açılmamalıdır.
- Belge işlemleri foreign-key performans uyarısı, `document_id` indeksi eklenerek giderilmiştir. Advisor yeniden kontrol edilmelidir.

## Dosya işleme sınırları
- Dosyalar özel bucket'a, oturum sahibinin klasörüne yüklenir.
- PDF metin çıkarımı ilk 30 sayfa; OCR taranmış PDF'nin ilk 3 sayfası ile PNG/JPG/WEBP görsellerde Türkçe+İngilizce yapılır.
- Belge bağlamı AI isteğine en fazla 16.000 karakter aktarılır.
- Bir seferde en fazla 5 dosya; dosya başına 10 MB.
- Eski ikili DOC biçimi kabul edilmez.

## Yerel Ollama
Ollama kullanıcının kendi bilgisayarında çalışır; Cloudflare sunucusunda değildir. Tarayıcı localhost/127.0.0.1 servisine bağlanır. Ollama'da `OLLAMA_ORIGINS=https://nesilai.pages.dev` (yerel geliştirmede localhost origin'i de) yapılandırılmalıdır.

## Henüz etkin olmayan / ayrı altyapı gerektiren özellikler
- Kaynak doğrulamalı web araması ve derin araştırma.
- Gerçek görsel üretim sağlayıcısı.
- Güvenli, izole Python çalışma alanı.
- XLSX/PPTX rapor şablonları ve gelişmiş raporlama.
- Yönetici paneli ve kota yönetimi arayüzü.

Bu özellikler yalnızca ön yüz düğmesiyle güvenli biçimde etkinleştirilemez; sağlayıcı anahtarları, sunucu tarafı servisler ve/veya ayrı izolasyon altyapısı gerektirir. Kullanılabilir olmayan özellikler uygulamada hazırmış gibi gösterilmemelidir.

## Cloudflare Pages
- Framework preset: None
- Build command: boş
- Build output directory: `web`
- Root directory: boş
- Production domain: `nesilai.pages.dev`
