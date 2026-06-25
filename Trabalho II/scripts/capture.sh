#!/bin/bash
# Script de captura de tráfego com tcpdump.
# Deve ser executado DENTRO do container (servidor ou cliente).
#
# Uso:
#   bash scripts/capture.sh <nome_do_arquivo_pcap> [interface]
#
# Exemplo:
#   bash scripts/capture.sh dns_http_tcp eth0
#   bash scripts/capture.sh dns_http_rudp eth0

OUTPUT_NAME=${1:-"captura"}
IFACE=${2:-eth0}
CAPTURE_DIR="/app/captures"

mkdir -p "$CAPTURE_DIR"

PCAP_FILE="$CAPTURE_DIR/${OUTPUT_NAME}.pcap"

echo "[CAPTURE] Iniciando captura em $IFACE..."
echo "[CAPTURE] Arquivo: $PCAP_FILE"
echo "[CAPTURE] Pressione Ctrl+C para parar."

tcpdump -i "$IFACE" -w "$PCAP_FILE" -v
