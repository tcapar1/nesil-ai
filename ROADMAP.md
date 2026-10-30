# Aşamalı geliştirme

## 30 Ekim 2026 — güvenilirlik ve ücretsiz kullanım güncellemesi

- Sohbet/araştırma ayrımı, zorunlu arama kaynaklı hata riskinin azaltılması.
- Gizli veri içermeyen hata kimliği/kategori kaydı.
- Açık sağlayıcı kaynak metadata'sı ve alıntı kimliği eşleştirmesi; kaynaksız
  araştırma ayrıntıları yerine açık başarısızlık yanıtı.
- İsteğe bağlı kaynak kesiti/yanıt karşılaştırması ve yönetici ek kaynak alan adları.
- Uzun belgelerde örtüşen kesit araması ve kaynak konumları; ayrı süreç/süre sınırı.
- İsteğe bağlı yerel OCR; sunucuda Tesseract/dil verisi kurulumu gerekir.
- Küçük ekip giriş kapısı, SQLite üzerinden ortak günlük/dakikalık kota ve 429 beklemesi.
- Ücretsiz Groq plan sınırları altında varsayılanlar; ücretli yedek servis yok.
- Windows ve Linux için otomatik test iş akışı.

Canlı Groq arama şeması ve gerçek cevap doğruluğu, gerçek Tesseract OCR,
çok sunuculu kota deposu, tam kimlik yönetimi ve mobil görsel deneme sonraki
doğrulama/geliştirme başlıklarıdır. Aşağıdaki aşamalar tarihsel planı açıklar;
güncel kurulum ve sınırlar README içindedir.

## 1. Güvenilir temel — bu değişiklik

Streamlit korunur. Model bağlantısı ve belge okuma ayrılır. Ham sağlayıcı
hataları gizlenir; dosya kapsamı ve kota beklemesi görünür. Sabit nüfus
yönlendirmesi kaldırılır. Mock testler gerçek API kullanmaz.

## 2. Araştırma ve bağlam

Kaynak URL'leri ayrı kayıtta tutulur ve JSON indirme sunulur. Kullanıcı
düğmesiyle sınırlı resmî/birincil alan adlarından ilk 3 kaynak okunabilir;
sayfa başlığı, erişim zamanı, açık metadata tarihleri ve metin kesiti kayda
eklenir. Sayfa erişimi iddia doğrulaması değildir. Bulunmayan alanlar boş kalır.
Kullanıcı düzenlemeli sohbet notu ve ilgili eski turları seçme eklenmiştir.
Araştırma başarısı araç kaydından ve yanıt iddiaları kaynak kanıtlarından
ayrıca doğrulanmalı. Kaynak çelişkileri,
prompt injection ve uzun konuşma Türkçe değerlendirme setiyle ölçülmeli.
Kesin token sayımı, ilgili kesitlerde kaynak konumu ve kullanıcı onaylı
hafıza tasarlanmalı. Akışlı yanıt ve gerçek mobil görsel test eklenmeli.

## 3. Güvenli kod çalıştırma

Tarayıcıda deneysel Python Mini eklenmiştir: kısa MicroPython kodu,
geçici sanal dosyalar, ağ kısıtlaması ve durdurma denetimi. Tam tarayıcı
CPU/bellek kotası garanti edilmez; yalnızca incelenmiş kodlar içindir.
Sınırlar ve veri akışı `PYTHON_MINI.md` dosyasındadır.

Tam CPython ve güvenilmeyen kod için ayrı konteyner/VM servisi, çekirdek
düzeyinde kaynak kotası ve kullanıcı başına izolasyon gerekir. Web sunucusunda
exec/subprocess kullanılmamalı. Bu servis olmadan tam Python açılmamalı.

## 4. Ses ve görsel

Son yanıtı tarayıcının yerel olarak bildirdiği seslerle dinleme eklenmiştir.
Kullanıcı denetimleri açıp Dinle düğmesine basar; uygun yerel ses yoksa
uzak ses hizmetine geçilmez. Gerçek cihazlarda ses kalitesi ve destek ayrıca
test edilmelidir. Mikrofon/transkripsiyon ve görsel üretimi henüz yoktur.

Önce sağlayıcıların ücretsiz sınırları ve veri işleme koşulları doğrulanmalı.
Yükleme boyutu/süre sınırları ve oturum bazlı silme sağlanmalı. Görsel
anlama, görsel üretme, konuşmayı yazıya çevirme ve seslendirme ayrı araçlar
olmalı. Ücretli kullanım kullanıcı onayı olmadan açılmamalı.

## 5. E-posta ve hesap bağlantıları

Hesaba bağlanmadan, gönderilmeyen `.eml` taslağı hazırlama/indirme eklenmiştir.
Son yanıt taslağa alınabilir; kullanıcı konu/alıcı/metni düzenler. Gerçek
e-posta gönderimi veya hesap işlemi yapılmaz.

OAuth ve en az yetki kullanılmalı; şifre veya erişim token'ı sohbete
istenmemeli. Önce salt okunur işlevler ve taslak hazırlama; gönderim veya
önemli değişiklikten önce somut alıcı/içerik/işlem önizlemesi ve onay.
Token'lar şifreli saklanmalı; bağlantıyı kesme/silme desteklenmeli.

## 6. Windows yerel yardımcı

İlk hedef kullanıcının kendi Windows bilgisayarıdır. İnternete açık komut
uç noktası oluşturulmamalı. Eşleştirme, izin verilen işlemler, görünür
çalışma durumu, durdurma düğmesi ve hassas işlemlerde onay gerekir.
Her kullanıcının cihazını desteklemek ayrı dağıtım/güncelleme aşamasıdır.

## 7. Ölçek

Ölçümlere göre ortak kota/kuyruk yönetimi, kullanıcı hesapları, isteğe bağlı
kalıcı sohbet ve ayrı arka uç değerlendirilmeli. Ücretsiz erişim bir hizmet
bütçesiyle sınırlandırılmalı; sınırsız ücretsiz kullanım vaat edilmemeli.
