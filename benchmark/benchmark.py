"""
benchmark.py — Ponto de entrada principal do benchmark.

Executa automaticamente todos os cenários (A, B, C) para TCP e R-UDP,
salvando os resultados em logs/results.csv.

USO DENTRO DO CONTAINER CLIENTE:
    python3 benchmark/benchmark.py

O script executa:
  1. Aplica o cenário de rede (tc qdisc)
  2. Roda N transferências TCP
  3. Roda N transferências R-UDP
  4. Limpa as regras tc
  5. Repete para o próximo cenário
"""

import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.scenarios import SCENARIOS
from benchmark.runner import run_benchmark

RUNS_PER_SCENARIO = 15  # PDF pede entre 10 e 30


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


def main():
    print("=" * 60)
    print("  BENCHMARK TCP vs R-UDP")
    print("  Pedro Henrique de Carvalho Sousa - 20239017876")
    print("=" * 60)

    for scenario_key in ["A", "B", "C"]:
        scenario = SCENARIOS[scenario_key]
        print(f"\n{'#'*60}")
        print(f"  CENÁRIO {scenario_key}: {scenario['label']}")
        print(f"{'#'*60}")

        apply_tc(scenario_key)

        # TCP
        run_benchmark("tcp", RUNS_PER_SCENARIO, scenario_key, "pdf_text.txt")

        # R-UDP
        run_benchmark("rudp", RUNS_PER_SCENARIO, scenario_key, "pdf_text.txt")

        clear_tc()

    print("\n" + "=" * 60)
    print("  BENCHMARK COMPLETO!")
    print(f"  Resultados salvos em: logs/results.csv")
    print("=" * 60)


if __name__ == "__main__":
    main()