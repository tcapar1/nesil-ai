# Aşamalı geliştirme

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

Kod web sunucusunda exec/subprocess ile çalıştırılmamalı. Ağ kapalı,
geçici dosyalı, kullanıcı başına izole, CPU/bellek/süre sınırı olan bir
sandbox kurulmalı. Uygun ortam seçilmeden özellik etkinleştirilmemeli.

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
