"""
Cliente HTTP com Resolução DNS
1. Resolve o IP do servidor web via DNS
2. Faz requisição HTTP GET usando TCP ou R-UDP

Uso:
    python3 client/http_client.py GET /index.html
    python3 client/http_client.py GET /index.html --protocol tcp --server servidor.local
    python3 client/http_client.py GET /index.html --protocol rudp --server servidor.local --save output.html
"""

import os
import sys
import socket
import argparse
import time

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dns.client import resolve as dns_resolve
from client.rudp_client import send_http_via_rudp

# Configurações padrão via variáveis de ambiente
DNS_SERVER_HOST = os.environ.get("DNS_SERVER_HOST", "servidor_dns")
DNS_SERVER_PORT = int(os.environ.get("DNS_SERVER_PORT", 53))
HTTP_TCP_PORT = int(os.environ.get("HTTP_TCP_PORT", 80))
HTTP_RUDP_PORT = int(os.environ.get("HTTP_RUDP_PORT", 81))

# Timeout DNS
DNS_TIMEOUT = float(os.environ.get("DNS_TIMEOUT", "2.0"))


def http_get_tcp(server_ip: str, port: int, path: str) -> tuple[int, bytes, float]:
    """
    Faz uma requisição HTTP GET usando socket TCP.
    
    Returns:
        tuple[int, bytes, float]: (status_code, body, elapsed_time)
    """
    start_time = time.time()
    
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(30.0)
    
    try:
        # Conecta ao servidor
        client.connect((server_ip, port))
        
        # Constrói a requisição HTTP GET
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {server_ip}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode('utf-8')
        
        # Envia requisição
        client.sendall(request)
        
        # Recebe resposta
        response_data = b""
        while True:
            try:
                chunk = client.recv(8192)
                if not chunk:
                    break
                response_data += chunk
            except socket.timeout:
                break
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Parse da resposta HTTP
        if not response_data:
            raise ValueError("Resposta vazia do servidor")
        
        # Separa cabeçalhos do corpo
        header_end = response_data.find(b"\r\n\r\n")
        if header_end == -1:
            raise ValueError("Formato de resposta HTTP inválido")
        
        headers_bytes = response_data[:header_end]
        body = response_data[header_end + 4:]
        
        # Extrai status code da primeira linha
        first_line = headers_bytes.split(b"\r\n")[0].decode('utf-8', errors='replace')
        parts = first_line.split()
        status_code = int(parts[1]) if len(parts) >= 2 else 0
        
        return status_code, body, elapsed
        
    finally:
        client.close()


def http_get_rudp(server_ip: str, port: int, path: str) -> tuple[int, bytes, float]:
    """
    Faz uma requisição HTTP GET usando R-UDP.
    
    Returns:
        tuple[int, bytes, float]: (status_code, body, elapsed_time)
    """
    start_time = time.time()
    
    # Constrói a requisição HTTP GET
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {server_ip}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode('utf-8')
    
    # Envia requisição via R-UDP e recebe resposta
    response_data, retransmissions = send_http_via_rudp(server_ip, port, request)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    if not response_data:
        raise ValueError("Resposta vazia do servidor R-UDP")
    
    # Parse da resposta HTTP
    header_end = response_data.find(b"\r\n\r\n")
    if header_end == -1:
        raise ValueError("Formato de resposta HTTP inválido (R-UDP)")
    
    headers_bytes = response_data[:header_end]
    body = response_data[header_end + 4:]
    
    first_line = headers_bytes.split(b"\r\n")[0].decode('utf-8', errors='replace')
    parts = first_line.split()
    status_code = int(parts[1]) if len(parts) >= 2 else 0
    
    return status_code, body, elapsed


def main():
    parser = argparse.ArgumentParser(description="Cliente HTTP com Resolução DNS")
    parser.add_argument("method", type=str, nargs="?", default="GET",
                        help="Método HTTP (apenas GET é suportado)")
    parser.add_argument("path", type=str, nargs="?", default="/index.html",
                        help="Caminho do recurso (ex: /index.html)")
    parser.add_argument("--protocol", type=str, choices=["tcp", "rudp"], default="tcp",
                        help="Protocolo de transporte (default: tcp)")
    parser.add_argument("--server", type=str, default="servidor.local",
                        help="Nome do servidor web para resolução DNS")
    parser.add_argument("--dns-server", type=str, default=DNS_SERVER_HOST,
                        help=f"Servidor DNS (default: {DNS_SERVER_HOST})")
    parser.add_argument("--dns-port", type=int, default=DNS_SERVER_PORT,
                        help=f"Porta DNS (default: {DNS_SERVER_PORT})")
    parser.add_argument("--port", type=int, default=None,
                        help="Porta do servidor web (default: 80 para TCP, 81 para R-UDP)")
    parser.add_argument("--save", type=str, default=None,
                        help="Salvar resposta em arquivo")
    
    args = parser.parse_args()
    
    # Determina porta
    if args.port is None:
        port = HTTP_TCP_PORT if args.protocol == "tcp" else HTTP_RUDP_PORT
    else:
        port = args.port
    
    print("=" * 60)
    print("  CLIENTE HTTP COM RESOLUÇÃO DNS")
    print("=" * 60)
    print(f"  Método:     {args.method}")
    print(f"  Path:       {args.path}")
    print(f"  Servidor:   {args.server}")
    print(f"  Protocolo:  {args.protocol}")
    print(f"  Porta:      {port}")
    print(f"  DNS Server: {args.dns_server}:{args.dns_port}")
    print("=" * 60)
    
    # Passo 1: Resolução DNS
    print(f"\n[CLIENT] Passo 1: Resolvendo '{args.server}' via DNS...")
    try:
        server_ip, ttl = dns_resolve(args.server, args.dns_server, args.dns_port, DNS_TIMEOUT)
        print(f"[CLIENT] DNS: {args.server} -> {server_ip}")
    except TimeoutError as e:
        print(f"[CLIENT] ERRO: {e}")
        print("[CLIENT] Tentando fallback para nome do container...")
        # Fallback: usa o nome do servidor diretamente como hostname
        server_ip = args.server
    except ValueError as e:
        print(f"[CLIENT] ERRO: {e}")
        print("[CLIENT] Tentando fallback para nome do container...")
        server_ip = args.server
    
    # Passo 2: Requisição HTTP
    print(f"\n[CLIENT] Passo 2: Enviando requisição HTTP GET {args.path}")
    print(f"[CLIENT] Transporte: {args.protocol.upper()} -> {server_ip}:{port}")
    
    try:
        if args.protocol == "tcp":
            status_code, body, elapsed = http_get_tcp(server_ip, port, args.path)
        else:
            status_code, body, elapsed = http_get_rudp(server_ip, port, args.path)
        
        print(f"\n[CLIENT] Resposta recebida!")
        print(f"  Status:     {status_code}")
        print(f"  Tamanho:    {len(body)} bytes")
        print(f"  Tempo:      {elapsed:.4f}s")
        print(f"  Throughput: {len(body) / max(elapsed, 0.001):.2f} B/s")
        
        # Salva resposta se solicitado
        if args.save:
            with open(args.save, "wb") as f:
                f.write(body)
            print(f"  Salvo em:   {args.save}")
        
        # Mostra preview do conteúdo (primeiros 500 bytes)
        preview = body[:500].decode('utf-8', errors='replace')
        print(f"\n--- Preview (primeiros 500 bytes) ---")
        print(preview)
        print("--- Fim do Preview ---")
        
        return {
            "status_code": status_code,
            "body_size": len(body),
            "time": elapsed,
            "throughput": len(body) / max(elapsed, 0.001),
            "protocol": args.protocol,
            "server": args.server,
            "path": args.path,
        }
        
    except Exception as e:
        print(f"\n[CLIENT] ERRO na requisição HTTP: {e}")
        return None


if __name__ == "__main__":
    main()
