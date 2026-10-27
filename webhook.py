#!/usr/bin/env python3
"""Instagram webhook alıcısı: Meta doğrulamasına cevap verir, her bildirimde ig_dm.py'yi hemen çalıştırır.
Gelen gövde kullanılmaz (yalnız tetik); iş mantığı ig_dm.py'de, veriyi Graph API'den kendisi okur.
Böylece sahte bir istek en fazla bir kontrol turu tetikler. Önüne HTTPS veren bir proxy koy (Caddy/Nginx/Traefik)."""
import os, subprocess, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DIZIN = Path(__file__).resolve().parent
VT = os.environ.get('IG_VERIFY_TOKEN') or (DIZIN / 'verify_token.txt').read_text().strip()


class H(BaseHTTPRequestHandler):
    def do_GET(self):   # Meta webhook doğrulaması
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if q.get('hub.mode') == ['subscribe'] and q.get('hub.verify_token') == [VT]:
            self.send_response(200); self.end_headers(); self.wfile.write(q.get('hub.challenge', [''])[0].encode())
        else:
            self.send_response(403); self.end_headers()

    def do_POST(self):
        self.rfile.read(min(int(self.headers.get('Content-Length') or 0), 1_000_000))
        self.send_response(200); self.end_headers(); self.wfile.write(b'ok')
        # flock: aynı anda tek tur (Linux). macOS'ta flock yoksa doğrudan python3 çağır.
        subprocess.Popen(['flock', '-n', '/tmp/ig-dm.lock', 'python3', str(DIZIN / 'ig_dm.py')],
                         stdout=open(DIZIN / 'ig.log', 'a'), stderr=subprocess.STDOUT)

    def log_message(self, *a):
        pass


ThreadingHTTPServer(('127.0.0.1', int(os.environ.get('PORT', 8797))), H).serve_forever()
