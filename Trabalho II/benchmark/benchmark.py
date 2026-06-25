"""
benchmark.py — Ponto de entrada principal do benchmark do Trabalho II.

Executa automaticamente todos os cenários (A, B, C) para TCP e R-UDP
com diferentes tamanhos de arquivo, salvando os resultados em logs/results.csv.

USO DENTRO DO CONTAINER CLIENTE:
    python3 benchmark/benchmark.py

O script executa:
  1. Gera arquivos de teste se não existirem
  2. Aplica o cenário de rede (tc qdisc)
  3. Roda N transferências HTTP/TCP para cada tamanho de arquivo
  4. Roda N transferências HTTP/R-UDP para cada tamanho de arquivo
  5. Limpa as regras tc
  6. Repete para o próximo cenário
"""

import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.scenarios import SCENARIOS
from benchmark.runner import run_benchmark

RUNS_PER_SCENARIO = 10  # Mínimo exigido pelo PDF
FILE_SIZES = ["100kb", "1mb"]  # 10mb é muito lento para R-UDP, opcional


def apply_tc(scenario_key: str):
    """Aplica as regras de controle de tráfego (tc) para o cenário dado."""
    scenario = SCENARIOS[scenario_key]

    # Remove regras anteriores
    subprocess.run(
        ["tc", "qdisc", "del", "dev", "eth0", "root"],
        capture_output=True
    )

    # Aplica novas regras
    cmd = scenario["tc_cmd"].split()
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"[TC] Cenário {scenario_key} aplicado: {scenario['label']}")
    else:
        print(f"[TC] AVISO: falha ao aplicar tc: {result.stderr}")
        print(f"[TC] (Pode ser normal se estiver rodando fora do Docker)")


def clear_tc():
    """Remove todas as regras de controle de tráfego."""
    subprocess.run(
        ["tc", "qdisc", "del", "dev", "eth0", "root"],
        capture_output=True
    )
    print("[TC] Regras removidas.")


def generate_test_files():
    """Gera arquivos de teste no diretório www/ se não existirem."""
    www_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "www")
    os.makedirs(www_dir, exist_ok=True)
    
    test_files = {
        "arquivo_100kb.txt": 100 * 1024,
        "arquivo_1024kb.txt": 1024 * 1024,
    }
    
    for filename, size in test_files.items():
        filepath = os.path.join(www_dir, filename)
        if not os.path.exists(filepath):
            print(f"[SETUP] Gerando {filename} ({size} bytes)...")
            content = (
                "Linha de teste para o Mini-Servidor Web - "
                "Redes II UFPI - Pedro Henrique Carvalho\n"
            )
            with open(filepath, "w") as f:
                written = 0
                while written < size:
                    chunk = content[:size - written]
                    f.write(chunk)
                    written += len(chunk)
            print(f"[SETUP] {filename} gerado: {os.path.getsize(filepath)} bytes")


def main():
    print("=" * 60)
    print("  BENCHMARK — Trabalho II")
    print("  HTTP/1.1 (TCP vs R-UDP) + DNS")
    print("  Pedro Henrique de Carvalho Sousa - 20239017876")
    print("=" * 60)
    
    # Gera arquivos de teste
    generate_test_files()

    for scenario_key in ["A", "B", "C"]:
        scenario = SCENARIOS[scenario_key]
        print(f"\n{'#'*60}")
        print(f"  CENÁRIO {scenario_key}: {scenario['label']}")
        print(f"{'#'*60}")

        apply_tc(scenario_key)

        for file_size in FILE_SIZES:
            # TCP
            run_benchmark("tcp", RUNS_PER_SCENARIO, scenario_key, file_size)
            # R-UDP
            run_benchmark("rudp", RUNS_PER_SCENARIO, scenario_key, file_size)

        clear_tc()

    print("\n" + "=" * 60)
    print("  BENCHMARK COMPLETO!")
    print(f"  Resultados salvos em: logs/results.csv")
    print("=" * 60)


if __name__ == "__main__":
    main()
