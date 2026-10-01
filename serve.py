#!/usr/bin/env python3
"""HTTPS server for the Quran PWA.

Plain HTTP is not a secure context, so browsers refuse to offer PWA install
from a LAN address (http://192.168.x.x). Serving over HTTPS with a self-signed
certificate makes the app installable on every device on the network. Visitors
must accept the certificate warning once per device — that is the unavoidable
cost of not having a public domain.

Generated files (in the app dir, git-ignored):
  cert.pem / key.pem  — self-signed certificate covering localhost + the LAN IP
"""
import http.server
import os
import ssl
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "7860"))
CA = os.path.join(HERE, "rootCA.pem")
CAKEY = os.path.join(HERE, "rootCA-key.pem")
CERT = os.path.join(HERE, "cert.pem")
KEY = os.path.join(HERE, "key.pem")


def lan_ip():
    """Best-effort first non-loopback global IPv4 address."""
    try:
        out = subprocess.run(
            ["ip", "-4", "-o", "addr", "show", "scope", "global"],
            capture_output=True, text=True, timeout=5,
        ).stdout
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                return parts[3].split("/")[0]
    except Exception:
        pass
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def sans_for(ip):
    names = "DNS:localhost,IP:127.0.0.1"
    if ip and ip != "127.0.0.1":
        names += f",IP:{ip}"
    return names


def make_ca():
    """Create the local CA once. Stable across IP changes, so devices that
    trust it stay trusted when your LAN IP shifts."""
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-sha256", "-nodes",
         "-days", "3650",
         "-keyout", CAKEY, "-out", CA,
         "-subj", "/CN=Quran Local CA",
         "-addext", "basicConstraints=critical,CA:TRUE",
         "-addext", "keyUsage=critical,keyCertSign,cRLSign"],
        check=True, capture_output=True,
    )


def cert_is_valid():
    """True if a leaf cert exists, is signed by our CA, and covers the LAN IP."""
    if not (os.path.exists(CERT) and os.path.exists(KEY) and os.path.exists(CA)):
        return False
    ip = lan_ip()
    try:
        r = subprocess.run(
            ["openssl", "verify", "-CAfile", CA, CERT],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            return False
        if not ip:
            return True  # cannot compare SANs; keep the existing cert
        s = subprocess.run(
            ["openssl", "x509", "-in", CERT, "-noout", "-ext", "subjectAltName"],
            capture_output=True, text=True, timeout=10,
        )
        return ip in s.stdout
    except Exception:
        return True


def ensure_cert():
    """Generate the CA (once) and a leaf cert signed by it for this host."""
    if not (os.path.exists(CA) and os.path.exists(CAKEY)):
        make_ca()
        print(f"  Created local Certificate Authority ({CA})")
    if cert_is_valid():
        return
    ip = lan_ip() or "127.0.0.1"
    csr = os.path.join(HERE, "server.csr")
    ext = os.path.join(HERE, "server.ext")
    with open(ext, "w") as f:
        f.write("basicConstraints=CA:FALSE\n")
        f.write("keyUsage=digitalSignature,keyEncipherment\n")
        f.write("extendedKeyUsage=serverAuth\n")
        f.write(f"subjectAltName={sans_for(ip)}\n")
    subprocess.run(
        ["openssl", "req", "-newkey", "rsa:2048", "-sha256", "-nodes",
         "-keyout", KEY, "-out", csr, "-subj", "/CN=Quran Local App"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["openssl", "x509", "-req", "-sha256", "-days", "825",
         "-in", csr, "-CA", CA, "-CAkey", CAKEY, "-CAcreateserial",
         "-out", CERT, "-extfile", ext],
        check=True, capture_output=True,
    )
    os.remove(csr)
    os.remove(ext)
    print(f"  Generated server certificate ({CERT}) for {ip or 'this host'}")


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serve files from HERE; support Range requests for audio seeking."""

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    # Range support: python's SimpleHTTPRequestHandler ignores it, which breaks
    # seeking in long audio and can re-download a whole file on every scrub.
    # Serve the local CA at a friendly URL with the right MIME type, so a
    # phone can open https://<ip>:7860/ca.crt and its OS offers to install it
    # as a trusted certificate. Without this the file downloads as text and
    # the user has to find it in a file manager.
    def do_GET(self):
        if self.path.rstrip("/") in ("/ca.crt", "/rootCA.pem", "/ca.pem"):
            if os.path.isfile(CA):
                with open(CA, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/x-x509-ca-cert")
                self.send_header("Content-Disposition",
                                 "attachment; filename=\"quran-ca.crt\"")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(404, "CA certificate not generated yet")
            return
        return super().do_GET()

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        if not os.path.isfile(path) or "range" not in self.headers:
            return super().send_head()
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None
        try:
            fs = os.fstat(f.fileno())
            size = fs.st_size
            m = self.headers["range"]
            unit, _, rng = m.partition("=")
            if unit.strip().lower() != "bytes":
                f.close()
                return super().send_head()
            first, _, last = rng.partition("-")
            first = int(first) if first else 0
            last = int(last) if last else size - 1
            last = min(last, size - 1)
            if first > last or first >= size:
                f.close()
                self.send_error(416, "Requested Range Not Satisfiable")
                return None
            self.send_response(206)
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Content-Range", f"bytes {first}-{last}/{size}")
            self.send_header("Content-Length", str(last - first + 1))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.end_headers()
            f.seek(first)
            n = last - first + 1
            remaining = n
            while remaining > 0:
                chunk = f.read(min(65536, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)
            f.close()
            return None  # body already written
        except Exception:
            f.close()
            raise

    def log_message(self, fmt, *args):
        pass  # keep the launcher output clean


def main():
    ensure_cert()
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT, KEY)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    print(f"  HTTPS on 0.0.0.0:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
