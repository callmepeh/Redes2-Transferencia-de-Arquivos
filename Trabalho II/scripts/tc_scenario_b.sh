#!/bin/bash
# Cenário B: 5% de perda / 50ms de delay
# Deve ser executado DENTRO do container cliente com permissão NET_ADMIN
#
# Uso: bash scripts/tc_scenario_b.sh

IFACE=${1:-eth0}

echo "[TC] Removendo regras antigas em $IFACE..."
tc qdisc del dev "$IFACE" root 2>/dev/null || true

echo "[TC] Aplicando Cenário B: delay=50ms, perda=5% em $IFACE"
tc qdisc add dev "$IFACE" root netem delay 50ms loss 5%

echo "[TC] Configuração atual:"
tc qdisc show dev "$IFACE"
