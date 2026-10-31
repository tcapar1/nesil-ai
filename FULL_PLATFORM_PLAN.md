# Nesil AI — Tam Kapsamlı Platform Yol Haritası

Bu plan `feature/full-platform-20261031` dalında yürütülür. `main` ve Streamlit canlı dağıtımı, açıkça onaylanmış yayın adımına kadar değiştirilmez.

## Ürün hedefi

Türkçe öncelikli; web ve mobil uyumlu; kullanıcı hesabı, özel veri alanı, çoklu yapay zekâ sağlayıcısı, belge/araştırma/üretkenlik araçları ve yönetilebilir kullanım kotası olan modüler bir kişisel ve ekip yapay zekâ platformu.

## İlkeler ve yayın kapıları

- Her geliştirme ayrı, küçük ve geri alınabilir commit/PR ile yapılır.
- Gerçek API, ücretli işlem, e-posta gönderimi, dosya silme, bilgisayar kontrolü veya dış sisteme yazma kullanıcı onayı olmadan yapılmaz.
- API anahtarları yalnızca sunucu sırlarında tutulur; service-role anahtarı hiçbir zaman istemciye veya kullanıcı verisine çıkmaz.
- Kullanıcı verileri JWT + RLS ile ayrılır; yönetici yetkisi yalnızca sunucu tarafı allowlist/rol politikasıyla verilir.
- Testler mock/sentetik veriyle yürütülür; gerçek kullanıcı verisi veya ücretli API gerektiren testler ayrıca onaylanır.
- Her aşamada otomatik test, güvenlik kontrolü, mobil/masaüstü kontrolü ve geri dönüş notu gerekir.
- Başarısız veya eksik doğrulama varsa PR taslak kalır; canlıya alınmaz.

## Aşama 0 — Koruma ve mevcut durum denetimi

- [x] Main commit'inden yedek dal oluşturuldu: `backup/pre-full-platform-20261031`
- [x] Aynı commit'ten geliştirme dalı oluşturuldu: `feature/full-platform-20261031`
- [x] Main ile geliştirme dalı karşılaştırıldı; yedek dal ve taslak PR doğrulandı.
- [x] Supabase tabloları, RLS sahiplik politikaları, SECURITY DEFINER RPC yetkileri ve auth kullanıcı oluşturma tetikleyicisi salt okunur olarak denetlendi.
- [x] CI testleri Windows ve Ubuntu üzerinde geçti; testler mock/sentetik veri kullandı.
- [ ] Streamlit Cloud Secrets değerleri kullanıcı arayüzünde doğrulanmalı; gizli değerler istenmemeli veya loglanmamalı.
- [x] Canlı Supabase'de beklenen tablolar mevcut; migration geçmişi boş olduğundan başlangıç migration'ları körlemesine yeniden uygulanmayacak. Şema/migration geçmişi uzlaştırması ayrı kontrollü iş olarak kaydedildi.
- [ ] Supabase Auth leaked-password protection ayarı etkinleştirilmeli; yönetim arayüzünde doğrulanmadan tamamlandı sayılmayacak.

## Aşama 1 — Hesap ve kullanıcı alanı

### Mevcut teslimat durumu (2026-10-31)

- [x] Supabase e-posta/parola kayıt ve giriş ekranı, çıkış ve token yenileme.
- [x] Şifre sıfırlama e-postası isteği (e-posta bağlantısının gerçek cihazda tamamlanması henüz doğrulanmadı).
- [x] Profil görüntüleme/güncelleme; eski hesaplar için profil upsert.
- [x] Kalıcı sohbet oluşturma, listeleme, mesaj yükleme/kaydetme ve silme.
- [x] Yeni mesaj sonrası sohbet etkinlik zamanını yenileme.
- [x] Kullanıcı kontrollü hafıza ekleme, düzenleme ve silme.
- [x] CI mock testleri Windows ve Ubuntu üzerinde geçti; son commit için yeni CI çalışması sürüyor.
- [ ] İki ayrı gerçek test hesabıyla RLS izolasyonu ve e-posta akışını staging üzerinde doğrulama.
- [ ] Şifre sıfırlama bağlantısının dönüş/şifre yenileme ekranı uçtan uca doğrulaması.
- [ ] Kullanıcı verisi dışa aktarma ve hesap/veri silme talep akışı.

- E-posta/parola kayıt, giriş, çıkış, e-posta doğrulama ve şifre sıfırlama.
- Oturum yenileme, süresi dolmuş oturum yönetimi, oturumların kapatılması.
- Profil, görünen ad, dil, tema ve tercih ayarları.
- Kullanıcıya özel sohbet, dosya, hafıza ve ayar kayıtları.
- Veri dışa aktarma, hesap/veri silme talebi ve RLS izolasyon testleri.
- İsteğe bağlı ekip/kurum, davet, rol ve yetki modeli.

Kabul: İki test kullanıcısı birbirinin sohbetini, hafızasını, dosyasını veya ayarını okuyamaz/değiştiremez.

## Aşama 2 — Yapay zekâ motoru ve sohbet

### Sohbet yönetimi teslimatı (2026-10-31)

- [x] Sohbet başlığına göre arama/filtreleme ve yeniden adlandırma.
- [x] Sohbetleri sabitleme ve arşivleme; arşivlenmiş sohbetleri ayrı görünümde listeleme.
- [x] Pin/arşiv alanları için geriye uyumlu additive SQL migration ve taze kurulum şeması güncellemesi.
- [x] Bayrak güncellemelerinde izin verilen alanlar ve kullanıcı JWT/RLS sınırları.
- [x] Sohbet organizasyonu işlemleri için mock testler.
- [ ] Migration'ı ayrı staging projesinde uygulayıp eski/yeni sohbetlerle doğrula.
- [ ] Klasörler, etiketler ve toplu taşıma.

- [x] Kalıcı sohbet başlıklarını arama/filtreleme.
- [x] Sohbet başlığını kullanıcı tarafından yeniden adlandırma.
- [x] Başlık güncelleme metodunda kimlik ve uzunluk doğrulaması; mock test.
- [ ] Sabitleme, arşivleme ve klasörler.
- [ ] Sağlayıcı/model seçimi ve yetenek görünümü.
- [ ] Akışlı yanıt, durdurma ve güvenli yeniden deneme.

- Sağlayıcı adaptörleri ve model kataloğu: Groq, yerel Ollama; ek sağlayıcılar yalnızca yapılandırma ve kullanıcı onayıyla.
- Sağlayıcı/model seçimi, yetenek bildirimi, hata ve kota görünürlüğü.
- Akışlı yanıt, iptal etme, yeniden deneme, yanıtı düzenleyerek tekrar gönderme.
- Sohbet başlıkları, arama, sabitleme, arşivleme, klasörler ve dışa aktarma.
- Sohbet başına sistem talimatı/özel yönerge ve bağlam ayarları.
- Token/kullanım tahmini, sağlayıcı limitleri ve harcama korumaları.
- Uzun konuşma için ölçülebilir bağlam seçimi ve kullanıcı kontrollü hafıza.

Kabul: Sağlayıcı hatası kullanıcı mesajını kaybettirmez; kullanıcı onayı olmadan ücretli modele geçilmez.

## Aşama 3 — Belge ve bilgi çalışma alanı

### İlk belge kitaplığı teslimatı (2026-10-31)

- [x] Özel Supabase Storage istemcisi: kullanıcı JWT'siyle yükleme, listeleme, indirme ve silme.
- [x] Her kullanıcı için UUID klasörü ve Storage RLS sahiplik politikaları.
- [x] Özel bucket migration dosyası eklendi; mevcut canlı projede bucket olmadığı salt okunur kontrol edildi.
- [x] Uygulamada özel kitaplık görünümü, indirme ve silme kontrolleri eklendi.
- [x] Kitaplıktaki kayıtlı dosyayı doğrudan belge analiz alanına alma eklendi.
- [x] Dosya başına 10 MB, en fazla 5 dosya ve toplam 20 MB sınırı.
- [x] Storage istemcisi için mock testler eklendi.
- [ ] Storage migration'ını önce ayrı staging ortamında uygulayıp RLS ve dosya yaşam döngüsünü test et.
- [ ] Canlı projede migration ancak yedek, staging doğrulaması ve ayrı yayın onayı sonrası uygulanabilir.
- [ ] Belge meta verisi, etiket/klasör ve kullanıcıya özel arama.
- [x] Dosya kitaplığından seçilen dosyayı doğrudan belge çıkarma/sohbet akışına yükleme.
- [ ] OCR, büyük dosya ve belge kaynak konumu testleri.

- PDF, DOCX, XLSX, CSV, TXT, Markdown, görsel ve desteklenen sunum dosyaları.
- Sayfa/satır/hücre kaynak konumu; alıntı ve belgeye geri dönme.
- OCR, tablo çıkarımı, özet, karşılaştırma, soru-cevap ve yapılandırılmış veri çıkarma.
- Büyük belgelerde arka plan işi, ilerleme, iptal ve sınırlar.
- Kullanıcıya özel belge kitaplığı, etiketler, klasörler ve silme.
- Vektör/anlamsal arama ancak RLS, kaynak gösterimi ve silme zinciri doğrulandıktan sonra.

Kabul: Yanıtın dayandığı belge ve konum gösterilir; okunamayan içerik okunmuş gibi sunulmaz.

## Aşama 4 — Araştırma ve kaynak doğrulama

- Web araştırması, kaynak listesi ve kaynak metni inceleme.
- Kaynak tarihi, erişim zamanı ve veri dönemi alanlarını birbirinden ayırma.
- Çelişkili kaynakları yan yana gösterme; iddia/kanıt tablosu.
- Prompt injection ve güvenilmeyen web içeriği savunmaları.
- Kaynak bulunamadığında açık başarısızlık; doğrulanmayan bilgiye doğrulandı etiketi vermeme.

Kabul: Her önemli güncel iddia izlenebilir kaynakla ilişkilendirilir; sayfa erişimi tek başına doğrulama sayılmaz.

## Aşama 5 — Üretkenlik araçları

- E-posta taslağı ve bağlanan e-posta hesabında önce salt okunur arama.
- Takvim okuma, etkinlik taslağı ve onaylı oluşturma/değiştirme.
- Görev listesi, notlar, hatırlatmalar ve proje alanı.
- Excel/CSV analizleri, grafikler ve rapor üretimi.
- Word/PDF/sunum çıktıları ve şablonlar.
- Dış sistemlere yazma/gönderme öncesi alıcı, içerik ve işlem özeti + açık onay.

Kabul: Taslak ve gerçek gönderim birbirinden net ayrılır; hiçbir dış işlem sessizce yapılmaz.

## Aşama 6 — Ses, görsel ve çok modlu kullanım

- Görsel yükleme ve görsel anlama.
- Görsel üretimi/düzenleme için sağlayıcı adaptörü ve maliyet/onay kontrolü.
- Mikrofonla konuşma, konuşmayı yazıya çevirme ve yanıtı seslendirme.
- Kullanıcı denetimli başlat/durdur, veri saklama ve silme açıklamaları.
- Mobil tarayıcı ve cihaz uyumluluk testleri.

Kabul: Mikrofon/görsel/uzak servis yalnızca kullanıcı eylemiyle açılır; desteklenmeyen özellik açıkça belirtilir.

## Aşama 7 — Güvenli kodlama ve yerel yardımcı

- Kod açıklama, düzenleme önerisi, test üretme ve diff inceleme.
- Python Mini mevcut deneysel sınırlarıyla korunur.
- Tam Python çalıştırma yalnızca ayrı konteyner/VM, ağ kapatma, CPU/RAM/süre kotası ve kullanıcı izolasyonu sağlanırsa.
- Windows yerel yardımcı: eşleştirme, izin listesi, görünür işlem, durdurma ve riskli eylem onayı.
- İnternete açık keyfi komut çalıştırma veya kimlik doğrulamasız cihaz erişimi yok.

Kabul: Güvenilmeyen kod Streamlit web sürecinde veya kullanıcının bilgisayarında doğrudan çalıştırılmaz.

## Aşama 8 — Yönetim, güvenlik ve ölçek

- Yönetici paneli: kullanıcı/rol, kota, sağlayıcı sağlığı, hata kategorileri ve kullanım metrikleri.
- Hassas veri içermeyen denetim kayıtları; anahtar, parola, belge ve sohbet içeriği loglanmaz.
- Merkezi kota/iş kuyruğu ve çoklu sunucuya uygun kalıcı depo.
- Yedekleme, geri yükleme provası, veri saklama ve silme politikaları.
- Hız, erişilebilirlik, mobil uyum, hata izleme ve güvenlik testleri.
- Kurum özellikleri: davet, ekip alanı, rol tabanlı paylaşım ve yönetici politikaları.

Kabul: Kota eşzamanlı isteklerde aşılmaz; yedek geri yükleme ve kullanıcı izolasyonu testle kanıtlanır.

## Aşama 9 — Yayın ve canlıya geçiş

- Tüm aşamalar için yeşil CI ve güvenlik kontrolü.
- Staging/preview üzerinde Supabase entegrasyon ve Streamlit uçtan uca test.
- Mobil/masaüstü manuel kontrol listesi.
- Migration yedekleme ve geri dönüş provası.
- Kullanıcıya değişiklik özeti, riskler ve geri dönüş commit'i.
- Ayrı açık onay olmadan PR birleştirilmez ve canlı dağıtım yapılmaz.

## Şu anki kapsam ve sınırlar

Mevcut uygulamada Streamlit sohbeti, beş çalışma modu, sınırlı belge çıkarımı, isteğe bağlı Groq araştırması, kaynak kaydı, e-posta taslağı, yerel seslendirme, deneysel Python Mini, Ollama yönlendirmesi ve Supabase tabanlı hesap/veri altyapısı bulunuyor. Bu özelliklerin gerçek üretim ortamında uçtan uca çalıştığı henüz varsayılmayacak; her biri ayrıca doğrulanacak.

Bu plan tek seferde büyük ve riskli bir değişiklik yapmak yerine küçük, test edilebilir teslimatlara bölünür. Öncelik: mevcut hesap/veri güvenliğini doğrulamak, ardından sohbet ve belge deneyimini sağlamlaştırmak.
