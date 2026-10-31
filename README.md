# Nesil AI

Türkçe öncelikli Streamlit asistanı. Bu sürüm sohbet, beş çalışma modu,
belgelerden sınırlı metin çıkarma, isteğe bağlı Groq web araştırması ve TXT
sohbet indirme sunar. Ayrıca gönderilmeyen e-posta taslağı indirme ve
tarayıcıdaki yerel seslerle son yanıtı dinleme araçları vardır. Bilgisayar
kontrolü, sunucuda kullanıcı kodu çalıştırma, gerçek e-posta gönderimi, görsel üretimi ve sesi
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
- PDF: ilk 200 sayfaya kadar metin; isteğe bağlı yerel OCR ilk 20 taranmış sayfada denenir.
- DOCX: ana metin ve sınırlı tablolar. Metin kutuları ve görseller okunmaz.
- Excel: ilk 20 sayfa, en fazla 2.000 satır/50 sütun; sayfa başına yaklaşık
  60.000 karakter. Kayıtlı formül sonuçları okunur, formüller hesaplanmaz.
- CSV: en fazla 5.000 satır/50 sütun. UTF-8 beklenir.
- Dosya başına en fazla 240.000 karakter saklanır; her soruda tüm dosyalara
  pay ayıran yerel sözcük eşleştirmeyle en fazla 10.000 karakter seçilir.
  Örtüşen kesitlerde sayfa/paragraf/satır veya karakter konumu korunur.
  Kısa devam sorularında önceki soru da belge kesiti seçiminde kullanılır.
  Bu yöntem tam belge taraması, finansal hesap motoru veya anlamsal arama değildir.
- Ayrıştırma öncesinde ZIP öğe/açılmış boyut kontrolleri vardır. Arayüzde
  belgeler ayrı süreçte okunur; 35 saniyede bitmeyen süreç durdurulur.
  Desteklenen Unix sistemlerinde 768 MB adres alanı ve 30 saniye CPU sınırı
  uygulanır. Windows'ta sert bellek sınırı yoktur. Bu, ağ ve dosya sistemi
  erişimi kapatılmış bir konteyner değildir; ölçekli kullanımda ek izolasyon gerekir.

Yerel OCR için `python -m pip install -r requirements-ocr.txt` çalıştırın;
ayrıca sunucuya Tesseract ve Türkçe/İngilizce dil verilerini kurun. Tesseract
PATH üzerinden bulunmalıdır. `NESIL_OCR_LANG` varsayılanı `tur+eng`.
Görüntüler OCR hizmetine yüklenmez. Eksik kurulum açıkça bildirilir;
OCR kullanılmadan normal metinli PDF'ler okunmaya devam eder. OCR gerçek
motor kurulumu ve tarama kalitesiyle ayrıca değerlendirilmelidir.

Supabase kimlik doğrulaması etkinleştirildiğinde kullanıcı hesapları, profil,
sohbet başlıkları, mesajlar ve kullanıcı tarafından kaydedilen hafıza kayıtları
Supabase'de kalıcı tutulur. İstekler kullanıcının JWT'siyle yapılır; satır düzeyi
güvenlik (RLS) kullanıcı kayıtlarını ayırır. Çıkış, sunucu tarafındaki oturum
bilgilerini temizler. Supabase ayarları yoksa veya NESIL_AUTH_BACKEND=legacy
seçilmişse eski kurum erişim kodu akışı kullanılabilir.

Genel sohbet, görev planlama ve belge modlarında soru, sınırlı sohbet geçmişi ve
seçilen dosya kesitleri Groq'a aktarılır. Kodlama ve matematik modlarında bu içerik,
uygulama aynı bilgisayarda çalışıyorsa yerel Ollama'ya gönderilir. Web araştırması
ek hizmetlere veri aktarımı içerebilir. Sağlayıcıların saklama politikaları ayrıca
geçerlidir. Dosya bağlamını kaldırmak daha önce kaydedilmiş sohbet mesajlarını
silmez. Sohbeti temizlemek yalnızca mevcut ekrandaki bağlamı sıfırlar; kalıcı
sohbeti silmek için kayıtlı sohbetler bölümündeki silme onayı kullanılmalıdır.
Kalıcı hafıza kullanıcı tarafından eklenebilir, düzenlenebilir ve silinebilir.

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

Araştırma yalnızca kullanıcı seçeneği açıkken istenir. Selamlaşma ve basit
hazır olma mesajlarında araç kullanımı kapatılır; diğer sorularda
`browser_search`, `tool_choice=auto` ile sunulur ve sistem talimatı arama
ister. Her mesaja zorunlu araç çağrısı eklenmez. Arama sağlayıcı tarafında
çalışır; gerçek araç sonucu bulunmadan başarı garantisi verilmez.
Kaynak URL'lerini kontrol edin. Sabit nüfus yanıtı ve sahte
güncellik iddiası kaldırılmıştır. Kota dolduğunda doğrulanmamış yedek bilgi
üretilmez; soru tekrar denemek için korunur.

Yanıtta bildirilen en fazla 12 farklı HTTP(S) bağlantısı ayrıca kaynak
kaydında gösterilir ve JSON olarak indirilebilir. Kayıt zamanı, **yanıtın
kaydedildiği zamandır**; sayfaya erişim zamanı değildir. Kaynak kontrolü
yapılmadıkça yayın tarihi, veri dönemi ve erişim zamanı boş bırakılır.
Bağlantı bulunamazsa ayrıntılı araştırma yanıtı yayımlanmaz; kaynak elde
edilemediğini açıklayan yanıt gösterilir. Sağlayıcı döndürürse `executed_tools`
ve `annotations` içindeki açık URL, kaynak kimliği ve kesitler de işlenir.
Kaynak numarası liste sırasından tahmin edilmez. Kimliği bağlantıyla
eşleştirilemeyen `【…†…】` / `〖…†…〗` işaretleri açık uyarıya dönüştürülür.
Sağlayıcı metadata şeması bilinmiyorsa eşleştirme yapılmaz; canlı Groq
yanıtlarıyla uyumluluk ayrıca kontrol edilmelidir.
Bağlantılar sırf yanıtta yer aldıkları için güvenilir veya güncel kabul edilmez.
Bağlantı başlıkları modelin kullandığı etiketlerdir; sayfa başlığı değildir.

**Kaynak sayfalarını kontrol et** düğmesi, ilk üç bağlantıyı isteğe bağlı
olarak açmayı dener. Her oturumda kontroller arasında 60 saniye vardır;
sayfalar normal ekran yenilenmelerinde tekrar indirilmez. Kaynak URL'si
ilgili siteye gönderilir; API anahtarı, kullanıcı çerezi veya sohbet
geçmişi gönderilmez. Ek model çağrısı yapılmaz.

Yalnızca HTTPS/443, Türkiye `.gov.tr` adresleri ve `source_reader.py`
içindeki sınırlı birincil kaynak listesi desteklenir. Yönetici kurumun
sitesini `NESIL_SOURCE_HOSTS=kurum.example,www.kurum.example` ortam
değişkeniyle tam alan adı olarak ekleyebilir; alt alan adları otomatik
açılmaz. Tüm DNS cevapları
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
Metin alındıktan sonra **Yanıtı kaynak metniyle karşılaştır** düğmesiyle
önceki yanıt ve en fazla üç kaynak kesiti modele gönderilebilir. Bu ek model
çağrısı ortak kotaya dahildir. Desteklenen, çelişen ve kesitte bulunmayan
iddialar ayrılır; inceleme tam sayfa veya bağımsız doğruluk garantisi değildir.
`verified` alanı false kalır: sayfaya erişim, yanıttaki iddiayı veya en
güncel veriyi doğrulamaz. JavaScript, PDF/OCR ve JSON-LD tarihleri bu
okuyucuda işlenmez. Bot engeli ve yönlendirme olan sayfalar okunamayabilir.

`research.public_url` yalnızca bağlantı kaydı filtresidir; tek başına
sunucu tarafı URL getirme güvenlik mekanizması olarak kullanılmamalıdır.

Teknik dayanak: [OWASP SSRF önleme](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html),
[Python TLS](https://docs.python.org/3/library/ssl.html).

HTTP hatalarında ham sağlayıcı metni, soru veya anahtar loglanmaz. İzin
verilen hata kategorisi, HTTP kodu ve rastgele hata kimliği yönetici loguna
yazılır. Araç, bağlam ve geçici hizmet hataları ayrı açıklanır; her 400
hatası mesaj uzunluğuna bağlanmaz.

429 yanıtında `Retry-After` okunur (yoksa 60 saniye); bekleme SQLite içinde
sunucudaki oturumlarla paylaşılır. Normal gönderimler arasında 5 saniye
vardır. Otomatik tekrar veya ücretli yedek modele geçiş yoktur.

## Kurum girişi ve ortak kullanım sınırları

İsteğe bağlı küçük ekip girişi için Streamlit Secrets içine aşağıdaki
tabloyu ekleyin. Her kullanıcıya farklı, rastgele en az 16 karakterlik
erişim kodu verin; örneği gerçek kullanımda değiştirmeden kullanmayın.

```toml
[NESIL_USERS]
ayse = "BURAYA-UZUN-RASTGELE-KOD-YAZIN"
```

Alternatif: `NESIL_USERS_JSON` ortam değişkeninde aynı kullanıcı/kod
eşleştirmesi. Yapılandırılmazsa mevcut herkese açık kullanım korunur;
tüm anonim kullanıcılar aynı günlük kullanıcı kotasını paylaşır.
Kodlar sunucu sırrıdır, modele gönderilmez. Girişten önce dosya yükleme
ve sohbet ekranı açılmaz. Çıkış oturum içeriğini temizler. Bu küçük ekip
erişim kapısıdır; SSO/MFA, hesap kurtarma ve kurumsal kimlik hizmeti değildir.
Sunucu genelinde beş dakikada en fazla 20 giriş denemesi yapılabilir.

SQLite kaydı soru, belge, erişim kodu veya yanıt saklamaz; günlük sayaç,
kullanıcı kimliğinin özeti ve sağlayıcı beklemesini saklar. Günlük sınırlar
UTC'ye göre yenilenir. Varsayılanlar ortam değişkenleriyle ayarlanır:

| Ayar | Varsayılan |
| --- | --- |
| `NESIL_USAGE_DB` | `.nesil-ai/usage.sqlite3` |
| `NESIL_DAILY_REQUESTS` | 500 ortak istek/gün |
| `NESIL_USER_DAILY_REQUESTS` | 100 istek/kullanıcı/gün |
| `NESIL_DAILY_TOKENS` | 150.000 token bütçesi/gün |

Uygulama ücretsiz kullanım için ortak 20 istek/dakika ve 7.500 tahmini
token/dakika sınırı uygular. Günlük ayarlar en fazla 1.000 istek ve
200.000 token olabilir; ortam değişkenleri bunları yükseltemez.
Model çıktısı 1.200 token ile sınırlıdır. Soru, sistem, not, geçmiş ve dosya
kesitleri yaklaşık 5.100 UTF-8 byte giriş bütçesine sığdırılır. Not ve soru
tek başına sığmıyorsa API isteği gönderilmez; dosya kesitleri ve geçmiş
kontrollü kısaltılır. Byte bütçesi kesin model token sayacı değildir.

30 Ekim 2026'da kontrol edilen [Groq ücretsiz plan sınırları](https://console.groq.com/docs/rate-limits)
GPT-OSS 120B için 30 istek/dakika, 1.000 istek/gün, 8.000 token/dakika ve
200.000 token/gün bildiriyor. Gerçek kuruluş sınırları farklı olabilir;
Groq Console Limits sayfasındaki değerler geçerlidir. Kota dolunca beklenir;
otomatik tekrar, başka sağlayıcıya geçiş, ücretli plan yükseltme veya ödeme
işlemi yapılmaz. OCR, seslendirme ve Python Mini yerel çalışır.

**Groq hesabı Free planda olmalıdır.** Uygulama API anahtarından hesabın
faturalama planını doğrulayamaz; aynı sınırlar ücretli Developer anahtarıyla
kullanıldığında ücret oluşmasını engellemez. [Groq faturalama açıklaması](https://console.groq.com/docs/billing-faqs).

İstekten önce aynı işlem içinde kota ayrılır; eşzamanlı kullanıcılar ve yeni
tarayıcı oturumları ortak istek sınırını aşamaz. Token tahmini UTF-8 byte
sayısı, çıktı payı ve araştırma payıyla yapılır; yanıtın `total_tokens`
değeri varsa sonradan uzlaştırılır. Sağlayıcının iç arama tokenları tahmini
aşabilir; bu kesin parasal harcama garantisi değildir. Groq hesabında da
harcama sınırı ayarlayın. Başarısız/usage döndürmeyen isteklerde ayrılan
bütçe korunur. Kota kaydına erişilemiyorsa model isteği gönderilmez.

Kalıcı bir `NESIL_USAGE_DB` yolu kullanın. Geçici dosya sistemi yeniden
kurulumda sayaçları kaybeder. Birden çok sunucu/replica için ortak işlemli
veritabanı gerekir; ayrı SQLite dosyaları ortak kota sağlamaz.

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

## Python Mini (deneysel)

İsteğe bağlı tarayıcı paneli kısa MicroPython kodlarını çalıştırır ve küçük
TXT/CSV/JSON sonuçlarını indirir. Groq çağrısı veya ücretli çalışma servisi
kullanmaz. Tam Python kütüphaneleri desteklenmez; tarayıcının toplam bellek
ve CPU kullanımı için sert kota garanti edilmez. Yalnızca gözden geçirilmiş
kodlar içindir. [Sınırlar, veri akışı ve lisans](PYTHON_MINI.md).

## Testleri çalıştırma

```sh
python -m unittest discover -s tests -v
```

Windows/Python 3.12 üzerinde 98 test doğrulandı. Ayrıca yerel Tesseract
ve pypdfium2 ile bir sayfalık sentetik taranmış PDF'deki `98765 TL` ifadesi
ayrı süreç üzerinden okundu. OCR, harfleri yanlış okuyabilir; gerçek belge
ve farklı tarama kaliteleriyle ayrıca değerlendirilmelidir.

Testler sahte anahtar, mock HTTP ve yerel örnek belgeler kullanır. Gerçek
Groq, e-posta veya ücretli işlem çağrısı yapmaz. Gerçek kaynak doğruluğu,
model cevap kalitesi ve mobil görsel değerlendirme ayrıca yapılmalıdır.

## Geri dönüş

Başlangıç sürümü: `1f5689ef1ce30ee58537de94fdcf89c3302c06d7`.
Değişiklikler geliştirme dalında tutulur; canlı uygulamaya otomatik geçiş
öngörülmez. Birleştirme sonrası sorun olursa PR commit'i revert edilerek
önceki sürüme dönülebilir. Secrets değerlerini değiştirmeye gerek yoktur.


## Yerel yapay zekâ: Ollama (isteğe bağlı)

Kodlama ve Matematik Öğretmeni modları isteğe bağlı yerel Ollama sağlayıcısını kullanır.
Genel yardımcı, görev planlama ve belge modları mevcut Groq sağlayıcısını kullanmaya devam eder.
app.py içindeki yönlendirme kodlama ve matematik modlarını doğrudan Ollama'ya gönderir;
diğer modlar mevcut kota denetimli Groq akışında kalır. Yerel sağlayıcı etkin değilse
kodlama/matematik modları açıkça yapılandırma uyarısı verir. Bu modlarda internet
araştırması devre dışıdır; Groq'a otomatik geçiş veya ücretli yedek çağrı yapılmaz.

Windows bilgisayarında Ollama kurulduktan sonra PowerShell'de:

```powershell
ollama pull qwen2.5-coder:3b
ollama pull qwen3:4b
```

Nesil AI uygulamasını aynı bilgisayarda yerel olarak çalıştırırken ortam değişkenleri:

```powershell
$env:NESIL_LOCAL_MODEL_ENABLED="true"
$env:OLLAMA_BASE_URL="http://127.0.0.1:11434"
$env:NESIL_OLLAMA_CODING_MODEL="qwen2.5-coder:3b"
$env:NESIL_OLLAMA_MATH_MODEL="qwen3:4b"
python -m streamlit run app.py
```

Ollama HTTP servisi varsayılan olarak 127.0.0.1:11434 adresinde dinler.
**Önemli dağıtım sınırı:** Streamlit Cloud üzerindeki uygulamanın 127.0.0.1 adresi
kullanıcının ev bilgisayarı değil, bulut sunucusudur. Kişisel bilgisayardaki Ollama'yı
kullanmak için Nesil AI uygulaması da o bilgisayarda çalıştırılmalıdır. Uzak erişim
için güvenli, kimlik doğrulamalı ağ geçidi ayrıca tasarlanmalı; Ollama portu internete
doğrudan açılmamalıdır.

Mevcut bilgisayardaki 8 GB RAM ve 4 GB ekran kartı belleği nedeniyle bu modellerin
yanıt süresi yavaş olabilir. Önce 3B kodlama modelini deneyin; iki modeli aynı anda
yüklemeyin. Matematik modeli ayrıca indirildiğinde kullanılabilir. Model indirme ve
çalıştırma gerçek bilgisayarda ayrıca doğrulanmalıdır.


## Supabase ile kalıcı kullanım kotası ve veri altyapısı

Geliştirme dalında Supabase/PostgreSQL desteği isteğe bağlıdır. SQLite yerel
geliştirme için varsayılan kalır. Supabase'e geçmeden önce
`supabase/migrations/202610310001_initial_schema.sql` dosyasını Supabase SQL
Editor üzerinden uygulayın. Ardından sunucu ortamında şu değişkenleri tanımlayın:

- `NESIL_STORAGE_BACKEND=supabase`
- `SUPABASE_URL=https://YOUR-PROJECT.supabase.co`
- `SUPABASE_SERVICE_ROLE_KEY=...`

Service-role anahtarını yalnızca Streamlit Secrets veya sunucu ortamında tutun;
asla GitHub'a, tarayıcıya veya kullanıcıya göstermeyin. Uygulama RPC üzerinden
atomik kota ayırır ve sonuçları uzlaştırır. Supabase ayarı eksikse kota kaydı
başarısız olur ve model çağrısı yapılmaz. Yerel geliştirmede
`NESIL_STORAGE_BACKEND=sqlite` kullanılabilir.

Migration ayrıca kullanıcı profili, konuşma, mesaj ve kullanıcıya ait hafıza
tablolarını RLS açık şekilde hazırlar. Henüz sohbet/hafıza tablolarına yazma
ve Supabase Auth arayüzü bağlanmış değildir; bu tablolar sonraki aşama için
şemadır. İstemci rolleri için hiçbir okuma/yazma politikası açılmaz. Gerçek
kullanıcı kimliği, oturum ve kullanıcı onaylı hafıza akışı bağlanmadan bu
tablolar kullanılmamalıdır. Supabase Auth entegrasyonu ve veri silme
akışları ayrı test edilmeden kalıcı sohbet etkinleştirilmez.


### Supabase Auth (geliştirme aşaması)

E-posta/şifre girişini etkinleştirmek için Streamlit Secrets içine ayrıca
`SUPABASE_ANON_KEY` (veya `SUPABASE_PUBLISHABLE_KEY`) ekleyin.
Ardından `NESIL_AUTH_BACKEND=supabase` ayarını kullanın. Supabase Dashboard
üzerinde Authentication > Providers > Email ayarları ve e-posta doğrulama
seçenekleri yönetilmelidir. Public/anon anahtar kullanıcı istemcilerinde
kullanılmak üzere tasarlanmıştır; service-role anahtarı yalnızca sunucuda
kalmalıdır.

Yeni `202610310002_auth_rls_policies.sql` migration dosyası, ilk şema
migration'ından sonra SQL Editor'de ayrıca uygulanmalıdır. Bu migration
profiller, sohbetler, mesajlar ve hafıza kayıtları için kullanıcı sahipliği
RLS politikalarını hazırlar. **Bu aşamada sohbet ve hafıza kayıtlarının
PostgreSQL'e kaydedilmesi henüz uygulamaya bağlanmamıştır.** Giriş ekranı ve
çıkış akışı eklenmiştir; kalıcı sohbet CRUD, token yenileme ve kullanıcı
kontrollü hafıza akışı tamamlanıp test edilmeden bu özellikler kullanılabilir
olarak kabul edilmemelidir. Geliştirme dalı varsayılan olarak eski erişim
kapısını korur; Supabase Auth ancak `NESIL_AUTH_BACKEND=supabase`
olarak açıkça seçilirse etkinleşir.
