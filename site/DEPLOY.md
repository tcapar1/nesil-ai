# NESIL AI — Cloudflare Pages sitesi

Bu klasör, ana Python/Streamlit uygulamasından ayrı bir statik web sitesi içerir.

## Cloudflare Pages ayarları

- Project name: `nesilai`
- Production branch: `feature/cloudflare-pages-20261101` (ilk test için; ana dala geçmeyin)
- Root directory: `site`
- Build command: boş
- Build output directory: `.`
- Framework preset: None / Other

İlk dağıtım bir önizlemedir. `main` dalına birleştirme veya mevcut Worker'ı değiştirme yapmaz.

## Yayın öncesi kontrol

1. `https://nesilai.pages.dev` açılıyor mu?
2. Mobil görünüm ve bağlantılar çalışıyor mu?
3. Mevcut uygulamaya geçiş bağlantısı doğru mu?
4. Yeni uygulama henüz Streamlit özelliklerinin tamamını taşımadığı için eski uygulama, yeni sürüm eşdeğer testlerden geçene kadar kapatılmamalıdır.

## Güvenlik

Bu statik sitede API anahtarı, Supabase secret veya service-role key bulunmaz. Gizli anahtarlar yalnızca sunucu tarafı Cloudflare Worker secrets olarak tanımlanmalıdır.
