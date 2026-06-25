"""
Cliente DNS Minimalista
Resolve nomes de domínio consultando o servidor DNS sobre UDP.

Uso:
    python3 dns/client.py servidor.local
    python3 dns/client.py servidor.local --dns-server 10.0.0.1 --port 5353
"""

import os
import sys
import socket
import argparse
import random

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dns.packet import DNSPacket, FLAG_QUERY, FLAG_RESPONSE

DEFAULT_DNS_SERVER = os.environ.get("DNS_SERVER_HOST", "servidor_dns")
DEFAULT_DNS_PORT = int(os.environ.get("DNS_SERVER_PORT", 53))
DNS_TIMEOUT = 2.0  # segundos


def resolve(domain: str, dns_server: str = DEFAULT_DNS_SERVER,
            dns_port: int = DEFAULT_DNS_PORT, timeout: float = DNS_TIMEOUT) -> tuple[str, int]:
    """
    Resolve um nome de domínio via consulta DNS.
    
    Args:
        domain: Nome do domínio a resolver (ex: "servidor.local")
        dns_server: IP/host do servidor DNS
        dns_port: Porta UDP do servidor DNS
        timeout: Timeout em segundos
    
    Returns:
        tuple[str, int]: (ip_resolvido, ttl)
        
    Raises:
        TimeoutError: Se o servidor DNS não responder
        ValueError: Se o domínio não for encontrado
    """
    query_id = random.randint(0, 65535)

    # Cria pacote de consulta
    query = DNSPacket(query_id, FLAG_QUERY, domain)
    query_bytes = query.pack()

    # Cria socket UDP
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.settimeout(timeout)

    try:
        # Envia consulta
        print(f"[DNS CLIENT] Resolvendo '{domain}' -> {dns_server}:{dns_port} (ID={query_id})")
        client.sendto(query_bytes, (dns_server, dns_port))

        # Aguarda resposta
        data, addr = client.recvfrom(2048)
        response = DNSPacket.unpack(data)

        # Verifica se é a resposta para nossa consulta
        if response.query_id != query_id:
            print(f"[DNS CLIENT] AVISO: ID de consulta diferente (esperado={query_id}, recebido={response.query_id})")

        if response.is_error() or response.ip == "0.0.0.0":
            raise ValueError(f"Domínio '{domain}' não encontrado no servidor DNS")

        print(f"[DNS CLIENT] Resolvido: {domain} -> {response.ip} (TTL={response.ttl}s)")
        return response.ip, response.ttl

    except socket.timeout:
        raise TimeoutError(f"Timeout ao consultar DNS {dns_server}:{dns_port} para '{domain}'")
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description="Cliente DNS")
    parser.add_argument("domain", type=str, help="Nome do domínio a resolver")
    parser.add_argument("--dns-server", type=str, default=DEFAULT_DNS_SERVER,
                        help=f"Servidor DNS (default: {DEFAULT_DNS_SERVER})")
    parser.add_argument("--port", type=int, default=DEFAULT_DNS_PORT,
                        help=f"Porta UDP do DNS (default: {DEFAULT_DNS_PORT})")
    parser.add_argument("--timeout", type=float, default=DNS_TIMEOUT,
                        help=f"Timeout em segundos (default: {DNS_TIMEOUT})")

    args = parser.parse_args()

    try:
        ip, ttl = resolve(args.domain, args.dns_server, args.port, args.timeout)
        print(f"\nResultado: {args.domain} -> {ip}")
    except TimeoutError as e:
        print(f"\nERRO: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\nERRO: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
