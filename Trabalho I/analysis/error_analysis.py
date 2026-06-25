"""
error_analysis.py — Análise de Erros, Falhas e Retransmissões (Trabalho I)

Gera gráficos e tabelas a partir de logs/results.csv:
  1. Retransmissões R-UDP por Cenário (média + desvio)
  2. Distribuição de Retransmissões por execução (histograma)
  3. Taxa de Falha (% de execuções com retransmissão > 0)
  4. Comparativo TCP vs RUDP: Tabela de Erros
  5. Packet Error Rate (retransmissões / total de pacotes enviados)
  6. Scatter plot: Retransmissões vs Throughput

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


def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_numeric(df["time"])
    df["throughput"] = pd.to_numeric(df["throughput"])
    df["retransmissions"] = pd.to_numeric(df["retransmissions"])
    return df


def compute_metrics(df: pd.DataFrame) -> dict:
    """Calcula métricas de erro/falha/retransmissão para cada (protocolo, cenário)."""
    metrics = {}
    
    FILE_SIZE_BYTES = 4994
    MAX_PAYLOAD = 1024
    BASE_PACKETS = math.ceil(FILE_SIZE_BYTES / MAX_PAYLOAD) + 1  # +1 for FIN
    
    for (proto, scenario), group in df.groupby(["protocol", "scenario"]):
        total_runs = len(group)
        retrans = group["retransmissions"]
        
        # Retransmission stats
        mean_ret = retrans.mean()
        std_ret = retrans.std()
        max_ret = retrans.max()
        total_ret = retrans.sum()
        
        # Failure rate: proportion of runs with 1+ retransmissions
        failed_runs = (retrans > 0).sum()
        failure_rate = failed_runs / total_runs * 100
        
        # Packet Error Rate: retransmissions / total packets sent
        total_packets_sent = BASE_PACKETS * total_runs + total_ret
        packet_error_rate = total_ret / max(total_packets_sent, 1) * 100
        
        # Error-free runs
        clean_runs = (retrans == 0).sum()
        clean_rate = clean_runs / total_runs * 100
        
        metrics[(proto, scenario)] = {
            "total_runs": total_runs,
            "mean_ret": mean_ret,
            "std_ret": std_ret,
            "max_ret": max_ret,
            "total_ret": int(total_ret),
            "failed_runs": int(failed_runs),
            "failure_rate": failure_rate,
            "clean_runs": int(clean_runs),
            "clean_rate": clean_rate,
            "packet_error_rate": packet_error_rate,
            "base_packets": BASE_PACKETS,
        }
    
    return metrics


def print_error_table(df: pd.DataFrame, metrics: dict):
    """Imprime tabela detalhada de erros, falhas e retransmissões."""
    scenarios = sorted(df["scenario"].unique())
    protocols = ["tcp", "rudp"]
    
    print("=" * 110)
    print("  TABELA DE ANÁLISE DE ERROS, FALHAS E RETRANSMISSÕES — TRABALHO I")
    print("  Protocolo: Arquivo de 4994 bytes (5 pacotes dados + 1 FIN = 6 pacotes base)")
    print("=" * 110)
    
    header = f"{'Protocolo':<10} {'Cenário':<10} {'Execuções':<10} {'Retrans. Média':<15} {'Retrans. Máx':<13} {'Retrans. Total':<15} {'Qtd. Falhas':<12} {'Tx. Falha (%)':<15} {'Tx. Erro Pacote (%)':<18} {'Exec. Limpas (%)':<18}"
    print(header)
    print("-" * 110)
    
    for scenario in scenarios:
        for proto in protocols:
            key = (proto, scenario)
            if key not in metrics:
                continue
            m = metrics[key]
            print(
                f"{proto:<10} {scenario:<10} "
                f"{m['total_runs']:<10} "
                f"{m['mean_ret']:<15.2f} "
                f"{m['max_ret']:<13.0f} "
                f"{m['total_ret']:<15} "
                f"{m['failed_runs']:<12} "
                f"{m['failure_rate']:<15.2f} "
                f"{m['packet_error_rate']:<18.2f} "
                f"{m['clean_rate']:<18.1f}"
            )
    
    print("-" * 110)
    print()
    
    # Análise textual
    print("=" * 60)
    print("  ANÁLISE DOS RESULTADOS")
    print("=" * 60)
    
    for scenario in scenarios:
        rudp_key = ("rudp", scenario)
        tcp_key = ("tcp", scenario)
        if rudp_key in metrics:
            m = metrics[rudp_key]
            total_ret = m["total_ret"]
            print(f"\n  Cenário {scenario} ({scenario_labels.get(scenario, '')}):")
            print(f"    R-UDP: {m['failed_runs']}/{m['total_runs']} execuções com falha "
                  f"({m['failure_rate']:.1f}% taxa de falha)")
            print(f"    Retransmissões totais: {total_ret} | "
                  f"Média: {m['mean_ret']:.2f} | Máx: {m['max_ret']:.0f}")
            
            # Cálculo de retransmissões extras devido ao cenário
            expected_time_no_loss = {"A": 0.060, "B": 0.6158, "C": 1.2667}
            if scenario in expected_time_no_loss:
                exp_time = expected_time_no_loss[scenario]
                print(f"    Tempo teórico esperado (Stop-and-Wait): {exp_time:.4f}s")
        
        if tcp_key in metrics:
            m = metrics[tcp_key]
            print(f"    TCP: {m['clean_runs']}/{m['total_runs']} execuções sem erros "
                  f"({m['clean_rate']:.1f}%) — 0 retransmissões visíveis")


scenario_labels = {
    "A": "0% perda / 10ms delay",
    "B": "5% perda / 50ms delay",
    "C": "10% perda / 100ms delay",
}


def plot_retransmission_comparison(df: pd.DataFrame, output_dir: str):
    """Gráfico de barras: Retransmissões Médias ± Desvio por cenário (apenas RUDP)."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    rudp = df[df["protocol"] == "rudp"]
    if rudp.empty:
        plt.close()
        return
    
    grouped = rudp.groupby("scenario")["retransmissions"].agg(["mean", "std", "max"]).reset_index()
    scenarios = sorted(grouped["scenario"].unique())
    x = np.arange(len(scenarios))
    width = 0.5
    
    # Barras com média
    bars = ax.bar(x, grouped["mean"], width, yerr=grouped["std"],
                  color="#FF5722", capsize=8, alpha=0.85,
                  edgecolor="black", linewidth=1.2,
                  label="Média de Retransmissões")
    
    # Marca o valor máximo em cada barra
    for i, (_, row) in enumerate(grouped.iterrows()):
        ax.text(i, row["mean"] + row["std"] + 0.15, f"Máx: {row['max']:.0f}",
                ha="center", fontsize=10, fontweight="bold", color="#B71C1C")
        ax.text(i, -0.3, f"n={int(rudp[rudp['scenario'] == row['scenario']].count()['retransmissions'])}",
                ha="center", fontsize=9, color="gray")
    
    ax.set_xlabel("Cenário de Rede", fontsize=12)
    ax.set_ylabel("Retransmissões", fontsize=12)
    ax.set_title("Retransmissões R-UDP por Cenário — Média ± Desvio Padrão", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Cenário {s}\n({scenario_labels.get(s, '')})" for s in scenarios],
                       fontsize=10)
    ax.legend(loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "retransmissoes_rudp_media.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_retransmission_histogram(df: pd.DataFrame, output_dir: str):
    """Histograma: Distribuição das retransmissões por cenário (RUDP)."""
    rudp = df[df["protocol"] == "rudp"]
    if rudp.empty:
        return
    
    scenarios = sorted(rudp["scenario"].unique())
    fig, axes = plt.subplots(1, len(scenarios), figsize=(14, 5), sharey=True)
    
    if len(scenarios) == 1:
        axes = [axes]
    
    colors = {"A": "#4CAF50", "B": "#FF9800", "C": "#f44336"}
    
    for i, scenario in enumerate(scenarios):
        ax = axes[i]
        data = rudp[rudp["scenario"] == scenario]["retransmissions"]
        
        bins = range(0, int(data.max()) + 2)
        ax.hist(data, bins=bins, color=colors.get(scenario, "#2196F3"),
                alpha=0.8, edgecolor="black", linewidth=1.2)
        
        mean_val = data.mean()
        ax.axvline(mean_val, color="black", linestyle="--", linewidth=2,
                   label=f"Média: {mean_val:.2f}")
        
        ax.set_xlabel("Retransmissões", fontsize=11)
        ax.set_ylabel("Frequência" if i == 0 else "", fontsize=11)
        ax.set_title(f"Cenário {scenario}", fontsize=13, fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(axis="y", alpha=0.3)
    
    fig.suptitle("Distribuição das Retransmissões R-UDP por Cenário",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(output_dir, "retransmissoes_histograma.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_failure_rate(df: pd.DataFrame, output_dir: str):
    """Gráfico de barras: Taxa de Falha (% execuções com retransmissão > 0) por protocolo+cenário."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    scenarios = sorted(df["scenario"].unique())
    protocols = ["tcp", "rudp"]
    x = np.arange(len(scenarios))
    width = 0.35
    colors = {"tcp": "#2196F3", "rudp": "#FF5722"}
    
    for i, proto in enumerate(protocols):
        failure_rates = []
        for scenario in scenarios:
            sub = df[(df["protocol"] == proto) & (df["scenario"] == scenario)]
            if not sub.empty:
                failed = (sub["retransmissions"] > 0).sum()
                rate = failed / len(sub) * 100
                failure_rates.append(rate)
            else:
                failure_rates.append(0)
        
        offset = (i - 0.5) * width
        bars = ax.bar([xi + offset for xi in x], failure_rates, width,
                      label=proto.upper(), color=colors[proto], alpha=0.85,
                      edgecolor="black", linewidth=0.8)
        
        # Labels nas barras
        for bar, rate in zip(bars, failure_rates):
            if rate > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f"{rate:.1f}%", ha="center", fontsize=10, fontweight="bold")
    
    ax.set_xlabel("Cenário de Rede", fontsize=12)
    ax.set_ylabel("Taxa de Falha (%)", fontsize=12)
    ax.set_title("Taxa de Falha por Protocolo e Cenário\n(% de execuções com retransmissão)",
                 fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Cenário {s}\n({scenario_labels.get(s, '')})" for s in scenarios],
                       fontsize=10)
    ax.legend()
    ax.set_ylim(0, 105)
    ax.grid(axis="y", alpha=0.3)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "taxa_falha_por_cenario.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_packet_error_rate(df: pd.DataFrame, output_dir: str):
    """Gráfico: Packet Error Rate (retransmissões / total pacotes enviados) por cenário (RUDP)."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    FILE_SIZE_BYTES = 4994
    MAX_PAYLOAD = 1024
    BASE_PACKETS = math.ceil(FILE_SIZE_BYTES / MAX_PAYLOAD) + 1  # 6
    
    rudp = df[df["protocol"] == "rudp"]
    if rudp.empty:
        plt.close()
        return
    
    scenarios = sorted(rudp["scenario"].unique())
    x = np.arange(len(scenarios))
    width = 0.5
    
    per_values = []
    for scenario in scenarios:
        sub = rudp[rudp["scenario"] == scenario]
        total_ret = sub["retransmissions"].sum()
        total_runs = len(sub)
        total_packets = BASE_PACKETS * total_runs + total_ret
        per = total_ret / max(total_packets, 1) * 100
        per_values.append(per)
    
    # Perda de pacote simulada pelo tc (para comparação)
    simulated_loss = {"A": 0, "B": 5, "C": 10}
    sim_values = [simulated_loss.get(s, 0) for s in scenarios]
    
    bars = ax.bar(x, per_values, width, color="#FF9800", alpha=0.85,
                  edgecolor="black", linewidth=1.2,
                  label="Packet Error Rate (R-UDP)")
    
    # Linha de perda simulada
    ax.plot(x, sim_values, marker="D", linewidth=2.5, color="#2196F3",
            linestyle="--", markersize=8, label="Perda Simulada (tc netem)")
    
    # Labels
    for bar, per, sim in zip(bars, per_values, sim_values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f"{per:.2f}%", ha="center", fontsize=11, fontweight="bold")
        ax.text(bar.get_x() + bar.get_width()/2, sim + 0.3,
                f"tc: {sim}%", ha="center", fontsize=9, color="#2196F3",
                fontweight="bold")
    
    ax.set_xlabel("Cenário de Rede", fontsize=12)
    ax.set_ylabel("Taxa de Erro (%)", fontsize=12)
    ax.set_title("Packet Error Rate do R-UDP vs Perda Simulada na Rede",
                 fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Cenário {s}\n({scenario_labels.get(s, '')})" for s in scenarios],
                       fontsize=10)
    ax.legend(loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "packet_error_rate.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_retransmissions_vs_throughput(df: pd.DataFrame, output_dir: str):
    """Scatter plot: Retransmissões vs Throughput para RUDP."""
    rudp = df[df["protocol"] == "rudp"]
    if rudp.empty:
        return
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    scenarios = sorted(rudp["scenario"].unique())
    colors = {"A": "#4CAF50", "B": "#FF9800", "C": "#f44336"}
    markers = {"A": "o", "B": "s", "C": "^"}
    
    for scenario in scenarios:
        sub = rudp[rudp["scenario"] == scenario]
        ax.scatter(sub["retransmissions"], sub["throughput"] / 1024,  # KB/s
                   c=colors.get(scenario, "#333"), marker=markers.get(scenario, "o"),
                   s=80, alpha=0.7, edgecolors="black", linewidth=0.5,
                   label=f"Cenário {scenario}")
    
    ax.set_xlabel("Retransmissões", fontsize=12)
    ax.set_ylabel("Throughput (KB/s)", fontsize=12)
    ax.set_title("Relação: Retransmissões vs Throughput (R-UDP)", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "retransmissoes_vs_throughput.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_comparison_table(df: pd.DataFrame, metrics: dict, output_dir: str):
    """Gera uma imagem de tabela comparativa com os dados de erro."""
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.axis("off")
    
    scenarios = sorted(df["scenario"].unique())
    protocols = ["tcp", "rudp"]
    
    col_labels = [
        "Protocolo", "Cenário", "Execuções",
        "Retrans.\nMédia", "Retrans.\nMáx", "Retrans.\nTotal",
        "Falhas\n(qtd)", "Tx. Falha\n(%)", "Tx. Erro\nPacote (%)", "Exec.\nLimpas (%)"
    ]
    
    cell_text = []
    for scenario in scenarios:
        for proto in protocols:
            key = (proto, scenario)
            if key not in metrics:
                continue
            m = metrics[key]
            cell_text.append([
                proto.upper(), f"Cenário {scenario}",
                str(m["total_runs"]),
                f"{m['mean_ret']:.2f}",
                f"{m['max_ret']:.0f}",
                str(m["total_ret"]),
                str(m["failed_runs"]),
                f"{m['failure_rate']:.1f}%",
                f"{m['packet_error_rate']:.2f}%",
                f"{m['clean_rate']:.1f}%",
            ])
    
    table = ax.table(cellText=cell_text, colLabels=col_labels,
                     loc="center", cellLoc="center")
    
    # Estilo da tabela
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)
    
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(fontweight="bold", color="white")
            cell.set_facecolor("#333333")
        elif cell_text[row-1][0] == "TCP":
            cell.set_facecolor("#E3F2FD")  # Azul claro
        else:
            cell.set_facecolor("#FBE9E7")  # Laranja claro
    
    ax.set_title("Tabela Comparativa de Erros, Falhas e Retransmissões — Trabalho I",
                 fontsize=14, fontweight="bold", pad=20)
    
    plt.tight_layout()
    path = os.path.join(output_dir, "tabela_erros.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  Salvo: {path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Análise de Erros/Falhas/Retransmissões — Trabalho I")
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Caminho do CSV de resultados")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Diretório de saída dos gráficos")
    args = parser.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    print("=" * 60)
    print("  ANÁLISE DE ERROS, FALHAS E RETRANSMISSÕES")
    print("  Trabalho I — Transferência de Arquivos (TCP vs R-UDP)")
    print("=" * 60)
    print(f"  CSV:    {args.csv}")
    print(f"  Output: {args.output}\n")
    
    df = load_data(args.csv)
    print(f"  {len(df)} registros carregados.\n")
    
    metrics = compute_metrics(df)
    
    # Tabela textual
    print_error_table(df, metrics)
    
    # Gráficos
    print("\n" + "=" * 60)
    print("  GERANDO GRÁFICOS")
    print("=" * 60)
    
    plot_retransmission_comparison(df, args.output)
    plot_retransmission_histogram(df, args.output)
    plot_failure_rate(df, args.output)
    plot_packet_error_rate(df, args.output)
    plot_retransmissions_vs_throughput(df, args.output)
    plot_comparison_table(df, metrics, args.output)
    
    print(f"\n  Todos os gráficos foram gerados em: {args.output}")


if __name__ == "__main__":
    main()
