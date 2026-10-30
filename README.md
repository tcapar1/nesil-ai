# Nesil AI

Türkçe öncelikli Streamlit asistanı. Bu sürüm sohbet, dört çalışma modu,
belgelerden sınırlı metin çıkarma, isteğe bağlı Groq web araştırması ve TXT
sohbet indirme sunar. Bilgisayar kontrolü, kod çalıştırma, e-posta, görsel ve
ses araçları henüz uygulanmamıştır; `ROADMAP.md` aşamalarını izleyin.

## Kurulum

Python 3.11 veya 3.12:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

`GROQ_API_KEY` yalnızca ortam değişkeninden veya yerel/Streamlit Cloud
Secrets içinden okunur. Anahtarı depoya veya sohbetlere yazmayın. Anahtar
yokken gerçek cevap üretilmez. Ücretli hizmet otomatik etkinleştirilmez;
mevcut hesabın kullanım ve ücret politikası geçerlidir.

## Dosyalar ve gizlilik

- En fazla 5 dosya, dosya başına 10 MB ve toplam 20 MB.
- PDF: ilk 30 sayfaya kadar metin, OCR yok.
- DOCX: ana metin ve sınırlı tablolar. Metin kutuları ve görseller okunmaz.
- Excel: ilk 8 sayfa, en fazla 200 satır/50 sütun; sayfa başına yaklaşık
  2.000 karakter. Kayıtlı formül sonuçları okunur, formüller hesaplanmaz.
- CSV: en fazla 200 satır/50 sütun. UTF-8 beklenir.
- Dosya başına en fazla 12.000 karakter saklanır; her soruda tüm dosyalara
  pay ayıran yerel sözcük eşleştirmeyle en fazla 5.000 karakter seçilir.
  Bu yöntem tam belge taraması, finansal hesap motoru veya anlamsal arama değildir.
- Ayrıştırma öncesinde ZIP öğe/açılmış boyut kontrolleri vardır. Ayrıştırıcılar
  ayrı bir süreçte izole edilmediğinden kötü niyetli belgeler için tam koruma
  sağlanmaz; herkese açık ölçekli kullanım öncesinde süreç sınırları gerekir.

Uygulama konuşmaları kalıcı veritabanına yazmaz; oturum belleğinde en fazla
100 mesaj tutar. Yanıt için soru, sınırlı sohbet geçmişi ve seçilen dosya
kesitleri Groq'a aktarılır. Web araştırması ek hizmetlere veri aktarımı
içerebilir. Sağlayıcıların saklama politikaları ayrıca geçerlidir.
Dosya bağlamını kaldırmak eski sohbet mesajlarında bulunan alıntıları silmez.
Tüm oturum içeriğini temizleme yüklenen dosyaları ve sohbeti kaldırır.

## Sohbet bağlamı

Yan paneldeki 2.000 karakterlik **Sohbet notu** amaç, tercihler ve önemli
kararlar için kullanıcı tarafından yazılır. Ek bir özet/model isteği yapılmaz.
Not her soruda kullanıcı bağlamı olarak gönderilir; sistem talimatı değildir.
Sohbet temizlenince not da silinir. Oturumlar arasında kalıcı hafıza yoktur.

Geçmişteki soru/cevap turları bölünmeden seçilir. Önce yakın konuşma için
yer ayrılır, ardından soruyla sözcük eşleşmesi olan eski turlar seçilir.
Bu yöntem anlamsal hafıza değildir; bulunamayan eski bilgileri hatırlama
garantisi vermez. Bağlamdan çıkarılan mesajlar olduğunda modele sınır bildirilir.

## Araştırma ve kota

Araştırma yalnızca kullanıcı seçeneği açıkken istenir. `browser_search`
sağlayıcı tarafında çalışır; bu sürüm aramanın başarı kaydını bağımsız
doğrulamaz. Kaynak URL'lerini kontrol edin. Sabit nüfus yanıtı ve sahte
güncellik iddiası kaldırılmıştır. Kota dolduğunda doğrulanmamış yedek bilgi
üretilmez; soru tekrar denemek için korunur.

Yanıtta bildirilen en fazla 12 farklı HTTP(S) bağlantısı ayrıca kaynak
kaydında gösterilir ve JSON olarak indirilebilir. Kayıt zamanı, **yanıtın
kaydedildiği zamandır**; sayfaya erişim zamanı değildir. Yayın tarihi,
veri dönemi ve erişim zamanı bağımsız doğrulanmadığından boş bırakılır.
Bağlantı bulunamazsa araştırmanın doğrulanmış sayılmaması gerektiği belirtilir.
Bağlantılar sırf yanıtta yer aldıkları için güvenilir veya güncel kabul edilmez.
Kaynak kaydı sayfaları indirmez; başlıklar modelin kullandığı etiketlerdir.
URL filtresi bazı yerel/özel adresleri eler, DNS doğrulaması yapmaz ve bir
sunucu tarafı URL getirme güvenlik mekanizması olarak kullanılmamalıdır.

429 yanıtında `Retry-After` okunur (yoksa 60 saniye); aynı oturumda süre
dolmadan istek gönderilmez. Normal gönderimler arasında 5 saniye vardır.
Otomatik tekrar ve ilave özet API çağrısı yoktur. Bunlar oturum önlemleridir;
kuruluş düzeyindeki kotayı veya yeni oturum açarak sınır aşılmasını önlemez.
Kalıcı/global kota yönetimi sonraki aşamadadır. Karakter bütçesi token
sayımının yaklaşık bir karşılığıdır; kesin token sayacı değildir.

## Test

```sh
python -m unittest discover -s tests -v
```

Testler sahte anahtar, mock HTTP ve yerel örnek belgeler kullanır. Gerçek
Groq, e-posta veya ücretli işlem çağrısı yapmaz. Gerçek kaynak doğruluğu,
model cevap kalitesi ve mobil görsel değerlendirme ayrıca yapılmalıdır.

## Geri dönüş

Başlangıç sürümü: `1f5689ef1ce30ee58537de94fdcf89c3302c06d7`.
Değişiklikler geliştirme dalında tutulur; canlı uygulamaya otomatik geçiş
öngörülmez. Birleştirme sonrası sorun olursa PR commit'i revert edilerek
önceki sürüme dönülebilir. Secrets değerlerini değiştirmeye gerek yoktur.
