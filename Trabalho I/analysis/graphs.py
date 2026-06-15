"""
graphs.py — Gera gráficos comparativos TCP vs R-UDP a partir do CSV de resultados.

Gráficos gerados:
  1. Throughput Médio por Cenário (barras agrupadas com desvio padrão)
  2. Tempo Médio por Cenário (barras agrupadas com desvio padrão)
  3. Retransmissões R-UDP por Cenário
  4. Boxplot de Throughput por Protocolo e Cenário

USO:
    python3 analysis/graphs.py
    python3 analysis/graphs.py --csv logs/results.csv --output analysis/plots/
"""

import os
import sys
import argparse

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # Backend não-interativo para gerar PNG em servidor/container

# Diretório raiz do projeto
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DEFAULT_CSV = os.path.join(ROOT, "logs", "results.csv")
DEFAULT_OUTPUT = os.path.join(ROOT, "analysis", "plots")


def load_data(csv_path: str) -> pd.DataFrame:
    """Carrega o CSV de resultados."""
    df = pd.read_csv(csv_path)
    # Garante tipos numéricos
    df["time"] = pd.to_numeric(df["time"])
    df["throughput"] = pd.to_numeric(df["throughput"])
    df["retransmissions"] = pd.to_numeric(df["retransmissions"])
    return df


def plot_throughput_bar(df: pd.DataFrame, output_dir: str):
    """Gráfico de barras: Throughput Médio ± Desvio Padrão por cenário."""
    fig, ax = plt.subplots(figsize=(10, 6))

    grouped = df.groupby(["scenario", "protocol"])["throughput"].agg(["mean", "std"]).reset_index()

    scenarios = sorted(df["scenario"].unique())
    protocols = ["tcp", "rudp"]
    x = range(len(scenarios))
    width = 0.35
    colors = {"tcp": "#2196F3", "rudp": "#FF5722"}

    for i, proto in enumerate(protocols):
        proto_data = grouped[grouped["protocol"] == proto]
        means = [proto_data[proto_data["scenario"] == s]["mean"].values[0] if s in proto_data["scenario"].values else 0 for s in scenarios]
        stds = [proto_data[proto_data["scenario"] == s]["std"].values[0] if s in proto_data["scenario"].values else 0 for s in scenarios]
        offset = (i - 0.5) * width
        bars = ax.bar([xi + offset for xi in x], means, width, yerr=stds,
                      label=proto.upper(), color=colors[proto], capsize=5, alpha=0.85)

    ax.set_xlabel("Cenário de Rede", fontsize=12)
    ax.set_ylabel("Throughput (bytes/s)", fontsize=12)
    ax.set_title("Throughput Médio — TCP vs R-UDP", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Cenário {s}" for s in scenarios])
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, "throughput_por_cenario.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_time_bar(df: pd.DataFrame, output_dir: str):
    """Gráfico de barras: Tempo Médio ± Desvio Padrão por cenário."""
    fig, ax = plt.subplots(figsize=(10, 6))

    grouped = df.groupby(["scenario", "protocol"])["time"].agg(["mean", "std"]).reset_index()

    scenarios = sorted(df["scenario"].unique())
    protocols = ["tcp", "rudp"]
    x = range(len(scenarios))
    width = 0.35
    colors = {"tcp": "#2196F3", "rudp": "#FF5722"}

    for i, proto in enumerate(protocols):
        proto_data = grouped[grouped["protocol"] == proto]
        means = [proto_data[proto_data["scenario"] == s]["mean"].values[0] if s in proto_data["scenario"].values else 0 for s in scenarios]
        stds = [proto_data[proto_data["scenario"] == s]["std"].values[0] if s in proto_data["scenario"].values else 0 for s in scenarios]
        offset = (i - 0.5) * width
        ax.bar([xi + offset for xi in x], means, width, yerr=stds,
               label=proto.upper(), color=colors[proto], capsize=5, alpha=0.85)

    ax.set_xlabel("Cenário de Rede", fontsize=12)
    ax.set_ylabel("Tempo (segundos)", fontsize=12)
    ax.set_title("Tempo Médio de Transferência — TCP vs R-UDP", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Cenário {s}" for s in scenarios])
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, "tempo_por_cenario.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_retransmissions(df: pd.DataFrame, output_dir: str):
    """Gráfico de barras: Retransmissões do R-UDP por cenário."""
    fig, ax = plt.subplots(figsize=(8, 5))

    rudp_data = df[df["protocol"] == "rudp"]
    if rudp_data.empty:
        print("  AVISO: Nenhum dado R-UDP para gráfico de retransmissões.")
        plt.close()
        return

    grouped = rudp_data.groupby("scenario")["retransmissions"].agg(["mean", "std"]).reset_index()

    scenarios = sorted(grouped["scenario"].unique())
    x = range(len(scenarios))

    ax.bar(x, grouped["mean"], yerr=grouped["std"],
           color="#FF9800", capsize=5, alpha=0.85)

    ax.set_xlabel("Cenário de Rede", fontsize=12)
    ax.set_ylabel("Retransmissões (média)", fontsize=12)
    ax.set_title("Retransmissões R-UDP por Cenário", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Cenário {s}" for s in scenarios])
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, "retransmissoes_rudp.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_boxplot(df: pd.DataFrame, output_dir: str):
    """Boxplot de Throughput separado por protocolo e cenário."""
    fig, axes = plt.subplots(1, len(df["scenario"].unique()), figsize=(14, 6), sharey=True)

    scenarios = sorted(df["scenario"].unique())
    colors = {"tcp": "#2196F3", "rudp": "#FF5722"}

    if len(scenarios) == 1:
        axes = [axes]

    for i, scenario in enumerate(scenarios):
        ax = axes[i]
        scenario_data = df[df["scenario"] == scenario]

        data_to_plot = []
        labels = []
        box_colors = []
        for proto in ["tcp", "rudp"]:
            proto_data = scenario_data[scenario_data["protocol"] == proto]["throughput"]
            if not proto_data.empty:
                data_to_plot.append(proto_data.values)
                labels.append(proto.upper())
                box_colors.append(colors[proto])

        bp = ax.boxplot(data_to_plot, labels=labels, patch_artist=True)
        for patch, color in zip(bp["boxes"], box_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        ax.set_title(f"Cenário {scenario}", fontsize=12, fontweight="bold")
        ax.set_ylabel("Throughput (bytes/s)" if i == 0 else "")
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle("Distribuição do Throughput — TCP vs R-UDP", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(output_dir, "boxplot_throughput.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_degradation_dual(df: pd.DataFrame, output_dir: str):
    """Gera um gráfico de linha com eixo Y duplo mostrando a degradação de vazão."""
    fig, ax1 = plt.subplots(figsize=(10, 6))

    scenarios = sorted(df["scenario"].unique())
    x = range(len(scenarios))

    # Calcula médias
    tcp_means = [df[(df["protocol"] == "tcp") & (df["scenario"] == s)]["throughput"].mean() / (1024*1024) for s in scenarios]
    rudp_means = [df[(df["protocol"] == "rudp") & (df["scenario"] == s)]["throughput"].mean() / 1024 for s in scenarios]

    color = '#2196F3'
    ax1.set_xlabel('Cenário de Rede', fontsize=12)
    ax1.set_ylabel('Vazão TCP (MB/s)', color=color, fontsize=12)
    line1 = ax1.plot(x, tcp_means, marker='o', linewidth=2.5, color=color, label='TCP (Eixo Esq.)')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(True, alpha=0.3)

    ax2 = ax1.twinx()  
    color = '#FF5722'
    ax2.set_ylabel('Vazão R-UDP (KB/s)', color=color, fontsize=12)
    line2 = ax2.plot(x, rudp_means, marker='s', linewidth=2.5, color=color, linestyle='--', label='R-UDP (Eixo Dir.)')
    ax2.tick_params(axis='y', labelcolor=color)

    # Legenda única para ambos
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper right')

    plt.title("Curva de Degradação da Vazão (TCP vs R-UDP)", fontsize=14, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"Cenário {s}" for s in scenarios])

    plt.tight_layout()
    path = os.path.join(output_dir, "degradacao_throughput_dual_axis.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_rudp_vs_theory(df: pd.DataFrame, output_dir: str):
    """Compara o tempo experimental médio do R-UDP com a teoria do Stop-and-Wait."""
    fig, ax = plt.subplots(figsize=(10, 6))

    scenarios = sorted(df["scenario"].unique())
    x = np_range = [0, 1, 2] # Cenários A, B, C
    width = 0.35

    # Tempos experimentais
    rudp_exp_means = [df[(df["protocol"] == "rudp") & (df["scenario"] == s)]["time"].mean() for s in scenarios]
    rudp_exp_stds = [df[(df["protocol"] == "rudp") & (df["scenario"] == s)]["time"].std() for s in scenarios]

    # Tempos teóricos: 6 pacotes * (delay + (perda/(1-perda)) * Timeout)
    # Cenário A: loss=0, delay=10ms (0.010s), timeout=1.0s -> 6 * 0.010 = 0.060s
    # Cenário B: loss=0.05, delay=50ms (0.050s), timeout=1.0s -> 6 * (0.050 + (0.05/0.95)*1.0) = 0.6158s
    # Cenário C: loss=0.10, delay=100ms (0.100s), timeout=1.0s -> 6 * (0.100 + (0.10/0.90)*1.0) = 1.2667s
    theoretical_times = [
        6 * 0.010,
        6 * (0.050 + (0.05/0.95) * 1.0),
        6 * (0.100 + (0.10/0.90) * 1.0)
    ]

    ax.bar([xi - width/2 for xi in x], rudp_exp_means, width, yerr=rudp_exp_stds,
           label='R-UDP Experimental', color='#FF9800', capsize=5, alpha=0.85)
    
    ax.bar([xi + width/2 for xi in x], theoretical_times, width,
           label='Teoria Stop-and-Wait', color='#9E9E9E', alpha=0.75, hatch='//')

    ax.set_xlabel("Cenário de Rede", fontsize=12)
    ax.set_ylabel("Tempo de Transferência (segundos)", fontsize=12)
    ax.set_title("Tempo R-UDP: Experimental vs. Teoria Matemática", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Cenário {s}" for s in scenarios])
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, "tempo_rudp_vs_teoria.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Geração de gráficos do benchmark")
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Caminho do CSV de resultados")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Diretório de saída dos gráficos")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    print("=" * 50)
    print("  Geração de Gráficos — TCP vs R-UDP")
    print("=" * 50)
    print(f"  CSV:    {args.csv}")
    print(f"  Output: {args.output}\n")

    df = load_data(args.csv)
    print(f"  {len(df)} registros carregados.\n")

    plot_throughput_bar(df, args.output)
    plot_time_bar(df, args.output)
    plot_retransmissions(df, args.output)
    plot_boxplot(df, args.output)
    plot_degradation_dual(df, args.output)
    plot_rudp_vs_theory(df, args.output)

    print(f"\n  Todos os gráficos foram gerados em: {args.output}")


if __name__ == "__main__":
    main()
