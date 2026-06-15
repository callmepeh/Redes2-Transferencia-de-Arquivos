"""
Definição dos cenários de simulação de rede (tc/netem).

Cada cenário corresponde a uma configuração do comando 'tc qdisc' que será
aplicada dentro do container Docker do cliente antes da execução dos testes.
"""

SCENARIOS = {
    "A": {
        "label": "0% perda / 10ms delay",
        "delay": "10ms",
        "loss": "0%",
        "tc_cmd": "tc qdisc add dev eth0 root netem delay 10ms",
    },
    "B": {
        "label": "5% perda / 50ms delay",
        "delay": "50ms",
        "loss": "5%",
        "tc_cmd": "tc qdisc add dev eth0 root netem delay 50ms loss 5%",
    },
    "C": {
        "label": "10% perda / 100ms delay",
        "delay": "100ms",
        "loss": "10%",
        "tc_cmd": "tc qdisc add dev eth0 root netem delay 100ms loss 10%",
    },
}
