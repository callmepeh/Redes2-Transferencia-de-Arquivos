"""
Funções para cálculo de métricas estatísticas dos resultados do benchmark.

Calcula: mínimo, máximo, média e desvio padrão de throughput e tempo,
conforme exigido pelo enunciado (10~30 execuções por cenário).
"""

import math


def compute_stats(values: list[float]) -> dict:
    """Calcula min, max, média e desvio padrão de uma lista de valores."""
    n = len(values)
    if n == 0:
        return {"min": 0, "max": 0, "mean": 0, "std": 0}

    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std = math.sqrt(variance)

    return {
        "min": min(values),
        "max": max(values),
        "mean": mean,
        "std": std,
    }


def summarize_results(results: list[dict]) -> dict:
    """
    Recebe uma lista de dicts (cada um com time, throughput, retransmissions)
    e retorna um resumo estatístico.
    """
    times = [r["time"] for r in results]
    throughputs = [r["throughput"] for r in results]
    retransmissions = [r["retransmissions"] for r in results]

    return {
        "n_runs": len(results),
        "time": compute_stats(times),
        "throughput": compute_stats(throughputs),
        "retransmissions": compute_stats(retransmissions),
    }
