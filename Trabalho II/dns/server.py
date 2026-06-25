"""
Servidor DNS Minimalista (Mini-DNS)
Opera exclusivamente via UDP na porta 53 (ou customizada)
Resolve consultas do tipo A (IPv4) com base em um arquivo de zona estático (hosts.txt)

Uso:
    python3 dns/server.py
    python3 dns/server.py --port 5353 --hosts dns/hosts.txt
"""

import os
import sys
import socket
import argparse

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dns.packet import DNSPacket, FLAG_QUERY, FLAG_RESPONSE, FLAG_ERROR

DEFAULT_PORT = 53
DEFAULT_HOSTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hosts.txt")


def load_hosts(filepath: str) -> dict[str, str]:
    """
    Carrega o arquivo de zona estático.
    Retorna um dicionário: {nome_dominio: ip}
    Ignora linhas em branco e comentários (#).
    """
    hosts = {}
    if not os.path.exists(filepath):
        print(f"[DNS] AVISO: Arquivo {filepath} não encontrado. Usando tabela vazia.")
        return hosts

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0].lower()
                ip = parts[1]
                hosts[name] = ip

    print(f"[DNS] Carregados {len(hosts)} registros de {filepath}")
    return hosts


def start_server(port: int = DEFAULT_PORT, hosts_file: str = DEFAULT_HOSTS):
    """
    Inicia o servidor DNS.
    Escuta em UDP, recebe consultas, consulta a tabela e responde.
    """
    hosts = load_hosts(hosts_file)

    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind(("0.0.0.0", port))
    except PermissionError:
        print(f"[DNS] ERRO: Porta {port} requer privilégios. Use --port para porta alternativa (ex: 5353)")
        sys.exit(1)

    print(f"[DNS] Servidor DNS ouvindo em UDP 0.0.0.0:{port}")
    print(f"[DNS] Aguardando consultas...")

    query_count = 0

    while True:
        try:
            data, addr = server.recvfrom(2048)

            try:
                query = DNSPacket.unpack(data)
            except (ValueError, Exception) as e:
                print(f"[DNS] Pacote inválido de {addr}: {e}")
                continue

            if not query.is_query():
                print(f"[DNS] Ignorando pacote não-consulta de {addr}")
                continue

            query_count += 1
            domain = query.name.lower()
            print(f"[DNS] Consulta #{query_count}: '{domain}' de {addr}")

            # Resolve o nome
            ip = hosts.get(domain)
            if ip:
                print(f"[DNS]   -> Resolvido: {domain} = {ip}")
                response = DNSPacket(query.query_id, FLAG_RESPONSE, domain, ip, ttl=300)
            else:
                print(f"[DNS]   -> NÃO ENCONTRADO: {domain}")
                # Retorna IP 0.0.0.0 para indicar não encontrado
                response = DNSPacket(query.query_id, FLAG_RESPONSE | FLAG_ERROR, domain, "0.0.0.0", ttl=0)

            server.sendto(response.pack(), addr)

        except KeyboardInterrupt:
            print(f"\n[DNS] Servidor encerrado. Total de {query_count} consultas respondidas.")
            break

    server.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mini-Servidor DNS")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help="Porta UDP (default: 53)")
    parser.add_argument("--hosts", type=str, default=DEFAULT_HOSTS,
                        help="Arquivo de zona estático (default: dns/hosts.txt)")
    args = parser.parse_args()

    start_server(port=args.port, hosts_file=args.hosts)
