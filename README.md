# Nesil AI

Türkçe öncelikli Streamlit asistanı. Bu sürüm sohbet, dört çalışma modu,
belgelerden sınırlı metin çıkarma, isteğe bağlı Groq web araştırması ve TXT
sohbet indirme sunar. Ayrıca gönderilmeyen e-posta taslağı indirme ve
tarayıcıdaki yerel seslerle son yanıtı dinleme araçları vardır. Bilgisayar
kontrolü, kod çalıştırma, gerçek e-posta gönderimi, görsel üretimi ve sesi
yazıya çevirme henüz uygulanmamıştır; `ROADMAP.md` aşamalarını izleyin.

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
kaydedildiği zamandır**; sayfaya erişim zamanı değildir. Kaynak kontrolü
yapılmadıkça yayın tarihi, veri dönemi ve erişim zamanı boş bırakılır.
Bağlantı bulunamazsa araştırmanın doğrulanmış sayılmaması gerektiği belirtilir.
Bağlantılar sırf yanıtta yer aldıkları için güvenilir veya güncel kabul edilmez.
Bağlantı başlıkları modelin kullandığı etiketlerdir; sayfa başlığı değildir.

**Kaynak sayfalarını kontrol et** düğmesi, ilk üç bağlantıyı isteğe bağlı
olarak açmayı dener. Her oturumda kontroller arasında 60 saniye vardır;
sayfalar normal ekran yenilenmelerinde tekrar indirilmez. Kaynak URL'si
ilgili siteye gönderilir; API anahtarı, kullanıcı çerezi veya sohbet
geçmişi gönderilmez. Ek model çağrısı yapılmaz.

Yalnızca HTTPS/443, Türkiye `.gov.tr` adresleri ve `source_reader.py`
içindeki sınırlı birincil kaynak listesi desteklenir. Tüm DNS cevapları
genel adres olmalıdır; bağlantı seçilen sayısal adrese sabitlenir, TLS
alan adı ve sertifika kontrolü korunur. Proxy/çerez/kimlik bilgisi eklenmez.
Yönlendirmeler izlenmez. Yalnızca HTML/düz metin, sıkıştırılmamış en fazla
512 KB yanıt desteklenir. Soket zaman aşımı 3 saniye, gövde okuma bütçesi
5 saniyedir. DNS ve başlık okuması dahil katı bir toplam süre garantisi
yoktur; işletim sistemi ve ağ koşulları süreyi etkileyebilir. Bu kontroller
ağ seviyesinde izolasyonun veya bağımsız güvenlik denetiminin yerini tutmaz.

Metin alınırsa gerçek erişim zamanı, sayfa başlığı ve sınırlı kesit kayda
eklenir. Yayın tarihi yalnızca açık yayın metadata alanlarından alınır;
gövde içindeki tarihlerden tahmin edilmez. Veri dönemi yalnızca açık
temporal metadata varsa alınır. Çelişen yayın tarihleri olduğunda tarih
seçilmez. Alanlar sayfanın iddialarıdır; bağımsız gerçeklik doğrulaması
değildir. Sayfa metni düz metin gösterilir, modele otomatik gönderilmez.
`verified` alanı false kalır: sayfaya erişim, yanıttaki iddiayı veya en
güncel veriyi doğrulamaz. JavaScript, PDF/OCR ve JSON-LD tarihleri bu
okuyucuda işlenmez. Bot engeli ve yönlendirme olan sayfalar okunamayabilir.

`research.public_url` yalnızca bağlantı kaydı filtresidir; tek başına
sunucu tarafı URL getirme güvenlik mekanizması olarak kullanılmamalıdır.

Teknik dayanak: [OWASP SSRF önleme](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html),
[Python TLS](https://docs.python.org/3/library/ssl.html).

429 yanıtında `Retry-After` okunur (yoksa 60 saniye); aynı oturumda süre
dolmadan istek gönderilmez. Normal gönderimler arasında 5 saniye vardır.
Otomatik tekrar ve ilave özet API çağrısı yoktur. Bunlar oturum önlemleridir;
kuruluş düzeyindeki kotayı veya yeni oturum açarak sınır aşılmasını önlemez.
Kalıcı/global kota yönetimi sonraki aşamadadır. Karakter bütçesi token
sayımının yaklaşık bir karşılığıdır; kesin token sayacı değildir.

## E-posta taslağı ve seslendirme

Yan panelde **E-posta taslağı** bölümünden tek alıcı (isteğe bağlı), konu ve
ileti metni girilip `.eml` dosyası indirilebilir. Son yanıt kullanıcı düğmesiyle
ileti metnine alınabilir. Dosyada `X-Unsent: 1` vardır; taslak olarak açılışı
e-posta programına bağlıdır. Hiçbir SMTP/OAuth bağlantısı veya otomatik
gönderim yapılmaz. Taslak alanları modele gönderilmez ve sohbet temizlenince
silinir. Konu/alıcı başlıklarında kontrol karakterleri reddedilir. Standart
tek ASCII adres desteklenir; görünen ad ve çoklu alıcı desteklenmez.
Alanlar tek formda birlikte gönderilir; hazırlama sonrasında alıcı, konu ve
ileti salt okunur önizlemede gösterilir. **Taslağı düzenle** ile forma geri
dönülür ve önceki indirme kaldırılır. Düzenlenen taslak yeniden hazırlanır.

**Son yanıtı dinle** bölümünde denetimler kullanıcı seçimiyle açılır ve ses
yalnızca Dinle düğmesine basıldığında başlar. Tarayıcının `localService=true`
olarak bildirdiği sesler listelenir, varsa Türkçe ses öne alınır. Böyle bir
ses yoksa uzak ses hizmetine otomatik geçilmez. Durdur düğmesi vardır.
İlk 8.000 karakter seslendirilir; uzun yanıtlar için sınır gösterilir.
Ek model veya ücretli ses API çağrısı yoktur. Türkçe ses kalitesi, cihaz
dil paketleri ve tarayıcı desteği değişebilir. Mikrofon kaydı veya ses dosyası
üretimi yapılmaz. Gerçek cihazda ses çıkışı ayrıca doğrulanmalıdır.

Ses denetimleri sabit bir HTML/JS bileşenidir; yanıt metni yalnızca base64
veri olarak geçirilip konuşma metni şeklinde kullanılır. Kullanıcı veya
model yanıtı HTML/JavaScript kodu olarak yerleştirilmez. Bileşen içindeki ağ
istekleri CSP ile kapalıdır. Yeni Streamlit sürümlerinde `st.iframe`, 1.40
uyumluluğu için eski HTML iframe adaptörü kullanılır.

Kaynaklar: [Web Speech yerel ses özelliği](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesisVoice/localService),
[Streamlit iframe](https://docs.streamlit.io/develop/api-reference/text/st.iframe).

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
