# Yapay zekana ver (Claude Code / Codex / ChatGPT)

```
Bu klasörde Instagram yorum → DM otomasyonu var (ig_dm.py, webhook.py, kurallar.json, README.md).
Önce README.md'yi baştan sona oku. Sonra benimle adım adım kur:

1. Bana hangi kelimeye hangi içeriği göndermek istediğimi sor; kurallar.json'u buna göre yaz
   (Türkçe I/ı tuzağı için kelimenin iki yazımını da ekle).
2. Meta uygulamasını kurarken her adımda ekranda ne görmem gerektiğini söyle, ben yapayım, sen doğrula.
3. .env'i benimle doldur, token'ı asla sohbete yazdırma.
4. Önce `python3 ig_dm.py --temel`, sonra `--kuru` çalıştır; çıktıyı birlikte okuyalım.
5. Cron'u kur; webhook istersem HTTPS ile birlikte kur.
6. Rolü olmayan ikinci bir hesapla gerçek test yaptır: yorum → yorum cevabı → tuşlu DM → tuşa bas → içerik.
   Dördü de gelmeden "çalışıyor" deme.
Kodun akışını (iki adım, tek seferlik, linksiz ilk mesaj) bozma.
```
