import http.server
import socketserver
import json
import random
import time
from urllib.parse import urlparse

PORT = 3000

class MockBackendHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        # Simula endpoint de jobs pendentes
        if parsed_path.path == "/api/project/pending":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # 30% de chance de ter um job (para não spammar)
            if random.random() < 0.3:
                # Gera um ID único baseado no tempo
                job_id = int(time.time())
                job_data = {
                    "id": str(job_id),
                    "topic": "Curiosidades sobre o Espaço",
                    "script": "Você sabia que no espaço ninguém ouve seus gritos? O vácuo impede a propagação do som. Incrível, não?",
                    "theme": "cyan_future"
                }
                print(f"\n[SERVER] 📦 Enviando Job #{job_id} para o Worker...")
                self.wfile.write(json.dumps(job_data).encode('utf-8'))
            else:
                # Sem jobs
                self.wfile.write(json.dumps(None).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed_path = urlparse(self.path)
        
        # Simula endpoint de conclusão
        if parsed_path.path.endswith("/complete"):
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            print(f"\n[SERVER] ✅ Job #{data.get('id')} Concluído!")
            print(f"         📁 Arquivo: {data.get('video_path')}")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silenciar logs padrão do HTTP para limpar o terminal
        return

print(f"🌐 Mock Backend rodando em http://localhost:{PORT}")
print("   (Simulando NestJS API - Pressione Ctrl+C para parar)")

with socketserver.TCPServer(("", PORT), MockBackendHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server parado.")
