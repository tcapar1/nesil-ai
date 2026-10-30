# Python Mini

Kullanıcının açıp Çalıştır'a bastığı, deneysel tarayıcı aracı. Model otomatik
kod çalıştırmaz. Kod düzenleyicisi ve çıktı Streamlit widget'ı değildir;
bu araç kodu/çıktıyı uygulama sunucusuna veya model sağlayıcısına göndermez.
Son asistan mesajındaki Python bloğu başlangıç metni olabilir; sohbetin
model sağlayıcısına gönderilmesi uygulamanın normal sohbet akışına bağlıdır.

## Sınırlar

- MicroPython alt kümesi; CPython, pip, NumPy/Pandas ve sistem komutu yok.
- En fazla 20.000 karakter kod, 5 saniye çalıştırma, 16 KB standart çıktı.
- Python heap 2 MB; WebAssembly doğrusal belleği en fazla 32 MB.
- En fazla 5 UTF-8 TXT/CSV/JSON dosyası; dosya başına 64 KB, toplam 128 KB.
- Sanal `/out` dizini; her çalıştırmada yeni çalışma alanı. Gerçek cihaz
  dosyaları, yüklenen belgeler, sohbet geçmişi ve Secrets aktarılmaz.
- İndirme kullanıcı düğmesiyle olur. Sayfa yenilenince geçici sonuçlar silinir.

Bu, düşmanca kod için sunucu konteyneri seviyesinde bir izolasyon değildir.
MicroPython'ın JavaScript köprüsü vardır; WASM sınırı JavaScript nesnelerinin
ve tüm tarayıcı işleminin belleğini sınırlamaz. Worker/iframe izolasyonu
tarayıcı güvenliğine dayanır. Yalnızca incelenmiş kısa kodlar içindir.
Ön plandaki denetleyici 5 saniye sonunda worker çalışma alanını kapatır;
tarayıcı aşırı yük veya arka plan zamanlayıcı kısıtlaması mutlak süreyi etkileyebilir.

## İzolasyon ve veri akışı

Güvenilen denetleyici sabit URL'lerden motoru indirir ve SHA-256 doğrular.
WASM bellek tanımı beklenen yapıdaysa maksimumu 512 sayfaya düşürür;
beklenmeyen sürüm/bellek yapısında çalıştırmayı reddeder. İndirme önbelleği
yalnızca motor dosyaları içindir; kullanıcı kodu önbelleğe alınmaz.

Motor yalnızca `sandbox="allow-scripts"` olan, aynı köken izni verilmeyen
iç iframe'in dedicated worker'ında çalışır. İç CSP dış bağlantıya izin
vermez (`connect-src blob:`); worker/modül yükleme yalnızca blob'dandır.
Denetleyici mesaj kaynağını, opaque origin'i, iş kimliğini ve çıktı
boyut/türünü kontrol eder. Metin HTML olarak yorumlanmaz. Durdur düğmesi
ve zaman aşımı çalışma alanını kaldırır. Sunucuda eval/exec/subprocess yoktur.

İlk çalıştırma jsDelivr'a motor dosyası isteği yapar; CDN bağlantının IP ve
standart HTTP metaverisini görebilir. Kod, sohbet ve anahtar bu isteğe eklenmez.
CDN yoksa panel hata verir; model kotası kullanmaz. Tam çevrimdışı çalışması
veya her tarayıcıda desteği garanti edilmez. HTTPS ya da localhost gerekir.

## Bağımlılık ve lisans

Resmî paket: `@micropython/micropython-webassembly-pyscript@1.29.0-6`.
URL, paket SHA-512 ve indirilen iki dosyanın SHA-256 değerleri
`runner_runtime.json` içindedir. Otomatik sürüm güncellemesi yapılmaz.
Orijinal motor dosyaları kaynak depoya eklenmez. MicroPython ve gömülü
bileşenlerinin bildirimleri [MICROPYTHON-LICENSE.txt](MICROPYTHON-LICENSE.txt)
dosyasındadır; [resmî kaynak](https://github.com/micropython/micropython/tree/v1.29.0/ports/webassembly).

Tam CPython için gelecekte kullanıcı başına geçici konteyner/VM, ağ ve
çekirdek düzeyinde kaynak sınırları olan ayrı servis gerekir. Bu araç
mevcut Streamlit sunucusunda kullanıcı kodu çalıştırmaya geçiş yapmaz.
