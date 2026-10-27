# Instagram Yorum → DM Otomasyonu (ManyChat'siz)

"Yoruma X yaz, DM'den atayım" videolarının arkasındaki sistem. Aylık ücret yok, tek Python dosyası, kendi sunucunda çalışır.
Bu kod benim hesabımda canlı çalışan sistemin genel hali.

**Ne yapar?**

1. Gönderine yorum gelir, yorumda belirlediğin kelime (ör. `OTOMASYON`) geçer.
2. Yoruma herkese açık kısa cevap verir: "DM'den attım 👊"
3. Yorumcuya **özel cevap** (private reply) olarak linksiz, tek tuşlu DM atar: "Göndereyim mi?" → **[Gönder]**
4. Kişi tuşa basınca asıl içerik gider (metin + link tuşu).
5. Her kişiye her adım **bir kez** gider. Aynı kişi 5 kez yorum yazsa da tek DM alır.

Birden çok kelime/içerik tanımlayabilirsin (`kurallar.json`).

---

## Neden iki adım? (en çok yapılan hata)

Instagram, seninle hiç konuşmamış birine istediğin mesajı attırmaz:

- **Özel cevap** yorum başına **tek mesaj** ve yorumdan sonraki **7 gün** içinde gönderilebilir.
- Kişi sana yazınca (tuşa basmak da sayılır) **24 saatlik mesaj penceresi** açılır, ancak o zaman serbestçe içerik/link gönderebilirsin.
- İlk mesaja link koymak spam filtresine takılma riskini artırır. Bu yüzden ilk mesaj linksiz, tuşlu; link ikinci mesajda.

Sistem bu kurallara göre kurgulandı. Tek mesajda link atan otomasyonlar ya teslim edemiyor ya da hesabı riske atıyor.

---

## Kurulum (~30 dk)

### 1) Hesap
Instagram hesabın **Profesyonel** olmalı (Creator ya da İşletme). Facebook sayfası **gerekmez**.

### 2) Meta uygulaması
1. [developers.facebook.com](https://developers.facebook.com) → **Uygulama oluştur** → kullanım alanı: **Instagram API (Instagram girişi ile)**.
2. İzinler:
   - `instagram_business_basic`
   - `instagram_business_manage_comments`
   - `instagram_business_manage_messages`
3. **API kurulumu (Instagram girişi ile)** bölümünde hesabını ekle → **token oluştur**. Bu uzun ömürlü token (60 gün). Kod haftada bir kendisi yeniler.
4. Instagram uygulamasında: **Ayarlar → Mesajlar → Bağlı araçlar → Mesajlara erişime izin ver** açık olmalı. Kapalıysa DM API'si çalışmaz.

### 3) Sunucu
Herhangi bir Linux sunucu (en ucuz VPS yeter) ya da 7/24 açık bir bilgisayar.

```bash
git clone https://github.com/kara-developer/instagram-yorum-dm && cd instagram-yorum-dm
cp .env.example .env            # token ve kullanıcı adını yaz
nano kurallar.json              # kelimelerini ve içeriklerini yaz
python3 ig_dm.py --temel        # İLK ÇALIŞTIRMA: eski yorumları "görüldü" sayar, geçmişe mesaj atmaz
python3 ig_dm.py --kuru         # hiçbir şey göndermeden ne yapacağını gösterir
```

### 4) Tetikleme: iki yol, ikisini birden kur
- **Cron (yedek, şart):** `*/5 * * * * cd /yol/instagram-yorum-dm && flock -n /tmp/ig-dm.lock python3 ig_dm.py >> ig.log 2>&1`
- **Webhook (anlık):** `webhook.py`'yi çalıştır, önüne HTTPS ver (Caddy en kolayı). Meta uygulamasında **Webhooks** → callback URL `https://alanadin/`, doğrulama token'ı = `verify_token.txt` içeriği → `comments` ve `messages` alanlarına abone ol.

Webhook gelen veriye güvenmez, yalnız "bak" sinyali olarak kullanır; asıl veriyi API'den kendisi okur. Sahte istek en fazla bir kontrol turu tetikler.

### 5) Herkese açmak
Uygulama **geliştirme modundayken** yalnız uygulamada rolü olan hesaplarla çalışır. Kendi hesabınla test edip "çalışıyor" sanma:
**Rolü olmayan ikinci bir hesapla** gerçek yorum + tuş testi yap. Herkese açmak için uygulamayı **Canlı** moda al. Meta izinler için Gelişmiş Erişim / Uygulama İncelemesi isteyebilir, panelde ne istediğine bak.

---

## kurallar.json

```json
{
  "id": "otomasyon",
  "kelimeler": ["otomasyon"],
  "yorum_cevabi": "@{u} DM'den attım 👊",
  "ilk_dm": "Selam! Kurulum rehberini göndereyim mi?",
  "tus": "Gönder",
  "icerik": "Buyur 👇 ...",
  "link": "https://...",
  "link_baslik": "Paketi aç"
}
```

- `kelimeler` tam kelime olarak eşleşir (büyük/küçük harf fark etmez). **Türkçe tuzağı:** `HAFIZA` ile `hafıza` farklıdır (I/ı). İkisini de yaz.
- Kişi yorum yazmadan doğrudan DM'den kelimeyi yazarsa da içeriği alır.
- Otomasyonla ilgisi olmayan DM'lere hiçbir şey gitmez.

---

## Tuzaklar ve çözümleri

| Sorun | Çözüm |
|---|---|
| Kurulumda eski yüzlerce yoruma DM gider | İlk çalıştırma `--temel`: geçmiş "görüldü" sayılır |
| Kendi cevabın yeni yorum sanılıp döngüye girer | Kendi kullanıcı adın her yerde atlanır (`IG_KULLANICI`) |
| Aynı kişi birkaç yorum yazınca DM yağar | Kişi × kural × adım tablosu: her adım bir kez |
| Tuşlu özel cevap bazen reddedilir | Tuşsuz düz metne otomatik düşer |
| 60 gün sonra token ölür, sistem sessizce durur | Haftalık otomatik yenileme |
| Webhook bazen geç/eksik geliyor | Cron yedek: en geç 5 dk'da yakalar |
| Aynı anda iki tur aynı kişiye iki DM atar | `flock` ile tek tur |

---

## Claude/ChatGPT ile kendi hesabına uyarlat

`PROMPT.md` dosyasını yapay zekana ver. Kodu senin içeriklerine göre düzenler, kurulumu adım adım yaptırır.

---

**Kara Developer** · Instagram: [@kara.developer](https://instagram.com/kara.developer). Tek kişilik şirketimi AI ajanlarıyla yönetiyorum, çalışanı paylaşıyorum.
Lisans: MIT
