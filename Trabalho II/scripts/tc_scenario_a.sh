#!/bin/bash
# Cenário A: 0% de perda / 10ms de delay
# Deve ser executado DENTRO do container cliente com permissão NET_ADMIN
#
# Uso: bash scripts/tc_scenario_a.sh

IFACE=${1:-eth0}

echo "[TC] Removendo regras antigas em $IFACE..."
tc qdisc del dev "$IFACE" root 2>/dev/null || true

echo "[TC] Aplicando Cenário A: delay=10ms, perda=0% em $IFACE"
tc qdisc add dev "$IFACE" root netem delay 10ms

echo "[TC] Configuração atual:"
tc qdisc show dev "$IFACE"
