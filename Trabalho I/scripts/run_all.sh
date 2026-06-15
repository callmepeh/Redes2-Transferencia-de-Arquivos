#!/bin/bash
# Script mestre para executar o benchmark completo dentro do Docker.
# Deve ser executado DENTRO do container CLIENTE.
#
# O que ele faz:
# 1. Para cada cenário (A, B, C):
#    a. Aplica regras de tráfego (tc)
#    b. Inicia captura tcpdump em background
#    c. Roda N transferências TCP
#    d. Roda N transferências R-UDP
#    e. Para a captura
#    f. Limpa as regras tc
#
# Uso:
#   bash scripts/run_all.sh [num_execucoes]
#
# Exemplo:
#   bash scripts/run_all.sh 10

RUNS=${1:-10}
CAPTURE_DIR="/app/captures"

mkdir -p "$CAPTURE_DIR"

echo "=============================================="
echo "  BENCHMARK COMPLETO — TCP vs R-UDP"
echo "  Execuções por cenário: $RUNS"
echo "=============================================="

for SCENARIO in A B C; do
    echo ""
    echo "################################################"
    echo "  CENÁRIO $SCENARIO"
    echo "################################################"

    # Aplica regras tc
    bash scripts/tc_scenario_$(echo $SCENARIO | tr '[:upper:]' '[:lower:]').sh

    # Inicia captura em background
    echo "[CAPTURE] Iniciando tcpdump para cenário $SCENARIO..."
    tcpdump -i eth0 -w "$CAPTURE_DIR/cenario_${SCENARIO}.pcap" &
    TCPDUMP_PID=$!
    sleep 1

    # Roda benchmark TCP
    echo "[BENCHMARK] Rodando TCP..."
    PYTHONPATH=/app python3 benchmark/runner.py --protocol tcp --runs $RUNS --scenario $SCENARIO

    # Roda benchmark R-UDP
    echo "[BENCHMARK] Rodando R-UDP..."
    PYTHONPATH=/app python3 benchmark/runner.py --protocol rudp --runs $RUNS --scenario $SCENARIO

    # Para a captura
    sleep 1
    kill $TCPDUMP_PID 2>/dev/null
    wait $TCPDUMP_PID 2>/dev/null
    echo "[CAPTURE] Captura do cenário $SCENARIO salva."

    # Limpa tc
    tc qdisc del dev eth0 root 2>/dev/null
    echo "[TC] Regras limpas."
done

echo ""
echo "=============================================="
echo "  BENCHMARK COMPLETO!"
echo "  Resultados: logs/results.csv"
echo "  Capturas:   captures/*.pcap"
echo "=============================================="

# Gera gráficos (se pandas/matplotlib estiverem instalados)
echo ""
echo "[GRAPHS] Gerando gráficos..."
PYTHONPATH=/app python3 analysis/graphs.py 2>/dev/null && echo "[GRAPHS] Gráficos gerados!" || echo "[GRAPHS] AVISO: Instale pandas e matplotlib para gerar gráficos."
