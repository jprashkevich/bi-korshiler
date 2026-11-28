"""Публичная раздача файлов для Instagram: GET /m/<токен> из таблицы media, GET /health.

Отдельный бесплатный веб-сервис Render (biglife-media). Instagram скачивает слайды и видео сам,
по публичному адресу, а воркер завода из интернета не виден. Сервис нарочно минимальный — stdlib
и psycopg, без кода завода: ему не нужны ни Chromium, ни ключи, только DATABASE_URL.
Список файлов не отдаётся, только файл по точному случайному токену.
"""
from __future__ import annotations

import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg

TOKEN = re.compile(r"^/m/([A-Za-z0-9_-]{20,80}\.(?:jpg|mp4))$")


def fetch(token: str):
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        return conn.execute("SELECT mime, data FROM media WHERE token = %s", (token,)).fetchone()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes = b"", mime: str = "text/plain", head: bool = False) -> None:
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def _serve(self, head: bool) -> None:
        if self.path == "/health":
            return self._send(200, b"ok", head=head)
        m = TOKEN.match(self.path)
        if not m:
            return self._send(404, b"not found", head=head)
        row = fetch(m.group(1))
        if not row:
            return self._send(404, b"not found", head=head)
        self._send(200, bytes(row[1]), row[0], head=head)

    def do_GET(self):
        self._serve(head=False)

    def do_HEAD(self):
        self._serve(head=True)

    def log_message(self, fmt, *args):   # токены в адресах — в логи пишем только код ответа
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), Handler).serve_forever()
