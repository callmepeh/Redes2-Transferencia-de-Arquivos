"""
Servidor HTTP/1.1 sobre R-UDP (Reliable UDP)
Serve arquivos estáticos (HTML, CSS, TXT) em resposta a requisições GET.
Usa o protocolo R-UDP com Stop-and-Wait para entrega confiável.
Inclui cabeçalhos padrão HTTP/1.1 e X-Custom-Auth.

Uso:
    python3 server/rudp_http_server.py
    python3 server/rudp_http_server.py --port 8081 --www www/
"""

import os
import sys
import socket
import mimetypes
import argparse
import time

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocol.packet import RUDP_Packet, FLAG_DATA, FLAG_ACK, FLAG_FIN
from protocol.auth import get_auth_hash

DEFAULT_PORT = 81
DEFAULT_WWW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "www")
TIMEOUT = 1.0  # segundos


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
        f"Server: MiniWebServer/1.0 (R-UDP)\r\n"
        f"Date: {time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())}\r\n"
        f"\r\n"
    ).encode('utf-8')
    
    return headers + content


def handle_request(data: bytes, www_dir: str) -> tuple[int, bytes]:
    """
    Processa uma requisição HTTP GET e retorna (status_code, response_bytes).
    """
    try:
        request_text = data.decode('utf-8', errors='replace')
        lines = request_text.split('\r\n')
        
        if not lines:
            return (400, build_http_response(400, "Bad Request", b"<h1>400 Bad Request</h1>"))
        
        request_line = lines[0]
        parts = request_line.split()
        
        if len(parts) < 2:
            return (400, build_http_response(400, "Bad Request", b"<h1>400 Bad Request</h1>"))
        
        method = parts[0]
        path = parts[1]
        
        if method != "GET":
            return (405, build_http_response(405, "Method Not Allowed",
                                              b"<h1>405 Method Not Allowed</h1><p>Only GET is supported.</p>"))
        
        if '?' in path:
            path = path.split('?')[0]
        if '#' in path:
            path = path.split('#')[0]
        
        clean_path = os.path.normpath(path)
        if clean_path.startswith('/'):
            clean_path = clean_path[1:]
        
        if clean_path == "" or clean_path.endswith('/'):
            clean_path = os.path.join(clean_path, "index.html")
        
        filepath = os.path.join(www_dir, clean_path)
        real_www = os.path.realpath(www_dir)
        real_file = os.path.realpath(filepath)
        
        if not real_file.startswith(real_www):
            content = b"<h1>403 Forbidden</h1><p>Acesso negado.</p>"
            return (403, build_http_response(403, "Forbidden", content))
        
        if not os.path.isfile(real_file) or not os.path.exists(real_file):
            not_found_path = os.path.join(www_dir, "404.html")
            if os.path.isfile(not_found_path):
                with open(not_found_path, "rb") as f:
                    content = f.read()
            else:
                content = f"<h1>404 Not Found</h1><p>Arquivo n&atilde;o encontrado: {path}</p>".encode('utf-8')
            return (404, build_http_response(404, "Not Found", content))
        
        with open(real_file, "rb") as f:
            content = f.read()
        
        content_type = get_content_type(real_file)
        return (200, build_http_response(200, "OK", content, content_type))
        
    except Exception as e:
        print(f"[HTTP/R-UDP] Erro ao processar requisição: {e}")
        return (500, build_http_response(500, "Internal Server Error",
                                          f"<h1>500 Internal Server Error</h1><p>{e}</p>".encode('utf-8')))


def send_via_rudp(server_socket, client_addr, data: bytes):
    """
    Envia dados para o cliente usando o protocolo R-UDP (Stop-and-Wait).
    Fragmenta os dados em múltiplos pacotes R-UDP.
    """
    seq_num = 0
    total_retransmissions = 0
    chunk_size = 1024  # payload máximo por pacote R-UDP
    
    # Fragmenta os dados em chunks
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    total_chunks = len(chunks)
    
    print(f"[HTTP/R-UDP] Enviando {len(data)} bytes em {total_chunks} pacotes R-UDP...")
    
    for i, chunk in enumerate(chunks):
        packet = RUDP_Packet(seq_num, 0, FLAG_DATA, chunk)
        packet_bytes = packet.pack()
        
        ack_received = False
        while not ack_received:
            try:
                server_socket.sendto(packet_bytes, client_addr)
                ack_data, _ = server_socket.recvfrom(2048)
                ack_packet = RUDP_Packet.unpack(ack_data)
                
                if ack_packet.flags == FLAG_ACK and ack_packet.ack_num == seq_num:
                    ack_received = True
                    seq_num += 1
            except socket.timeout:
                total_retransmissions += 1
                print(f"[HTTP/R-UDP] TIMEOUT seq={seq_num}, chunk {i+1}/{total_chunks}. "
                      f"Retransmissão #{total_retransmissions}")
            except ValueError:
                # ACK corrompido
                pass
    
    return total_retransmissions, total_chunks


def start_server(port: int = DEFAULT_PORT, www_dir: str = DEFAULT_WWW):
    """
    Inicia o servidor HTTP/1.1 sobre R-UDP.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.settimeout(TIMEOUT)
    server.bind(("0.0.0.0", port))
    
    print(f"[HTTP/R-UDP] Servidor HTTP/1.1 ouvindo em R-UDP 0.0.0.0:{port}")
    print(f"[HTTP/R-UDP] Servindo arquivos de: {www_dir}")
    print(f"[HTTP/R-UDP] Aguardando requisições...")
    
    request_count = 0
    
    while True:
        try:
            # Aguarda requisição via R-UDP
            data, addr = server.recvfrom(4096)
            
            try:
                # Tenta desempacotar como R-UDP
                rudp_packet = RUDP_Packet.unpack(data)
                
                if rudp_packet.flags == FLAG_DATA:
                    request_count += 1
                    request_data = rudp_packet.payload
                    
                    print(f"[HTTP/R-UDP] Requisição #{request_count} recebida de {addr} "
                          f"(seq={rudp_packet.seq_num}, {len(request_data)} bytes)")
                    
                    # Envia ACK para o pacote de dados
                    ack_packet = RUDP_Packet(0, rudp_packet.seq_num, FLAG_ACK)
                    server.sendto(ack_packet.pack(), addr)
                    
                    # Processa a requisição HTTP
                    status_code, response = handle_request(request_data, www_dir)
                    print(f"[HTTP/R-UDP] Resposta #{request_count}: status={status_code}, "
                          f"tamanho={len(response)} bytes")
                    
                    # Envia resposta via R-UDP
                    retransmissions, total_chunks = send_via_rudp(server, addr, response)
                    print(f"[HTTP/R-UDP] Requisição #{request_count} concluída: "
                          f"{total_chunks} chunks, {retransmissions} retransmissões")
                    
                    # Envia FIN para encerrar a sessão
                    fin_packet = RUDP_Packet(0, 0, FLAG_FIN)
                    server.sendto(fin_packet.pack(), addr)
                
                elif rudp_packet.flags == FLAG_FIN:
                    ack_packet = RUDP_Packet(0, rudp_packet.seq_num, FLAG_ACK)
                    server.sendto(ack_packet.pack(), addr)
                    
            except ValueError as e:
                print(f"[HTTP/R-UDP] Pacote inválido de {addr}: {e}")
                
        except socket.timeout:
            continue
        except KeyboardInterrupt:
            print(f"\n[HTTP/R-UDP] Servidor encerrado. Total de {request_count} requisições.")
            break
    
    server.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Servidor HTTP/1.1 sobre R-UDP")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Porta R-UDP (default: {DEFAULT_PORT})")
    parser.add_argument("--www", type=str, default=DEFAULT_WWW,
                        help=f"Diretório de conteúdo web (default: {DEFAULT_WWW})")
    args = parser.parse_args()
    
    start_server(port=args.port, www_dir=args.www)
