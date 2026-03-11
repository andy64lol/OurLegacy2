#!/usr/bin/env python3
"""Simple HTTP server to serve the Our Legacy landing page."""

import http.server
import socketserver
import os

PORT = 5000
HOST = "0.0.0.0"


class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with socketserver.TCPServer((HOST, PORT), NoCacheHTTPRequestHandler) as httpd:
        httpd.allow_reuse_address = True
        print(f"Serving Our Legacy at http://{HOST}:{PORT}")
        httpd.serve_forever()
