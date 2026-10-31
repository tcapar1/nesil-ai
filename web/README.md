# nesilai Web (Cloudflare Pages)

Türkçe öncelikli, mobil uyumlu web istemcisi.

## Entegre edilen istemci özellikleri
- Supabase e-posta/parola kayıt, giriş, şifre sıfırlama ve kalıcı oturum.
- Kullanıcıya özel sohbet listesi ve mesaj geçmişi.
- Composer model seçimi: Groq Edge Function veya yerel Ollama.
- Belgelerim ekranı: özel Supabase Storage alanına dosya yükleme, listeleme, indirme ve kullanıcı onayıyla silme.
- Hafıza ekranı: kullanıcının kendi hafıza kayıtlarını ekleme, listeleme ve silme.
- Türkçe ve mobil uyumlu mevcut görsel tasarım korunmuştur.

## Güvenlik ve sınırlamalar
- Tarayıcıya yalnızca Supabase publishable key verilir. Service-role ve Groq anahtarları asla istemciye konmaz.
- Belge alanı için `202610310003_private_document_storage.sql` ve `202610310005_document_library_index.sql` migration'ları hedef Supabase projesinde uygulanmış olmalıdır. Hafıza tablosu temel şemada bulunur. Migration'ları canlıda uygulamadan önce mevcut şema karşılaştırılmalı ve yedek alınmalıdır.
- Dosyalar kullanıcı JWT'si, özel bucket ve RLS ile kullanıcı klasörüne yazılır. Şu an belge yükleme/indirme vardır; PDF/DOCX/XLSX içerik çıkarma ve sohbet bağlamına otomatik aktarma bu web istemcisine henüz port edilmemiştir.
- Yerel Ollama seçeneği yalnızca aynı bilgisayarda çalışan localhost servisine bağlanır. Ollama'da `OLLAMA_ORIGINS=https://nesilai.pages.dev` (ve yerel test için uygun localhost origin) yapılandırılmalıdır. Bu bağlantı Cloudflare'den uzaktaki bilgisayara proxy değildir; tarayıcı kullanıcısının kendi cihazındaki Ollama'ya erişir.
- Web araması, derin araştırma, gerçek görsel üretimi, güvenli Python sandbox ve yönetici/kota paneli henüz tamamlanmamıştır; eski Streamlit kodu doğrudan web istemcisine taşınmamıştır.
- Dosya silme kullanıcı onayı ister. Sohbet ve hafıza verileri Supabase RLS ile korunmalıdır.

## Cloudflare Pages
- Framework preset: None
- Build command: boş
- Build output directory: `web`
- Root directory: boş
- Preview branch: `integration/full-platform-20261101`

Canlı domain veya production branch ayarı, tüm testler ve kullanıcı kabulü tamamlanmadan değiştirilmez.
