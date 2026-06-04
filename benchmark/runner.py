"""
Runner: executa as transferências TCP e R-UDP localmente
e salva os resultados em CSV para análise posterior.

USO DENTRO DO CONTAINER:
    python3 benchmark/runner.py --protocol tcp --runs 10
    python3 benchmark/runner.py --protocol rudp --runs 10

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


def run_tcp(filepath: str) -> dict:
    """Executa uma transferência TCP e retorna as métricas."""
    from client.tcp_client import start_client
    return start_client(filepath)


def run_rudp(filepath: str) -> dict:
    """Executa uma transferência R-UDP e retorna as métricas."""
    from client.rudp_client import start_client
    return start_client(filepath)


def append_to_csv(row: dict, scenario: str):
    """Grava uma linha de resultado no CSV."""
    os.makedirs(CSV_DIR, exist_ok=True)
    file_exists = os.path.isfile(CSV_FILE)

    fieldnames = ["protocol", "scenario", "run", "time", "throughput", "bytes", "retransmissions"]

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists or os.path.getsize(CSV_FILE) == 0:
            writer.writeheader()
        writer.writerow(row)


def run_benchmark(protocol: str, runs: int, scenario: str, filepath: str):
    """Executa N transferências de um protocolo e salva os resultados."""
    results = []

    print(f"\n{'='*60}")
    print(f"  Benchmark: {protocol.upper()} | Cenário {scenario} | {runs} execuções")
    print(f"{'='*60}\n")

    for i in range(runs):
        print(f"\n--- Execução {i+1}/{runs} ---")

        if protocol == "tcp":
            metrics = run_tcp(filepath)
        elif protocol == "rudp":
            metrics = run_rudp(filepath)
        else:
            raise ValueError(f"Protocolo desconhecido: {protocol}")

        row = {
            "protocol": protocol,
            "scenario": scenario,
            "run": i + 1,
            "time": f"{metrics['time']:.6f}",
            "throughput": f"{metrics['throughput']:.2f}",
            "bytes": metrics["bytes"],
            "retransmissions": metrics.get("retransmissions", 0),
        }
        append_to_csv(row, scenario)
        results.append(metrics)

        # Pequena pausa entre execuções para não sobrecarregar
        time.sleep(0.3)

    # Resumo estatístico
    summary = summarize_results(results)
    print(f"\n{'='*60}")
    print(f"  RESUMO — {protocol.upper()} | Cenário {scenario}")
    print(f"{'='*60}")
    print(f"  Execuções:       {summary['n_runs']}")
    print(f"  Throughput:")
    print(f"    Mínimo:        {summary['throughput']['min']:.2f} bytes/s")
    print(f"    Máximo:        {summary['throughput']['max']:.2f} bytes/s")
    print(f"    Média:         {summary['throughput']['mean']:.2f} bytes/s")
    print(f"    Desvio Padrão: {summary['throughput']['std']:.2f} bytes/s")
    print(f"  Tempo:")
    print(f"    Mínimo:        {summary['time']['min']:.6f}s")
    print(f"    Máximo:        {summary['time']['max']:.6f}s")
    print(f"    Média:         {summary['time']['mean']:.6f}s")
    print(f"    Desvio Padrão: {summary['time']['std']:.6f}s")
    if protocol == "rudp":
        print(f"  Retransmissões:")
        print(f"    Total Médio:   {summary['retransmissions']['mean']:.1f}")
        print(f"    Máximo:        {summary['retransmissions']['max']:.0f}")
    print(f"{'='*60}\n")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runner de benchmark TCP vs R-UDP")
    parser.add_argument("--protocol", choices=["tcp", "rudp", "all"], default="all",
                        help="Protocolo a testar (tcp, rudp ou all)")
    parser.add_argument("--runs", type=int, default=10,
                        help="Número de execuções por protocolo (10-30)")
    parser.add_argument("--scenario", type=str, default="A",
                        help="Cenário de rede (A, B ou C)")
    parser.add_argument("--file", type=str, default="pdf_text.txt",
                        help="Arquivo a transferir")

    args = parser.parse_args()

    if args.protocol == "all":
        for proto in ["tcp", "rudp"]:
            run_benchmark(proto, args.runs, args.scenario, args.file)
    else:
        run_benchmark(args.protocol, args.runs, args.scenario, args.file)

    print(f"\nResultados salvos em: {CSV_FILE}")
