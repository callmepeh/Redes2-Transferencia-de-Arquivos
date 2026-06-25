"""
graphs.py — Gera gráficos comparativos do Trabalho II.
HTTP/1.1 (TCP vs R-UDP) com Resolução DNS.

Gráficos gerados:
  1. Throughput Médio por Cenário (barras agrupadas com desvio padrão)
  2. Tempo Médio por Cenário (barras agrupadas com desvio padrão)
  3. Retransmissões R-UDP por Cenário
  4. Boxplot de Throughput por Protocolo e Cenário
  5. Curva de Degradação (eixo Y duplo)
  6. Tempo de Resolução DNS por Cenário
  7. Tempo Total (DNS + HTTP) por Cenário

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
matplotlib.use("Agg")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DEFAULT_CSV = os.path.join(ROOT, "logs", "results.csv")
DEFAULT_OUTPUT = os.path.join(ROOT, "analysis", "plots")


def load_data(csv_path: str) -> pd.DataFrame:
    """Carrega o CSV de resultados."""
    df = pd.read_csv(csv_path)
    # Garante tipos numéricos
    for col in ["time", "throughput", "retransmissions", "dns_time"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def plot_throughput_bar(df: pd.DataFrame, output_dir: str):
    """Gráfico de barras: Throughput Médio ± Desvio Padrão por cenário e tamanho."""
    for file_size in sorted(df["file_size"].unique()):
        sub = df[df["file_size"] == file_size]
        fig, ax = plt.subplots(figsize=(10, 6))

        grouped = sub.groupby(["scenario", "protocol"])["throughput"]\
                    .agg(["mean", "std"]).reset_index()

        scenarios = sorted(sub["scenario"].unique())
        protocols = ["tcp", "rudp"]
        x = range(len(scenarios))
        width = 0.35
        colors = {"tcp": "#2196F3", "rudp": "#FF5722"}

        for i, proto in enumerate(protocols):
            proto_data = grouped[grouped["protocol"] == proto]
            means = [
                proto_data[proto_data["scenario"] == s]["mean"].values[0]
                if s in proto_data["scenario"].values else 0
                for s in scenarios
            ]
            stds = [
                proto_data[proto_data["scenario"] == s]["std"].values[0]
                if s in proto_data["scenario"].values else 0
                for s in scenarios
            ]
            offset = (i - 0.5) * width
            ax.bar([xi + offset for xi in x], means, width, yerr=stds,
                   label=proto.upper(), color=colors[proto], capsize=5, alpha=0.85)

        ax.set_xlabel("Cenário de Rede", fontsize=12)
        ax.set_ylabel("Throughput (bytes/s)", fontsize=12)
        ax.set_title(f"Throughput Médio — HTTP TCP vs R-UDP ({file_size})",
                     fontsize=14, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([f"Cenário {s}" for s in scenarios])
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

        plt.tight_layout()
        path = os.path.join(output_dir, f"throughput_por_cenario_{file_size}.png")
        plt.savefig(path, dpi=150)
        print(f"  Salvo: {path}")
        plt.close()


def plot_time_bar(df: pd.DataFrame, output_dir: str):
    """Gráfico de barras: Tempo Médio ± Desvio Padrão por cenário."""
    for file_size in sorted(df["file_size"].unique()):
        sub = df[df["file_size"] == file_size]
        fig, ax = plt.subplots(figsize=(10, 6))

        grouped = sub.groupby(["scenario", "protocol"])["time"]\
                    .agg(["mean", "std"]).reset_index()

        scenarios = sorted(sub["scenario"].unique())
        protocols = ["tcp", "rudp"]
        x = range(len(scenarios))
        width = 0.35
        colors = {"tcp": "#2196F3", "rudp": "#FF5722"}

        for i, proto in enumerate(protocols):
            proto_data = grouped[grouped["protocol"] == proto]
            means = [
                proto_data[proto_data["scenario"] == s]["mean"].values[0]
                if s in proto_data["scenario"].values else 0
                for s in scenarios
            ]
            stds = [
                proto_data[proto_data["scenario"] == s]["std"].values[0]
                if s in proto_data["scenario"].values else 0
                for s in scenarios
            ]
            offset = (i - 0.5) * width
            ax.bar([xi + offset for xi in x], means, width, yerr=stds,
                   label=proto.upper(), color=colors[proto], capsize=5, alpha=0.85)

        ax.set_xlabel("Cenário de Rede", fontsize=12)
        ax.set_ylabel("Tempo (segundos)", fontsize=12)
        ax.set_title(f"Tempo Médio de Transferência — HTTP TCP vs R-UDP ({file_size})",
                     fontsize=14, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([f"Cenário {s}" for s in scenarios])
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

        plt.tight_layout()
        path = os.path.join(output_dir, f"tempo_por_cenario_{file_size}.png")
        plt.savefig(path, dpi=150)
        print(f"  Salvo: {path}")
        plt.close()


def plot_retransmissions(df: pd.DataFrame, output_dir: str):
    """Gráfico de barras: Retransmissões do R-UDP por cenário e tamanho."""
    for file_size in sorted(df["file_size"].unique()):
        sub = df[(df["protocol"] == "rudp") & (df["file_size"] == file_size)]
        if sub.empty:
            continue

        fig, ax = plt.subplots(figsize=(8, 5))

        grouped = sub.groupby("scenario")["retransmissions"]\
                    .agg(["mean", "std"]).reset_index()

        scenarios = sorted(grouped["scenario"].unique())
        x = range(len(scenarios))

        ax.bar(x, grouped["mean"], yerr=grouped["std"],
               color="#FF9800", capsize=5, alpha=0.85)

        ax.set_xlabel("Cenário de Rede", fontsize=12)
        ax.set_ylabel("Retransmissões (média)", fontsize=12)
        ax.set_title(f"Retransmissões R-UDP por Cenário ({file_size})",
                     fontsize=14, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([f"Cenário {s}" for s in scenarios])
        ax.grid(axis="y", alpha=0.3)

        plt.tight_layout()
        path = os.path.join(output_dir, f"retransmissoes_rudp_{file_size}.png")
        plt.savefig(path, dpi=150)
        print(f"  Salvo: {path}")
        plt.close()


def plot_boxplot(df: pd.DataFrame, output_dir: str):
    """Boxplot de Throughput separado por protocolo e cenário."""
    for file_size in sorted(df["file_size"].unique()):
        sub = df[df["file_size"] == file_size]
        fig, axes = plt.subplots(1, len(sub["scenario"].unique()),
                                 figsize=(14, 6), sharey=True)

        scenarios = sorted(sub["scenario"].unique())
        colors = {"tcp": "#2196F3", "rudp": "#FF5722"}

        if len(scenarios) == 1:
            axes = [axes]

        for i, scenario in enumerate(scenarios):
            ax = axes[i]
            scenario_data = sub[sub["scenario"] == scenario]

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

        fig.suptitle(f"Distribuição do Throughput — HTTP TCP vs R-UDP ({file_size})",
                     fontsize=14, fontweight="bold")
        plt.tight_layout()
        path = os.path.join(output_dir, f"boxplot_throughput_{file_size}.png")
        plt.savefig(path, dpi=150)
        print(f"  Salvo: {path}")
        plt.close()


def plot_degradation_dual(df: pd.DataFrame, output_dir: str):
    """Gráfico de linha com eixo Y duplo mostrando degradação."""
    for file_size in sorted(df["file_size"].unique()):
        sub = df[df["file_size"] == file_size]
        fig, ax1 = plt.subplots(figsize=(10, 6))

        scenarios = sorted(sub["scenario"].unique())
        x = range(len(scenarios))

        tcp_means = [
            sub[(sub["protocol"] == "tcp") & (sub["scenario"] == s)]["throughput"].mean() / (1024*1024)
            for s in scenarios
        ]
        rudp_means = [
            sub[(sub["protocol"] == "rudp") & (sub["scenario"] == s)]["throughput"].mean() / 1024
            for s in scenarios
        ]

        color = '#2196F3'
        ax1.set_xlabel('Cenário de Rede', fontsize=12)
        ax1.set_ylabel('Vazão TCP (MB/s)', color=color, fontsize=12)
        line1 = ax1.plot(x, tcp_means, marker='o', linewidth=2.5, color=color,
                         label='TCP (Eixo Esq.)')
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.grid(True, alpha=0.3)

        ax2 = ax1.twinx()
        color = '#FF5722'
        ax2.set_ylabel('Vazão R-UDP (KB/s)', color=color, fontsize=12)
        line2 = ax2.plot(x, rudp_means, marker='s', linewidth=2.5, color=color,
                         linestyle='--', label='R-UDP (Eixo Dir.)')
        ax2.tick_params(axis='y', labelcolor=color)

        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper right')

        plt.title(f"Curva de Degradação da Vazão — HTTP ({file_size})",
                  fontsize=14, fontweight="bold")
        ax1.set_xticks(x)
        ax1.set_xticklabels([f"Cenário {s}" for s in scenarios])

        plt.tight_layout()
        path = os.path.join(output_dir, f"degradacao_throughput_dual_axis_{file_size}.png")
        plt.savefig(path, dpi=150)
        print(f"  Salvo: {path}")
        plt.close()


def plot_dns_time(df: pd.DataFrame, output_dir: str):
    """Gráfico de barras: Tempo de resolução DNS por cenário."""
    fig, ax = plt.subplots(figsize=(8, 5))

    # Agrupa por cenário e calcula média do tempo DNS
    dns_grouped = df.groupby("scenario")["dns_time"].mean().reset_index()
    scenarios = sorted(dns_grouped["scenario"].unique())
    x = range(len(scenarios))

    colors_scenario = ["#4CAF50", "#FF9800", "#f44336"]
    ax.bar(x, dns_grouped["dns_time"] * 1000, color=colors_scenario,
           alpha=0.85, width=0.5)

    ax.set_xlabel("Cenário de Rede", fontsize=12)
    ax.set_ylabel("Tempo de Resolução DNS (ms)", fontsize=12)
    ax.set_title("Tempo de Resolução DNS por Cenário", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Cenário {s}" for s in scenarios])
    ax.grid(axis="y", alpha=0.3)

    # Adiciona valores nas barras
    for i, v in enumerate(dns_grouped["dns_time"] * 1000):
        ax.text(i, v + 0.5, f"{v:.1f}ms", ha='center', fontweight='bold')

    plt.tight_layout()
    path = os.path.join(output_dir, "dns_time_analysis.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def plot_total_time_with_dns(df: pd.DataFrame, output_dir: str):
    """Gráfico de barras empilhadas: Tempo total (DNS + HTTP) por cenário."""
    fig, ax = plt.subplots(figsize=(12, 6))

    # Para cada cenário, protocolo e tamanho, calcula DNS + HTTP
    scenarios = sorted(df["scenario"].unique())
    protocols = ["tcp", "rudp"]
    file_sizes = sorted(df["file_size"].unique())

    colors = {"tcp": "#2196F3", "rudp": "#FF5722"}
    dns_color = "#9C27B0"

    x = range(len(scenarios))
    width = 0.2
    offsets = [-0.3, -0.1, 0.1, 0.3]  # Para 4 combinações (2 protos x 2 sizes)

    plot_idx = 0
    for proto in protocols:
        for fs in file_sizes:
            sub = df[(df["protocol"] == proto) & (df["file_size"] == fs)]
            if sub.empty:
                continue

            dns_means = [sub[sub["scenario"] == s]["dns_time"].mean() * 1000 for s in scenarios]
            http_means = [sub[sub["scenario"] == s]["time"].mean() * 1000 for s in scenarios]

            offset = offsets[plot_idx]
            bars_http = ax.bar(
                [xi + offset for xi in x], http_means, width,
                color=colors[proto], alpha=0.8,
                label=f"HTTP/{proto.upper()} ({fs})"
            )
            ax.bar(
                [xi + offset for xi in x], dns_means, width,
                bottom=0, color=dns_color, alpha=0.4
            )
            plot_idx += 1

    ax.set_xlabel("Cenário de Rede", fontsize=12)
    ax.set_ylabel("Tempo Total (ms)", fontsize=12)
    ax.set_title("Tempo Total de Carregamento (DNS + HTTP) — TCP vs R-UDP",
                 fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Cenário {s}" for s in scenarios])
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, "tempo_total_com_dns.png")
    plt.savefig(path, dpi=150)
    print(f"  Salvo: {path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Geração de gráficos do Trabalho II")
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Caminho do CSV de resultados")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Diretório de saída dos gráficos")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    print("=" * 50)
    print("  Geração de Gráficos — Trabalho II")
    print("  HTTP/1.1 (TCP vs R-UDP) + DNS")
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
    plot_dns_time(df, args.output)
    plot_total_time_with_dns(df, args.output)

    print(f"\n  Todos os gráficos foram gerados em: {args.output}")


if __name__ == "__main__":
    main()
