"""
Runner: executa as transferências HTTP (TCP e R-UDP) com resolução DNS
e salva os resultados em CSV para análise posterior.

USO DENTRO DO CONTAINER CLIENTE:
    python3 benchmark/runner.py --protocol tcp --runs 10 --file-size 100kb
    python3 benchmark/runner.py --protocol rudp --runs 10 --file-size 1mb

Ou para rodar tudo:
    python3 benchmark/runner.py --protocol all --runs 10
"""

import sys
import os
import csv
import argparse
import time

# Garante que o diretório raiz do projeto esteja no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.metrics import summarize_results

CSV_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
CSV_FILE = os.path.join(CSV_DIR, "results.csv")

# Tamanhos de arquivo disponíveis
FILE_SIZES = {
    "100kb": ("/arquivo_100kb.txt", "100kb"),
    "1mb":   ("/arquivo_1024kb.txt", "1mb"),
    "10mb":  ("/arquivo_10240kb.txt", "10mb"),
}

# Configurações de servidores
DNS_SERVER_HOST = os.environ.get("DNS_SERVER_HOST", "servidor_dns")
DNS_SERVER_PORT = int(os.environ.get("DNS_SERVER_PORT", 53))

def run_http_tcp(server_ip: str, port: int, path: str) -> dict:
    """Executa uma requisição HTTP via TCP e retorna as métricas."""
    from client.http_client import http_get_tcp
    
    try:
        status_code, body, elapsed = http_get_tcp(server_ip, port, path)
        return {
            "protocol": "tcp",
            "time": elapsed,
            "throughput": len(body) / max(elapsed, 0.001),
            "bytes": len(body),
            "retransmissions": 0,
            "status_code": status_code,
            "body_size": len(body),
        }
    except Exception as e:
        print(f"[ERRO] TCP request failed: {e}")
        return None


def run_http_rudp(server_ip: str, port: int, path: str) -> dict:
    """Executa uma requisição HTTP via R-UDP e retorna as métricas."""
    from client.http_client import http_get_rudp
    
    try:
        status_code, body, elapsed = http_get_rudp(server_ip, port, path)
        return {
            "protocol": "rudp",
            "time": elapsed,
            "throughput": len(body) / max(elapsed, 0.001),
            "bytes": len(body),
            "retransmissions": 0,  # Será atualizado se disponível
            "status_code": status_code,
            "body_size": len(body),
        }
    except Exception as e:
        print(f"[ERRO] R-UDP request failed: {e}")
        return None


def resolve_dns(server_name: str) -> tuple[str, float]:
    """
    Resolve um nome de servidor via DNS.
    Retorna (ip, dns_time).
    """
    from dns.client import resolve as dns_resolve
    
    try:
        start_dns = time.time()
        ip, ttl = dns_resolve(server_name, DNS_SERVER_HOST, DNS_SERVER_PORT, timeout=2.0)
        dns_time = time.time() - start_dns
        print(f"[DNS] {server_name} -> {ip} em {dns_time:.4f}s")
        return ip, dns_time
    except Exception as e:
        print(f"[DNS] Fallback para nome do container: {e}")
        return server_name, 0.0


def append_to_csv(row: dict):
    """Grava uma linha de resultado no CSV."""
    os.makedirs(CSV_DIR, exist_ok=True)
    file_exists = os.path.isfile(CSV_FILE)

    fieldnames = [
        "protocol", "scenario", "file_size", "run",
        "time", "throughput", "bytes", "retransmissions",
        "dns_time", "status_code", "body_size"
    ]

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists or os.path.getsize(CSV_FILE) == 0:
            writer.writeheader()
        writer.writerow(row)


def run_benchmark(protocol: str, runs: int, scenario: str, file_key: str = "100kb"):
    """
    Executa N transferências HTTP de um protocolo e salva os resultados.
    
    Args:
        protocol: "tcp", "rudp"
        runs: Número de execuções
        scenario: "A", "B", "C"
        file_key: "100kb", "1mb", "10mb"
    """
    results = []
    
    if file_key not in FILE_SIZES:
        print(f"[ERRO] Tamanho de arquivo desconhecido: {file_key}")
        print(f"  Opções: {', '.join(FILE_SIZES.keys())}")
        return []
    
    file_path, file_label = FILE_SIZES[file_key]
    
    # Determina porta
    port = int(os.environ.get("HTTP_TCP_PORT", "80")) if protocol == "tcp" \
           else int(os.environ.get("HTTP_RUDP_PORT", "81"))
    
    server_name = os.environ.get("HTTP_SERVER_HOST", "servidor.local")
    
    print(f"\n{'='*60}")
    print(f"  Benchmark: HTTP/{protocol.upper()} | Cenário {scenario} | "
          f"{file_label} | {runs} execuções")
    print(f"{'='*60}")
    
    # Resolve DNS (faz apenas uma vez para o benchmark)
    print(f"\n[DNS] Resolvendo '{server_name}'...")
    server_ip, dns_time = resolve_dns(server_name)
    print(f"[DNS] Resolvido: {server_name} -> {server_ip} em {dns_time:.4f}s")
    
    for i in range(runs):
        print(f"\n--- Execução {i+1}/{runs} ---")
        
        if protocol == "tcp":
            metrics = run_http_tcp(server_ip, port, file_path)
        elif protocol == "rudp":
            metrics = run_http_rudp(server_ip, port, file_path)
        else:
            raise ValueError(f"Protocolo desconhecido: {protocol}")
        
        if metrics is None:
            print(f"  [FALHA] Execução {i+1} falhou, pulando...")
            continue
        
        row = {
            "protocol": protocol,
            "scenario": scenario,
            "file_size": file_label,
            "run": i + 1,
            "time": f"{metrics['time']:.6f}",
            "throughput": f"{metrics['throughput']:.2f}",
            "bytes": metrics["bytes"],
            "retransmissions": metrics.get("retransmissions", 0),
            "dns_time": dns_time,
            "status_code": metrics.get("status_code", 0),
            "body_size": metrics.get("body_size", 0),
        }
        append_to_csv(row)
        results.append(metrics)
        
        # Pequena pausa entre execuções
        time.sleep(0.3)
    
    # Resumo estatístico
    summary = summarize_results(results)
    print(f"\n{'='*60}")
    print(f"  RESUMO — HTTP/{protocol.upper()} | Cenário {scenario} | {file_label}")
    print(f"{'='*60}")
    print(f"  Execuções:       {summary['n_runs']}")
    print(f"  Throughput:")
    print(f"    Mínimo:        {summary['throughput']['min']:.2f} B/s")
    print(f"    Máximo:        {summary['throughput']['max']:.2f} B/s")
    print(f"    Média:         {summary['throughput']['mean']:.2f} B/s")
    print(f"    Desvio Padrão: {summary['throughput']['std']:.2f} B/s")
    print(f"  Tempo:")
    print(f"    Mínimo:        {summary['time']['min']:.6f}s")
    print(f"    Máximo:        {summary['time']['max']:.6f}s")
    print(f"    Média:         {summary['time']['mean']:.6f}s")
    print(f"    Desvio Padrão: {summary['time']['std']:.6f}s")
    if protocol == "rudp":
        print(f"  Retransmissões:")
        print(f"    Total Médio:   {summary['retransmissions']['mean']:.1f}")
    print(f"  DNS Time (ms):  {dns_time*1000:.2f}")
    print(f"{'='*60}\n")
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runner de benchmark HTTP TCP vs R-UDP")
    parser.add_argument("--protocol", choices=["tcp", "rudp", "all"], default="all",
                        help="Protocolo a testar (tcp, rudp ou all)")
    parser.add_argument("--runs", type=int, default=10,
                        help="Número de execuções por protocolo (min 10)")
    parser.add_argument("--scenario", type=str, default="A",
                        help="Cenário de rede (A, B ou C)")
    parser.add_argument("--file-size", type=str, default="100kb",
                        choices=["100kb", "1mb", "10mb"],
                        help="Tamanho do arquivo (100kb, 1mb, 10mb)")
    parser.add_argument("--dns", action="store_true", default=True,
                        help="Usar resolução DNS (default: True)")

    args = parser.parse_args()

    if args.protocol == "all":
        for proto in ["tcp", "rudp"]:
            run_benchmark(proto, args.runs, args.scenario, args.file_size)
    else:
        run_benchmark(args.protocol, args.runs, args.scenario, args.file_size)

    print(f"\nResultados salvos em: {CSV_FILE}")
