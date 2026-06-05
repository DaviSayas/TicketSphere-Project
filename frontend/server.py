import http.server
import socketserver
import mimetypes
import sys

PORT = 5173

# Fix Windows MIME type bug for ES Modules
mimetypes.init()
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Prevent caching in development
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

# Threaded server: serves parallel ES-module requests concurrently.
# (A single-threaded server refuses connections when the browser opens
#  several module requests at once -> net::ERR_CONNECTION_REFUSED.)
class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

print(f"Iniciando o servidor frontend na porta {PORT}...")
try:
    with ThreadingHTTPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"Servidor a correr em http://localhost:{PORT}")
        print("Pressione CTRL+C para parar.")
        httpd.serve_forever()
except KeyboardInterrupt:
    print("\nServidor parado pelo utilizador.")
    sys.exit(0)
except Exception as e:
    print(f"Erro ao iniciar o servidor: {e}")
    sys.exit(1)
