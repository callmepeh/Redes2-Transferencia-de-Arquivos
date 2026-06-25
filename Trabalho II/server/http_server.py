"""
Servidor HTTP/1.1 sobre TCP Nativo
Serve arquivos estáticos (HTML, CSS, TXT) em resposta a requisições GET.
Inclui os cabeçalhos padrão HTTP/1.1 e o campo personalizado X-Custom-Auth.

Uso:
    python3 server/http_server.py
    python3 server/http_server.py --port 8080 --www www/
"""

import os
import sys
import socket
import mimetypes
import argparse
import time

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocol.auth import get_auth_hash

DEFAULT_PORT = 80
DEFAULT_WWW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "www")


def get_content_type(filepath: str) -> str:
    """Determina o Content-Type com base na extensão do arquivo."""
    content_type, _ = mimetypes.guess_type(filepath)
    if content_type is None:
        content_type = "application/octet-stream"
    return content_type


def build_http_response(status_code: int, status_text: str, content: bytes,
                        content_type: str = "text/html") -> bytes:
    """
    Constrói uma resposta HTTP/1.1 completa com cabeçalhos padrão
    e o campo X-Custom-Auth.
    """
    auth_hash = get_auth_hash()
    
    headers = (
        f"HTTP/1.1 {status_code} {status_text}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(content)}\r\n"
        f"X-Custom-Auth: {auth_hash}\r\n"
        f"Connection: close\r\n"
        f"Server: MiniWebServer/1.0 (R-UDP/TCP)\r\n"
        f"Date: {time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())}\r\n"
        f"\r\n"
    ).encode('utf-8')
    
    return headers + content


def handle_request(data: bytes, www_dir: str) -> bytes:
    """
    Processa uma requisição HTTP GET e retorna a resposta apropriada.
    """
    try:
        request_text = data.decode('utf-8', errors='replace')
        lines = request_text.split('\r\n')
        
        if not lines:
            return build_http_response(400, "Bad Request", b"<h1>400 Bad Request</h1>")
        
        # Parse da linha de requisição: GET /path HTTP/1.1
        request_line = lines[0]
        parts = request_line.split()
        
        if len(parts) < 2:
            return build_http_response(400, "Bad Request", b"<h1>400 Bad Request</h1>")
        
        method = parts[0]
        path = parts[1]
        
        # Apenas GET é suportado
        if method != "GET":
            return build_http_response(405, "Method Not Allowed",
                                       b"<h1>405 Method Not Allowed</h1><p>Only GET is supported.</p>")
        
        # Sanitiza o path para evitar directory traversal
        # Remove query strings
        if '?' in path:
            path = path.split('?')[0]
        
        # Remove fragmentos
        if '#' in path:
            path = path.split('#')[0]
        
        # Normaliza o path
        clean_path = os.path.normpath(path)
        # Remove o leading slash para path relativo
        if clean_path.startswith('/'):
            clean_path = clean_path[1:]
        
        # Se for diretório raiz, serve index.html
        if clean_path == "" or clean_path.endswith('/'):
            clean_path = os.path.join(clean_path, "index.html")
        
        # Constrói o caminho completo do arquivo
        filepath = os.path.join(www_dir, clean_path)
        
        # Verifica se o arquivo existe e está dentro do diretório www
        real_www = os.path.realpath(www_dir)
        real_file = os.path.realpath(filepath)
        
        if not real_file.startswith(real_www):
            # Directory traversal detectado
            content = b"<h1>403 Forbidden</h1><p>Acesso negado.</p>"
            return build_http_response(403, "Forbidden", content)
        
        if not os.path.isfile(real_file) or not os.path.exists(real_file):
            # Arquivo não encontrado - 404
            not_found_path = os.path.join(www_dir, "404.html")
            if os.path.isfile(not_found_path):
                with open(not_found_path, "rb") as f:
                    content = f.read()
            else:
                content = f"<h1>404 Not Found</h1><p>Arquivo n&atilde;o encontrado: {path}</p>".encode('utf-8')
            return build_http_response(404, "Not Found", content)
        
        # Lê o arquivo e retorna 200 OK
        with open(real_file, "rb") as f:
            content = f.read()
        
        content_type = get_content_type(real_file)
        return build_http_response(200, "OK", content, content_type)
        
    except Exception as e:
        print(f"[HTTP] Erro ao processar requisição: {e}")
        return build_http_response(500, "Internal Server Error",
                                   f"<h1>500 Internal Server Error</h1><p>{e}</p>".encode('utf-8'))


def start_server(port: int = DEFAULT_PORT, www_dir: str = DEFAULT_WWW):
    """
    Inicia o servidor HTTP/1.1 sobre TCP.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", port))
    server.listen(5)
    
    print(f"[HTTP/TCP] Servidor HTTP/1.1 ouvindo em TCP 0.0.0.0:{port}")
    print(f"[HTTP/TCP] Servindo arquivos de: {www_dir}")
    print(f"[HTTP/TCP] Aguardando conexões...")
    
    request_count = 0
    
    while True:
        try:
            conn, addr = server.accept()
            request_count += 1
            print(f"[HTTP/TCP] Conexão #{request_count} de {addr}")
            
            # Recebe a requisição
            data = conn.recv(8192)
            if data:
                # Processa e envia resposta
                response = handle_request(data, www_dir)
                conn.sendall(response)
                print(f"[HTTP/TCP] Requisição #{request_count} respondida")
            else:
                print(f"[HTTP/TCP] Conexão vazia de {addr}")
            
            conn.close()
            
        except KeyboardInterrupt:
            print(f"\n[HTTP/TCP] Servidor encerrado. Total de {request_count} requisições.")
            break
    
    server.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Servidor HTTP/1.1 sobre TCP")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Porta TCP (default: {DEFAULT_PORT})")
    parser.add_argument("--www", type=str, default=DEFAULT_WWW,
                        help=f"Diretório de conteúdo web (default: {DEFAULT_WWW})")
    args = parser.parse_args()
    
    start_server(port=args.port, www_dir=args.www)
