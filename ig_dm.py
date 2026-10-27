#!/usr/bin/env python3
"""Instagram yorum → DM otomasyonu (ManyChat'siz, tek dosya, yalnız Python standart kütüphanesi).

Akış:
  1) Gönderine yorum gelir; yorumda kurallar.json'daki bir kelime geçiyorsa:
     a) yoruma herkese açık kısa cevap   b) yorumcuya ÖZEL CEVAP (private reply): linksiz, tek tuşlu DM
  2) Kişi tuşa basar ya da DM'den cevap yazar → asıl içerik (metin + istersen link tuşu) gider.
  Her kişiye her adım en fazla bir kez. Durum ig.db'de (SQLite) tutulur.

Çalıştırma: cron'la birkaç dakikada bir ya da webhook.py tetikler.
  python3 ig_dm.py            normal çalışma
  python3 ig_dm.py --kuru     hiçbir şey göndermez, ne yapacağını yazar
  python3 ig_dm.py --temel    ilk kurulum: mevcut tüm yorum/DM'leri "görüldü" sayar (geçmişe mesaj atmaz)
"""
import json, re, sqlite3, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

DIZIN = Path(__file__).resolve().parent
ENV, DB, KURAL = DIZIN / '.env', DIZIN / 'ig.db', DIZIN / 'kurallar.json'
G = 'https://graph.instagram.com/v23.0/'
KURU, TEMEL = '--kuru' in sys.argv, '--temel' in sys.argv


def env(ad):
    m = re.search(rf'^{ad}=(\S+)', ENV.read_text(), re.M)
    return m.group(1) if m else ''


def api(yol, veri=None):
    url = G + yol + ('&' if '?' in yol else '?') + 'access_token=' + TOK
    istek = urllib.request.Request(url, data=json.dumps(veri).encode() if veri else None,
                                   headers={'Content-Type': 'application/json'}, method='POST' if veri else 'GET')
    try:
        return json.load(urllib.request.urlopen(istek, timeout=30))
    except urllib.error.HTTPError as e:
        raise RuntimeError(json.load(e).get('error', {}).get('message', str(e))[:200])


def db():
    c = sqlite3.connect(DB)
    c.execute('CREATE TABLE IF NOT EXISTS gorulen (id TEXT PRIMARY KEY, zaman TEXT DEFAULT CURRENT_TIMESTAMP)')
    c.execute('CREATE TABLE IF NOT EXISTS adim (kisi TEXT, kural TEXT, adim TEXT, zaman TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(kisi, kural, adim))')
    c.execute('CREATE TABLE IF NOT EXISTS ayar (k TEXT PRIMARY KEY, v TEXT)')
    return c


def goruldu(c, id_):
    """İlk görüşte False döner ve işaretler; sonraki her çalışmada True."""
    if c.execute('SELECT 1 FROM gorulen WHERE id=?', (id_,)).fetchone():
        return True
    if not KURU:
        c.execute('INSERT INTO gorulen(id) VALUES (?)', (id_,)); c.commit()
    return False


def yapildi(c, kisi, kural, adim):
    return bool(c.execute('SELECT 1 FROM adim WHERE kisi=? AND kural=? AND adim=?', (kisi, kural, adim)).fetchone())


def isaretle(c, kisi, kural, adim):
    if not KURU:
        c.execute('INSERT OR IGNORE INTO adim(kisi, kural, adim) VALUES (?,?,?)', (kisi, kural, adim)); c.commit()


def bekleyen_kural(c, kisi):
    """Kişiye ilk DM gitmiş ama içerik gitmemiş en son kural (tuşa bastığında hangi içeriği alacağı)."""
    r = c.execute("""SELECT b.kural FROM adim b WHERE b.kisi=? AND b.adim='dm'
                     AND NOT EXISTS (SELECT 1 FROM adim i WHERE i.kisi=b.kisi AND i.kural=b.kural AND i.adim='icerik')
                     ORDER BY b.zaman DESC LIMIT 1""", (kisi,)).fetchone()
    return r[0] if r else None


def gonder(ad, fn):
    if KURU or TEMEL:
        print(f'  [kuru] {ad}'); return True
    try:
        fn(); print(f'  ✓ {ad}'); return True
    except Exception as e:
        print(f'  ✗ {ad}: {e}'); return False


def kural_bul(metin):
    for k in KURALLAR:
        if re.search(r'(?<!\w)(' + '|'.join(map(re.escape, k['kelimeler'])) + r')(?!\w)', metin or '', re.I):
            return k
    return None


def ozel_cevap(yorum_id, k):
    # Özel cevap = yorum sahibine yorum üzerinden açılan DM. İlk mesajda LİNK YOK (spam filtresi), yalnız tuş.
    mesaj = {'text': k['ilk_dm'], 'quick_replies': [{'content_type': 'text', 'title': k.get('tus', 'Gönder'), 'payload': 'K:' + k['id']}]}
    try:
        api('me/messages', {'recipient': {'comment_id': yorum_id}, 'message': mesaj})
    except RuntimeError as e:
        print('  tuşlu olmadı, tuşsuz deneniyor:', e)
        api('me/messages', {'recipient': {'comment_id': yorum_id}, 'message': {'text': k['ilk_dm']}})


def icerik(uid, k):
    # Kişi bize yazdıktan sonra 24 saatlik mesaj penceresi açılır: artık link gönderilebilir.
    if k.get('link'):
        try:
            api('me/messages', {'recipient': {'id': uid}, 'message': {'attachment': {'type': 'template', 'payload': {
                'template_type': 'button', 'text': k['icerik'][:640],
                'buttons': [{'type': 'web_url', 'url': k['link'], 'title': k.get('link_baslik', 'Aç')[:20]}]}}}})
            return
        except RuntimeError as e:
            print('  link tuşu olmadı, düz metin:', e)
    api('me/messages', {'recipient': {'id': uid}, 'message': {'text': (k['icerik'] + ('\n' + k['link'] if k.get('link') else ''))[:1000]}})


def yorumlar(c):
    for m in api('me/media?fields=id,permalink&limit=30')['data']:
        ys = api(m['id'] + '/comments?fields=id,text,username,from&limit=50').get('data', [])
        for y in ys:
            u = y.get('username') or (y.get('from') or {}).get('username') or ''
            if u.lower() == BEN or goruldu(c, y['id']) or TEMEL:
                continue
            k = kural_bul(y.get('text'))
            if not k:
                continue
            uid = (y.get('from') or {}).get('id') or u
            print(f'yorum @{u} → kural {k["id"]}', flush=True)
            if k.get('yorum_cevabi') and not yapildi(c, uid, k['id'], 'yorum') and \
                    gonder(f'yorum cevabı @{u}', lambda: api(y['id'] + '/replies', {'message': k['yorum_cevabi'].format(u=u)})):
                isaretle(c, uid, k['id'], 'yorum')
            if not yapildi(c, uid, k['id'], 'dm') and gonder(f'ilk DM @{u}', lambda: ozel_cevap(y['id'], k)):
                isaretle(c, uid, k['id'], 'dm')


def dmler(c):
    for kon in api('me/conversations?platform=instagram&fields=messages.limit(5){id,from,message}&limit=25').get('data', []):
        for msj in reversed(kon.get('messages', {}).get('data', [])):
            f = msj.get('from') or {}
            if (f.get('username') or '').lower() == BEN or goruldu(c, msj['id']) or TEMEL:
                continue
            uid, u, metin = f.get('id'), f.get('username', '?'), msj.get('message') or ''
            kid = bekleyen_kural(c, uid) or bekleyen_kural(c, u)
            k = next((x for x in KURALLAR if x['id'] == kid), None) or kural_bul(metin)   # DM'den doğrudan kelime yazan da alır
            if not k or yapildi(c, uid, k['id'], 'icerik'):
                continue   # otomasyonla ilgisi olmayan DM: dokunma
            if gonder(f'içerik @{u} ({k["id"]})', lambda: icerik(uid, k)):
                isaretle(c, uid, k['id'], 'icerik')


def token_yenile(c):
    """Uzun ömürlü token 60 gün geçerli; haftada bir yenilenir, .env güncellenir."""
    son = c.execute("SELECT v FROM ayar WHERE k='yenileme'").fetchone()
    if KURU or (son and time.time() - float(son[0]) < 7 * 86400):
        return
    d = json.load(urllib.request.urlopen('https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=' + TOK, timeout=30))
    if d.get('access_token'):
        ENV.write_text(re.sub(r'^IG_TOKEN=\S+', 'IG_TOKEN=' + d['access_token'], ENV.read_text(), flags=re.M))
        c.execute("INSERT OR REPLACE INTO ayar VALUES ('yenileme', ?)", (str(time.time()),)); c.commit()
        print('token yenilendi')


if __name__ == '__main__':
    TOK, BEN = env('IG_TOKEN'), env('IG_KULLANICI').lower().lstrip('@')
    KURALLAR = json.loads(KURAL.read_text())
    c = db()
    yorumlar(c); dmler(c); token_yenile(c)
