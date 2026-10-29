# Nesil AI

Herkesin kullanabileceği genel amaçlı yapay zekâ ajanı için ilk web prototipi.

## Özellikler
- Türkçe sohbet arayüzü
- Genel yardımcı, görev planlama, kodlama ve rapor modları
- İsteğe bağlı Groq API bağlantısı
- API anahtarı tanımlı değilken açıkça etiketlenmiş demo modu

## Streamlit Community Cloud ile yayınlama
1. https://share.streamlit.io adresini aç ve GitHub hesabınla giriş yap.
2. Create app seçeneğine bas.
3. Repository: tcapar1/nesil-ai, Branch: main, Main file path: app.py seç.
4. Uygulamayı yayımla.
5. Gerçek model yanıtları için uygulama ayarlarının Secrets bölümüne şu biçimde anahtar ekle:

   GROQ_API_KEY = "buraya_kendi_api_anahtarın"

Anahtarı GitHub dosyalarına veya sohbet mesajlarına yazma. Groq hesabında API anahtarını kendin oluşturmalısın; sağlayıcının limitleri ve koşulları değişebilir.

## Güvenlik ve sınırlar
- Bu prototip dosya sistemi üzerinde işlem yapmaz, komut çalıştırmaz ve internette kendi başına gezinmez.
- API anahtarı eklenmezse uygulama gerçek yapay zekâ cevabı vermez; demo şablonu gösterir.
- Herkese açık hizmete geçmeden önce gizlilik bildirimi, kullanım sınırları, kötüye kullanım önlemleri ve testler eklenmelidir.
