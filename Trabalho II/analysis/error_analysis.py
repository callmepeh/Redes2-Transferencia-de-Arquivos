"""
error_analysis.py — Análise de Erros, Falhas e Retransmissões (Trabalho II)

Analisa dados de HTTP via TCP vs R-UDP com resolução DNS.
Como o runner não registrou retransmissões explicitamente, esta análise
DERIVA métricas de falha a partir de:
  - body_size < expected_file_size → transferência incompleta (falha)
  - Tempos excessivos → indicam retransmissões não contabilizadas
  - body_size vs bytes divergentes → indica erro de parsing HTTP

Gera gráficos:
  1. Taxa de Falha (transferências incompletas) por cenário
  2. Tamanho recebido vs esperado por execução
  3. Tempo de transferência por execução (outliers = falhas)
  4. Distribuição de integridade dos dados
  5. Tabela comparativa de erros/falhas

USO:
    python3 analysis/error_analysis.py
    python3 analysis/error_analysis.py --csv logs/results.csv --output analysis/plots/
"""

import os
import sys
import argparse
import math

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DEFAULT_CSV = os.path.join(ROOT, "logs", "results.csv")
DEFAULT_OUTPUT = os.path.join(ROOT, "analysis", "plots")

# Tamanhos esperados dos arquivos (incluindo cabeçalhos HTTP)
EXPECTED_SIZES = {
    "100kb": 102418,
    "1mb": 1048616,
    "10mb": 10485760,  # hipotético
}

# Limiar para considerar que houve timeout/retransmissão severa
# R-UDP: tempo > expected_base_time * MULTIPLIER indica retransmissões
TIMEOUT_THRESHOLD_MULTIPLIER = 2.0
RUDP_TIMEOUT_SECONDS = 1.0  # timeout do Stop-and-Wait


def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    for col in ["time", "throughput", "retransmissions", "dns_time", "bytes", "body_size"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def classify_transfer(row: pd.Series) -> str:
    """
    Classifica uma transferência como:
      - 'OK' → completa e dentro do esperado
      - 'INCOMPLETA' → body_size < expected_size
      - 'TIMEOUT' → tempo excessivo
      - 'ERRO' → outras anomalias
    """
    expected = EXPECTED_SIZES.get(row.get("file_size", ""), 0)
    body = row.get("body_size", 0)
    if pd.isna(body) or body == 0:
        body = row.get("bytes", 0)
    if pd.isna(body) or body == 0:
        return "ERRO"
    
    # Verifica se é completa
    if body >= expected * 0.95:  # 95% do tamanho esperado
        return "OK"
    elif body >= expected * 0.5:
        return "INCOMPLETA"
    elif body > 0:
        return "FRAGMENTADA"
    else:
        return "ERRO"


def estimate_retransmissions(row: pd.Series) -> int:
    """
    Estima retransmissões para R-UDP baseado no tempo de transferência.
    
    Para Stop-and-Wait com timeout de 1s:
    - Tempo_base ≈ (file_size / 1024) * RTT  (tempo teórico sem perdas)
    - Cada retransmissão adiciona ~1 segundo ao tempo total
    - Retransmissões estimadas ≈ max(0, (time - tempo_base) / 1.0)
    """
    if row.get("protocol") != "rudp":
        return 0
    
    elapsed = row.get("time", 0)
    if pd.isna(elapsed) or elapsed <= 0:
        return 0
    
    file_size = row.get("file_size", "")
    # Tempo base teórico: número de pacotes * RTT do cenário
    # Cenário A: RTT ~ 20ms, B: ~100ms, C: ~200ms
    rtt_map = {"A": 0.020, "B": 0.100, "C": 0.200}
    scenario = row.get("scenario", "A")
    rtt = rtt_map.get(scenario, 0.020)
    
    payload_size = 1024
    file_bytes = EXPECTED_SIZES.get(file_size, 102418)
    num_packets = math.ceil(file_bytes / payload_size)
    
    base_time = num_packets * rtt  # tempo ideal sem perdas
    
    if elapsed <= base_time * 1.5:
        return 0
    
    estimated = max(0, int((elapsed - base_time) / RUDP_TIMEOUT_SECONDS))
    return estimated


def compute_metrics(df: pd.DataFrame) -> dict:
    """Calcula métricas de erro/falha para cada (protocolo, cenário)."""
    metrics = {}
    
    for (proto, scenario, file_size), group in df.groupby(["protocol", "scenario", "file_size"]):
        total_runs = len(group)
        expected = EXPECTED_SIZES.get(file_size, 0)
        
        if expected == 0:
            continue
        
        # Classifica cada transferência
        classifications = group.apply(classify_transfer, axis=1)
        
        ok_runs = (classifications == "OK").sum()
        incomplete_runs = (classifications == "INCOMPLETA").sum()
        fragmented_runs = (classifications == "FRAGMENTADA").sum()
        error_runs = (classifications == "ERRO").sum()
        failed_runs = total_runs - ok_runs
        
        # Estatísticas de body_size
        body_sizes = group["body_size"].fillna(group["bytes"])
        if "bytes" in group.columns:
            bytes_col = group["bytes"].fillna(0)
        else:
            bytes_col = body_sizes
        
        mean_body = body_sizes.mean()
        std_body = body_sizes.std()
        min_body = body_sizes.min()
        
        # Retransmissões
        explicit_ret = group["retransmissions"].sum()
        
        # Retransmissões estimadas para RUDP
        estimated_rets = group.apply(estimate_retransmissions, axis=1)
        total_estimated_ret = estimated_rets.sum()
        mean_estimated_ret = estimated_rets.mean()
        max_estimated_ret = estimated_rets.max()
        
        # Estatísticas de tempo
        times = group["time"].dropna()
        mean_time = times.mean()
        max_time = times.max()
        timeout_count = 0
        
        # Identifica timeouts (tempo excessivo)
        for _, row in group.iterrows():
            elapsed = row.get("time", 0)
            if pd.isna(elapsed):
                continue
            file_size_key = row.get("file_size", "")
            expected_time = {
                "100kb": {"tcp": 0.3, "rudp": 1.0},
                "1mb": {"tcp": 0.5, "rudp": 10.0},
                "10mb": {"tcp": 5.0, "rudp": 100.0},
            }
            proto = row.get("protocol", "tcp")
            threshold = expected_time.get(file_size_key, {}).get(proto, 1.0) * 3
            if elapsed > threshold:
                timeout_count += 1
        
        failure_rate = failed_runs / total_runs * 100
        success_rate = ok_runs / total_runs * 100
        timeout_rate = timeout_count / total_runs * 100
        
        # Completezza média (quanto do arquivo foi recebido)
        completeness = (body_sizes / expected * 100).mean()
        
        metrics[(proto, scenario, file_size)] = {
            "total_runs": total_runs,
            "file_size": file_size,
            "expected_bytes": expected,
            "mean_body": mean_body,
            "std_body": std_body,
            "min_body": min_body,
            "completeness": completeness,
            "ok_runs": int(ok_runs),
            "incomplete_runs": int(incomplete_runs),
            "fragmented_runs": int(fragmented_runs),
            "error_runs": int(error_runs),
            "failed_runs": int(failed_runs),
            "failure_rate": failure_rate,
            "success_rate": success_rate,
            "explicit_retransmissions": int(explicit_ret),
            "estimated_retransmissions": int(total_estimated_ret),
            "mean_estimated_ret": mean_estimated_ret,
            "max_estimated_ret": int(max_estimated_ret),
            "mean_time": mean_time,
            "max_time": max_time,
            "timeout_count": timeout_count,
            "timeout_rate": timeout_rate,
        }
    
    return metrics


def print_error_table(df: pd.DataFrame, metrics: dict):
    """Imprime tabela detalhada de falhas e erros."""
    print("=" * 130)
    print("  TABELA DE ANÁLISE DE FALHAS E ERROS — TRABALHO II (HTTP + DNS)")
    print("=" * 130)
    
    header = (
        f"{'Protocolo':<10} {'Cenário':<10} {'Arquivo':<12} "
        f"{'Exec.':<8} {'OK':<8} {'Falhas':<8} {'Tx.Falha':<10} "
        f"{'Complet.':<10} {'Body Médio':<12} {'Body Min':<12} "
        f"{'Retrans. Est.':<14} {'Timeouts':<10}"
    )
    print(header)
    print("-" * 130)
    
    for (proto, scenario, file_size) in sorted(metrics.keys()):
        m = metrics[(proto, scenario, file_size)]
        completeness_str = f"{m['completeness']:.1f}%"
        if m['completeness'] < 95:
            completeness_str = f"{completeness_str} ⚠"
        
        print(
            f"{proto:<10} {scenario:<10} {file_size:<12} "
            f"{m['total_runs']:<8} {m['ok_runs']:<8} {m['failed_runs']:<8} "
            f"{m['failure_rate']:<10.1f} {completeness_str:<10} "
            f"{m['mean_body']:<12.0f} {m['min_body']:<12.0f} "
            f"{m['estimated_retransmissions']:<14} {m['timeout_count']:<10}"
        )
    
    print("-" * 130)
    print()
    
    # Análise textual
    print("=" * 70)
    print("  ANÁLISE DOS RESULTADOS")
    print("=" * 70)
    
    for (proto, scenario, file_size), m in sorted(metrics.items()):
        if m['failure_rate'] > 0 or m['estimated_retransmissions'] > 0:
            print(f"\n  {proto.upper()} | Cenário {scenario} | {file_size}:")
            print(f"    Taxa de sucesso: {m['success_rate']:.1f}% ({m['ok_runs']}/{m['total_runs']})")
            print(f"    Integridade média: {m['completeness']:.1f}% do arquivo recebido")
            if m['failure_rate'] > 0:
                print(f"    Transferências incompletas: {m['incomplete_runs']} execuções")
            if m['timeout_count'] > 0:
                print(f"    Execuções com timeout: {m['timeout_count']} ({m['timeout_rate']:.1f}%)")
            if m['estimated_retransmissions'] > 0:
                print(f"    Retransmissões (estimadas): total={m['estimated_retransmissions']}, "
                      f"média={m['mean_estimated_ret']:.1f}, máx={m['max_estimated_ret']}")


scenario_labels_t2 = {
    "A": "0% perda / 10ms delay",
    "B": "5% perda / 50ms delay",
    "C": "10% perda / 100ms delay",
}


def plot_failure_rate_per_scenario(df: pd.DataFrame, metrics: dict, output_dir: str):
    """Gráfico: Taxa de falha por (protocolo, cenário, arquivo)."""
    # Agrupa por protocolo e cenário (agregando arquivos)
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Para cada combinação (protocolo, cenário), calcula a taxa de falha média
    scenarios = sorted(df["scenario"].unique())
    protocols = ["tcp", "rudp"]
    x = np.arange(len(scenarios))
    width = 0.35
    colors = {"tcp": "#2196F3", "rudp": "#FF5722"}
    
    for i, proto in enumerate(protocols):
        failure_rates = []
        for scenario in scenarios:
            rates = []
            for key, m in metrics.items():
                if key[0] == proto and key[1] == scenario:
                    rates.append(m["failure_rate"])
            failure_rates.append(np.mean(rates) if rates else 0)
        
        offset = (i - 0.5) * width
        bars = ax.bar([xi + offset for xi in x], failure_rates, width,
                      label=proto.upper(), color=colors[proto], alpha=0.85,
                      edgecolor="black", linewidth=0.8)
        
        for bar, rate in zip(bars, failure_rates):
            if rate > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f"{rate:.1f}%", ha="center", fontsize=10, fontweight="bold")
    
    ax.set_xlabel("Cenário de Rede", fontsize=12)
    ax.set_ylabel("Taxa de Falha (%)", fontsize=12)
    ax.set_title("Taxa de Falha das Transferências HTTP\n(transferências incompletas ou com erro)",
                 fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Cenário {s}\n({scenario_labels_t2.get(s, '')})" for s in scenarios],
                       fontsize=10)
    ax.legend()
    ax.set_ylim(0, 105)
    ax.grid(axis="y", alpha=0.3)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "taxa_falha_http.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_body_size_completeness(df: pd.DataFrame, output_dir: str):
    """Gráfico: Integridade do body recebido vs esperado por execução."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for file_size in sorted(df["file_size"].unique()):
        expected = EXPECTED_SIZES.get(file_size, 0)
        if expected == 0:
            continue
        
        sub = df[df["file_size"] == file_size]
        if sub.empty:
            continue
        
        body_sizes = sub["body_size"].fillna(sub["bytes"])
        completeness = body_sizes / expected * 100
        
        colors_proto = {"tcp": "#2196F3", "rudp": "#FF5722"}
        markers_proto = {"tcp": "o", "rudp": "s"}
        
        for proto in ["tcp", "rudp"]:
            proto_sub = sub[sub["protocol"] == proto]
            if proto_sub.empty:
                continue
            proto_comp = completeness[sub["protocol"] == proto]
            x_vals = range(len(proto_sub))
            
            ax.scatter(x_vals, proto_comp,
                       c=colors_proto.get(proto, "#333"),
                       marker=markers_proto.get(proto, "o"),
                       s=60, alpha=0.7, edgecolors="black", linewidth=0.5,
                       label=f"{proto.upper()} ({file_size})")
    
    ax.axhline(100, color="green", linestyle="--", linewidth=2, alpha=0.7,
               label="100% (completo)")
    ax.axhline(95, color="orange", linestyle=":", linewidth=1.5, alpha=0.5,
               label="95% (limiar aceitável)")
    
    ax.set_xlabel("Execução (índice)", fontsize=12)
    ax.set_ylabel("Integridade do Arquivo Recebido (%)", fontsize=12)
    ax.set_title("Integridade dos Dados Recebidos por Execução\n(Tamanho recebido / Tamanho esperado)",
                 fontsize=14, fontweight="bold")
    ax.legend(fontsize=9, loc="lower left")
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "integridade_por_execucao.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_transfer_time_analysis(df: pd.DataFrame, output_dir: str):
    """Gráfico: Tempo de transferência por execução (destaca outliers)."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors_proto = {"tcp": "#2196F3", "rudp": "#FF5722"}
    markers_proto = {"tcp": "o", "rudp": "s"}
    
    # Log scale para melhor visualização
    for proto in ["tcp", "rudp"]:
        sub = df[df["protocol"] == proto]
        if sub.empty:
            continue
        
        x_vals = range(len(sub))
        times = sub["time"].dropna()
        
        ax.scatter(x_vals, times, c=colors_proto.get(proto, "#333"),
                   marker=markers_proto.get(proto, "o"),
                   s=50, alpha=0.6, edgecolors="black", linewidth=0.3,
                   label=proto.upper())
    
    ax.set_yscale("log")
    ax.set_xlabel("Execução (índice)", fontsize=12)
    ax.set_ylabel("Tempo de Transferência (s) — escala log", fontsize=12)
    ax.set_title("Tempo de Transferência por Execução (escala logarítmica)\n"
                 "Outliers altos indicam retransmissões/timeouts não contabilizados",
                 fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, which="both")
    
    plt.tight_layout()
    path = os.path.join(output_dir, "tempo_transferencia_outliers.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_dns_failure_impact(df: pd.DataFrame, output_dir: str):
    """Gráfico: Impacto do tempo DNS no tempo total, e outliers de DNS."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    dns_times = df["dns_time"].dropna() * 1000  # em ms
    
    scenarios = sorted(df["scenario"].unique())
    colors = {"A": "#4CAF50", "B": "#FF9800", "C": "#f44336"}
    positions = []
    data_groups = []
    labels_scenario = []
    
    for i, scenario in enumerate(scenarios):
        dns_data = df[df["scenario"] == scenario]["dns_time"].dropna() * 1000
        if not dns_data.empty:
            positions.append(i + 1)
            data_groups.append(dns_data.values)
            labels_scenario.append(f"Cenário {scenario}")
    
    if not data_groups:
        plt.close()
        return
    
    bp = ax.boxplot(data_groups, positions=positions, patch_artist=True, widths=0.5)
    
    for i, patch in enumerate(bp["boxes"]):
        scenario = scenarios[i] if i < len(scenarios) else "A"
        patch.set_facecolor(colors.get(scenario, "#999"))
        patch.set_alpha(0.7)
    
    # Adiciona scatter dos pontos individuais
    for i, (pos, data) in enumerate(zip(positions, data_groups)):
        jitter = np.random.normal(0, 0.05, size=len(data))
        ax.scatter([pos + jitter[j] for j in range(len(data))], data,
                   alpha=0.5, s=30, color=colors.get(scenarios[i], "#333"),
                   edgecolors="black", linewidth=0.3, zorder=5)
    
    # Linha de timeout DNS
    ax.axhline(2000, color="red", linestyle="--", linewidth=2, alpha=0.7,
               label="Timeout DNS (2s)")
    
    ax.set_xlabel("Cenário de Rede", fontsize=12)
    ax.set_ylabel("Tempo de Resolução DNS (ms)", fontsize=12)
    ax.set_title("Tempo de Resolução DNS por Cenário\nOutliers próximos de 2000ms indicam consultas perdidas",
                 fontsize=14, fontweight="bold")
    ax.set_xticklabels(labels_scenario)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "dns_time_outliers.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_completeness_by_protocol(df: pd.DataFrame, output_dir: str):
    """Boxplot: Distribuição da integridade dos dados por protocolo e cenário."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    scenarios = sorted(df["scenario"].unique())
    protocols = ["tcp", "rudp"]
    
    positions = []
    data_groups = []
    labels = []
    colors_proto = {"tcp": "#2196F3", "rudp": "#FF5722"}
    
    pos = 1
    for scenario in scenarios:
        for proto in protocols:
            sub = df[(df["scenario"] == scenario) & (df["protocol"] == proto)]
            if sub.empty:
                continue
            
            body_sizes = sub["body_size"].fillna(sub["bytes"])
            expected = EXPECTED_SIZES.get(sub["file_size"].iloc[0], 102418)
            completeness = body_sizes / expected * 100
            
            positions.append(pos)
            data_groups.append(completeness.values)
            labels.append(f"{proto.upper()}\nCen {scenario}")
            pos += 1
    
    if not data_groups:
        plt.close()
        return
    
    bp = ax.boxplot(data_groups, positions=positions, patch_artist=True, widths=0.5)
    
    for i, patch in enumerate(bp["boxes"]):
        # Alterna cores entre TCP e RUDP
        is_tcp = "TCP" in labels[i]
        patch.set_facecolor("#2196F3" if is_tcp else "#FF5722")
        patch.set_alpha(0.7)
    
    ax.axhline(100, color="green", linestyle="--", linewidth=1.5, alpha=0.7, label="100% (completo)")
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Integridade do Arquivo Recebido (%)", fontsize=12)
    ax.set_title("Distribuição da Integridade dos Dados por Protocolo e Cenário",
                 fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "integridade_boxplot.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_comparison_table(df: pd.DataFrame, metrics: dict, output_dir: str):
    """Gera imagem de tabela comparativa com dados de falha."""
    fig, ax = plt.subplots(figsize=(16, 5))
    ax.axis("off")
    
    col_labels = [
        "Protocolo", "Cenário", "Arquivo",
        "Exec.\nTotal", "OK", "Falhas",
        "Tx. Falha\n(%)", "Integridade\nMédia (%)",
        "Retrans.\nEst. Total", "Timeouts\n(qtd)",
        "Tempo\nMédio (s)", "Tempo\nMáx (s)"
    ]
    
    cell_text = []
    for key in sorted(metrics.keys()):
        proto, scenario, file_size = key
        m = metrics[key]
        completeness_str = f"{m['completeness']:.1f}"
        
        cell_text.append([
            proto.upper(), f"Cenário {scenario}", file_size,
            str(m["total_runs"]),
            str(m["ok_runs"]),
            str(m["failed_runs"]),
            f"{m['failure_rate']:.1f}%",
            completeness_str,
            str(m["estimated_retransmissions"]),
            str(m["timeout_count"]),
            f"{m['mean_time']:.2f}" if not pd.isna(m['mean_time']) else "N/A",
            f"{m['max_time']:.2f}" if not pd.isna(m['max_time']) else "N/A",
        ])
    
    table = ax.table(cellText=cell_text, colLabels=col_labels,
                     loc="center", cellLoc="center")
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)
    
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(fontweight="bold", color="white")
            cell.set_facecolor("#333333")
        elif row > 0:
            proto = cell_text[row-1][0]
            if proto == "TCP":
                cell.set_facecolor("#E3F2FD")
            else:
                cell.set_facecolor("#FBE9E7")
    
    ax.set_title("Tabela Comparativa de Falhas e Erros — Trabalho II (HTTP + DNS)",
                 fontsize=14, fontweight="bold", pad=20)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "tabela_falhas_http.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  Salvo: {path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Análise de Erros/Falhas — Trabalho II")
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Caminho do CSV de resultados")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Diretório de saída dos gráficos")
    args = parser.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    print("=" * 60)
    print("  ANÁLISE DE ERROS, FALHAS E RETRANSMISSÕES")
    print("  Trabalho II — HTTP/1.1 (TCP vs R-UDP) + DNS")
    print("=" * 60)
    print(f"  CSV:    {args.csv}")
    print(f"  Output: {args.output}\n")
    
    df = load_data(args.csv)
    print(f"  {len(df)} registros carregados.\n")
    
    # Análise exploratória
    print("--- ANÁLISE EXPLORATÓRIA ---")
    print(f"Protocolos: {df['protocol'].unique()}")
    print(f"Cenários: {sorted(df['scenario'].unique())}")
    print(f"Arquivos: {sorted(df['file_size'].unique())}")
    
    # Verifica body_size vs bytes
    if "body_size" in df.columns and "bytes" in df.columns:
        mismatch = (df["body_size"].fillna(0) != df["bytes"].fillna(0)).sum()
        print(f"Registros com body_size ≠ bytes: {mismatch}/{len(df)}")
    
    # Verifica status codes diferentes de 200
    if "status_code" in df.columns:
        non_200 = (df["status_code"] != 200).sum()
        print(f"Status codes diferentes de 200: {non_200}")
    
    print()
    
    metrics = compute_metrics(df)
    
    # Tabela textual
    print_error_table(df, metrics)
    
    # Gráficos
    print("\n" + "=" * 60)
    print("  GERANDO GRÁFICOS")
    print("=" * 60)
    
    plot_failure_rate_per_scenario(df, metrics, args.output)
    plot_body_size_completeness(df, args.output)
    plot_transfer_time_analysis(df, args.output)
    plot_dns_failure_impact(df, args.output)
    plot_completeness_by_protocol(df, args.output)
    plot_comparison_table(df, metrics, args.output)
    
    print(f"\n  Todos os gráficos foram gerados em: {args.output}")


if __name__ == "__main__":
    main()
