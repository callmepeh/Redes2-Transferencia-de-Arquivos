#!/bin/bash
# Cenário C: 10% de perda / 100ms de delay
# Deve ser executado DENTRO do container cliente com permissão NET_ADMIN
#
# Uso: bash scripts/tc_scenario_c.sh

IFACE=${1:-eth0}

echo "[TC] Removendo regras antigas em $IFACE..."
tc qdisc del dev "$IFACE" root 2>/dev/null || true

echo "[TC] Aplicando Cenário C: delay=100ms, perda=10% em $IFACE"
tc qdisc add dev "$IFACE" root netem delay 100ms loss 10%

echo "[TC] Configuração atual:"
tc qdisc show dev "$IFACE"
