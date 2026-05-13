# TCP vs R-UDP — Análise de Desempenho e Confiabilidade em Camadas de Transporte

Projeto desenvolvido para a disciplina de Redes de Computadores II — Universidade Federal do Piauí (UFPI).

## Integrante

- Nome: SEU NOME
- Matrícula: SUA MATRÍCULA

---

# Objetivo

Este projeto implementa e compara dois sistemas de transferência de arquivos:

1. TCP Nativo
2. R-UDP (Reliable UDP)

O objetivo principal é analisar:

- confiabilidade;
- throughput;
- retransmissões;
- impacto da perda de pacotes;
- latência;
- overhead do protocolo;
- comportamento sob condições adversas de rede.

Além disso, o projeto realiza validação cruzada entre:

- métricas coletadas pela aplicação Python;
- capturas reais de rede obtidas via Wireshark/TCPDump.

---

# Tecnologias Utilizadas

- Python 3
- Socket API
- Docker
- tc/netem
- Wireshark
- TCPDump
- Pandas
- Matplotlib

---

# Estrutura do Projeto

```txt
redes2-rudp-analysis/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── app/
│   ├── tcp/
│   ├── rudp/
│   └── common/
│
├── docker/
│
├── network/
│   ├── tc/
│   └── captures/
│
├── benchmark/
│
├── tests/
│
├── data/
│   ├── input/
│   └── output/
│
└── reports/
```

---

# Arquitetura do Sistema

## TCP

Transferência tradicional utilizando sockets TCP nativos.

```txt
Cliente TCP
    ↓
Socket TCP
    ↓
Servidor TCP
```

---

## R-UDP

Transferência baseada em UDP com camada de confiabilidade implementada manualmente.

Características implementadas:

- números de sequência;
- ACKs;
- timeout;
- retransmissão;
- checksum;
- autenticação SHA-256.

```txt
Cliente
    ↓
Empacotamento
    ↓
UDP Socket
    ↓
Rede com perda
    ↓
Servidor
    ↓
ACK
    ↓
Retransmissão
```

---

# Cabeçalho Personalizado do Protocolo

Cada pacote R-UDP possui um cabeçalho personalizado contendo:

| Campo | Descrição |
|---|---|
| seq_num | Número de sequência |
| ack_num | Número do ACK |
| flags | Controle do pacote |
| checksum | Verificação de integridade |
| payload_size | Tamanho do payload |
| auth_hash | SHA-256 do aluno |

---

# Autenticação do Tráfego

Todos os pacotes enviados incluem o campo:

```txt
X-Custom-Auth
```

Esse campo contém o hash SHA-256 de:

```txt
MATRICULA + NOME
```

Permitindo a identificação do tráfego no Wireshark/TCPDump.

---

# Cenários de Teste

Os testes são executados em containers Docker Ubuntu utilizando `tc/netem`.

| Cenário | Perda | Delay |
|---|---|---|
| A | 0% | 10ms |
| B | 5% | 50ms |
| C | 10% | 100ms |

---

# Requisitos

## Python

- Python 3.10+

## Docker

- Docker
- Docker Compose

## Ferramentas de Rede

- tcpdump
- Wireshark
- tc/netem

---

# Instalação

## Clonar o Repositório

```bash
git clone https://github.com/SEU_USUARIO/redes2-rudp-analysis.git

cd redes2-rudp-analysis
```

---

# Instalar Dependências

```bash
pip install -r requirements.txt
```

---

# Subindo os Containers

```bash
docker compose up --build
```

---

# Execução

# Servidor TCP

```bash
python app/tcp/server.py
```

---

# Cliente TCP

```bash
python app/tcp/client.py
```

---

# Servidor R-UDP

```bash
python app/rudp/server.py
```

---

# Cliente R-UDP

```bash
python app/rudp/client.py
```

---

# Simulação de Rede

## Cenário A

```bash
./network/tc/scenario_a.sh
```

---

## Cenário B

```bash
./network/tc/scenario_b.sh
```

---

## Cenário C

```bash
./network/tc/scenario_c.sh
```

---

## Resetar Configuração de Rede

```bash
./network/tc/reset.sh
```

---

# Captura de Tráfego

## TCPDump

```bash
sudo tcpdump -i any port 5000 -w capture.pcap
```

---

# Filtros Wireshark

## UDP

```txt
udp.port == 5000
```

## TCP

```txt
tcp.port == 5000
```

---

# Benchmark

O benchmark executa múltiplas transferências automaticamente e gera:

- throughput;
- média;
- desvio padrão;
- retransmissões;
- gráficos comparativos.

## Executar Benchmark

```bash
python benchmark/run_benchmark.py
```

---

# Resultados

Os resultados são exportados para:

```txt
benchmark/csv/
```

Os gráficos são gerados em:

```txt
benchmark/plots/
```

---

# Métricas Avaliadas

- tempo total de transferência;
- throughput;
- retransmissões;
- perda de pacotes;
- overhead;
- integridade do arquivo;
- discrepância entre aplicação e captura de rede.

---

# Estratégia de Confiabilidade

O protocolo R-UDP utiliza:

## Stop-and-Wait ARQ

Fluxo:

1. cliente envia pacote;
2. cliente aguarda ACK;
3. timeout:
   - retransmissão;
4. ACK recebido:
   - próximo pacote.

---

# Integridade dos Dados

A integridade é garantida utilizando:

```txt
CRC32
```

---

# Análise Estatística

O projeto realiza:

- média;
- mínimo;
- máximo;
- desvio padrão.

Utilizando:

- Pandas;
- Matplotlib.

---

# Estrutura dos Logs

Exemplo:

```txt
[CLIENT] Sending packet seq=10
[SERVER] ACK sent seq=10
[TIMEOUT] Retransmitting packet seq=10
```

---

# Relatório

O relatório segue o modelo SBC e contém:

- fundamentação teórica;
- arquitetura;
- metodologia;
- experimentos;
- análise estatística;
- validação cruzada;
- conclusões.

---

# Perguntas Investigadas

1. Como o throughput do TCP se comporta em comparação ao R-UDP sob perda de 10%?

2. Qual o overhead introduzido pelo protocolo R-UDP?

3. Houve discrepância entre os dados da aplicação e do Wireshark/TCPDump?

---

# Limitações

- implementação baseada em Stop-and-Wait;
- sem controle avançado de congestionamento;
- timeout fixo;
- sem janela deslizante.

---

# Trabalhos Futuros

- implementação Go-Back-N;
- Selective Repeat;
- controle adaptativo de timeout;
- controle de congestionamento;
- paralelismo;
- interface gráfica.

---

# Licença

Projeto desenvolvido exclusivamente para fins acadêmicos.