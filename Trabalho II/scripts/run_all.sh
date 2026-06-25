#!/bin/bash
# Script mestre para executar o benchmark completo do Trabalho II dentro do Docker.
# Deve ser executado DENTRO do container CLIENTE.
#
# O que ele faz:
# 1. Gera arquivos de teste (100kB, 1MB, 10MB) se não existirem
# 2. Para cada cenário (A, B, C):
#    a. Aplica regras de tráfego (tc)
#    b. Inicia captura tcpdump em background
#    c. Roda N transferências TCP (GET /arquivo_Xkb.txt)
#    d. Roda N transferências R-UDP (GET /arquivo_Xkb.txt)
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
WWW_DIR="/app/www"

mkdir -p "$CAPTURE_DIR"

echo "================================================"
echo "  BENCHMARK COMPLETO — Trabalho II"
echo "  HTTP/1.1 (TCP vs R-UDP) + DNS"
echo "  Execuções por cenário: $RUNS"
echo "================================================"

# Gera arquivos de teste no diretório www (se não existirem)
echo ""
echo "[SETUP] Verificando arquivos de teste..."

generate_test_file() {
    local size_kb=$1
    local filename="arquivo_${size_kb}kb.txt"
    local filepath="${WWW_DIR}/${filename}"
    
    if [ ! -f "$filepath" ]; then
        echo "[SETUP] Gerando ${filename} (${size_kb}kB)..."
        # Gera um arquivo com texto repetido do tamanho especificado
        python3 -c "
import os
size = ${size_kb} * 1024
content = 'Linha de teste para o Mini-Servidor Web - Redes II UFPI - Pedro Henrique Carvalho\n'
with open('${filepath}', 'w') as f:
    while os.path.getsize('${filepath}') < size if os.path.exists('${filepath}') else True:
        f.write(content)
        if os.path.exists('${filepath}') and os.path.getsize('${filepath}') >= size:
            break
" 2>/dev/null
        
        # Alternativa: usa dd
        if [ ! -f "$filepath" ] || [ ! -s "$filepath" ]; then
            dd if=/dev/urandom bs=1024 count=${size_kb} 2>/dev/null | base64 > "$filepath" 2>/dev/null
        fi
        echo "[SETUP] ${filename} gerado: $(wc -c < "$filepath") bytes"
    else
        echo "[SETUP] ${filename} já existe: $(wc -c < "$filepath") bytes"
    fi
}

# Gera arquivos de 100kB, 1MB, 10MB
# Nota: 10MB pode ser demorado para R-UDP, use com cautela
generate_test_file 100
generate_test_file 1024   # 1MB
# generate_test_file 10240  # 10MB (descomente se quiser testar)

echo ""
echo "[SETUP] Arquivos de teste prontos:"
ls -lh "${WWW_DIR}"/arquivo_*.txt 2>/dev/null

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
echo "================================================"
echo "  BENCHMARK COMPLETO!"
echo "  Resultados: logs/results.csv"
echo "  Capturas:   captures/*.pcap"
echo "================================================"

# Gera gráficos (se pandas/matplotlib estiverem instalados)
echo ""
echo "[GRAPHS] Gerando gráficos..."
PYTHONPATH=/app python3 analysis/graphs.py 2>/dev/null && echo "[GRAPHS] Gráficos gerados!" || echo "[GRAPHS] AVISO: Instale pandas e matplotlib para gerar gráficos."
