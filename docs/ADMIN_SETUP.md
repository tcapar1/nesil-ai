# Nesil AI Yönetici Paneli

Yönetici paneli, doğrulanmış Supabase Auth oturumunu sunucu tarafında kontrol eder. Tarayıcıya service-role anahtarı gönderilmez.

## Yönetici hesabı

Varsayılan yönetici e-postası: `tuncaycapar1@gmail.com`.

Gerekirse yönetici listesini Supabase Function secret olarak tanımlayın:

```powershell
supabase secrets set NESIL_ADMIN_EMAILS="tuncaycapar1@gmail.com" --project-ref zwdrqhqpbuvpqteuklbg
```

Bu komut yalnızca yönetici e-posta listesini ayarlar; veritabanına dokunmaz.

## Yönetici API'sini dağıtma

Supabase CLI ile doğru projeye giriş yapıp fonksiyonu dağıtın:

```powershell
supabase login
supabase functions deploy nesil-admin --project-ref zwdrqhqpbuvpqteuklbg
```

Fonksiyon, Supabase'in sunucu tarafında sağladığı `SUPABASE_URL`, `SUPABASE_ANON_KEY` ve `SUPABASE_SERVICE_ROLE_KEY` ortam değişkenlerini kullanır. Service-role anahtarını GitHub'a, web/config.js dosyasına veya tarayıcıya koymayın.

## Panelin gösterdikleri

- Auth kullanıcılarının e-posta adresi, kayıt tarihi, son giriş ve e-posta doğrulama durumu
- Toplam sohbet, mesaj ve belge kayıt sayıları
- En fazla 1.000 kullanıcı; daha büyük hesaplarda liste ilk 1.000 kullanıcıyla sınırlıdır

Panel salt okunurdur. Kullanıcı sohbetlerinin içeriklerini, parolaları veya dosya içeriklerini yönetici listesine açmaz. Bu özellik için yeni veritabanı migration'ı gerekmez.

## Doğrulama

Dağıtımdan sonra `https://nesilai.pages.dev/` adresinde `tuncaycapar1@gmail.com` hesabıyla giriş yapın. Sol menüde **Yönetim paneli** görünmelidir. Normal kullanıcıda bu menü görünmez ve yönetici API'si HTTP 403 döndürür.
