# COMPILAÇÃO E PROJETO — Trabalho II

## Mini-Servidor HTTP/1.1 com Resolução DNS (R-UDP/TCP)

**Disciplina:** Redes de Computadores II — UFPI  
**Aluno:** Pedro Henrique de Carvalho Sousa — Matrícula: 20239017876  
**Data de Entrega:** 26/06/2026  

---

## 📋 Visão Geral do Projeto

Este projeto implementa a **Terceira Avaliação de Redes de Computadores II**, evoluindo o sistema de transferência de arquivos do Trabalho I para um **Mini-Servidor Web HTTP/1.1** funcional, capaz de operar sobre TCP nativo e R-UDP (Reliable UDP), com um **Módulo de Resolução de Nomes (Mini-DNS)** para simular o mapeamento de domínios.

### Arquitetura do Sistema

```
┌──────────────┐    UDP:53     ┌──────────────┐
│  Cliente DNS  │ ──────────→  │ Servidor DNS  │
│  (dns/client) │ ←──────────  │ (dns/server)  │
└──────────────┘               └──────────────┘
       │                              │
       │ IP do Servidor               │ hosts.txt
       ▼                              ▼
┌──────────────┐   TCP:80      ┌──────────────┐
│ Cliente HTTP  │ ──────────→  │ Servidor Web  │
│ (client/http) │ ←──────────  │ (server/http) │  ← TCP Nativo
└──────────────┘               └──────────────┘
       │
       │ OU
       ▼
┌──────────────┐   R-UDP:81    ┌────────────────┐
│ Cliente HTTP  │ ──────────→  │ Servidor Web    │
│ (client/http) │ ←──────────  │ (server/rudp)   │  ← R-UDP
└──────────────┘               └────────────────┘
```

---

## 📁 Estrutura do Projeto

```
Trabalho II/
├── dns/                          # Módulo DNS
│   ├── __init__.py               #   Pacote Python
│   ├── packet.py                 #   Formato do pacote DNS simplificado (ID, Name, IP)
│   ├── server.py                 #   Servidor DNS (UDP)
│   ├── client.py                 #   Cliente DNS
│   └── hosts.txt                 #   Arquivo de zona estático
├── client/
│   ├── __init__.py               #   Pacote Python
│   ├── http_client.py            #   Cliente HTTP com integração DNS
│   └── rudp_client.py            #   Funções auxiliares R-UDP
├── server/
│   ├── __init__.py               #   Pacote Python
│   ├── http_server.py            #   Servidor HTTP/1.1 sobre TCP
│   └── rudp_http_server.py       #   Servidor HTTP/1.1 sobre R-UDP
├── protocol/
│   ├── __init__.py               #   Pacote Python
│   ├── auth.py                   #   Autenticação SHA-256 (X-Custom-Auth)
│   ├── checksum.py               #   CRC32
│   └── packet.py                 #   Pacote R-UDP (cabeçalho personalizado)
├── www/                          # Conteúdo Web
│   ├── index.html                #   Página inicial
│   ├── teste.html                #   Página de teste
│   ├── 404.html                  #   Página de erro 404
│   ├── style.css                 #   Estilos CSS
│   ├── arquivo_100kb.txt         #   Arquivo de 100kB para benchmark
│   └── arquivo_1024kb.txt        #   Arquivo de 1MB para benchmark
├── Docker/
│   ├── Dockerfile                #   Imagem Ubuntu + Python + tc
│   └── docker-compose.yml        #   3 serviços: DNS, Web, Cliente
├── scripts/
│   ├── tc_scenario_a.sh          #   Cenário A: 0% perda / 10ms delay
│   ├── tc_scenario_b.sh          #   Cenário B: 5% perda / 50ms delay
│   ├── tc_scenario_c.sh          #   Cenário C: 10% perda / 100ms delay
│   ├── capture.sh                #   Captura de tráfego com tcpdump
│   └── run_all.sh                #   Script mestre do benchmark
├── benchmark/
│   ├── __init__.py               #   Pacote Python
│   ├── scenarios.py              #   Definição dos cenários tc
│   ├── metrics.py                #   Cálculo de métricas estatísticas
│   ├── runner.py                 #   Executor do benchmark
│   └── benchmark.py              #   Ponto de entrada principal
├── analysis/
│   ├── __init__.py               #   Pacote Python
│   ├── analyze.py                #   Relatório textual de análise
│   └── graphs.py                 #   Geração de gráficos comparativos
├── captures/                     #   Capturas .pcap (geradas pelo benchmark)
├── logs/                         #   Resultados CSV (gerados pelo benchmark)
├── requirements.txt              #   Dependências Python
├── COMPILACAO_E_PROJETO.md       #   Este arquivo
└── README.md                     #   (opcional)
```

---

## 🚀 Como Compilar e Executar

### Pré-requisitos

- **Docker** e **Docker Compose** instalados
- **Python 3.10+** (para execução local opcional)
- **Linux** com suporte a `tc` (para testes com simulação de rede)

### Passo 1: Construir e Iniciar os Containers

```bash
cd "Trabalho II"
docker compose -f Docker/docker-compose.yml up --build
```

Este comando cria e inicia 3 containers:

| Container       | IP          | Função                          | Portas          |
|-----------------|-------------|----------------------------------|-----------------|
| `dns_redes`     | `10.0.0.2`  | Servidor DNS (UDP)              | 53              |
| `web_redes`     | `10.0.0.10` | Servidor Web HTTP/1.1           | 80 (TCP) / 81 (R-UDP) |
| `cliente_redes` | `10.0.0.100`| Cliente para testes e benchmark | -               |

### Passo 2: Executar Testes Individuais

Dentro do container **cliente** (`docker exec -it cliente_redes bash`):

#### Testar Resolução DNS

```bash
# Consulta DNS direta
python3 dns/client.py servidor.local --dns-server 10.0.0.2 --port 53

# Deve retornar: servidor.local -> 10.0.0.10
```

#### Testar Requisição HTTP via TCP

```bash
# Requisição HTTP GET com resolução DNS
python3 client/http_client.py GET /index.html \
    --protocol tcp \
    --server servidor.local \
    --dns-server 10.0.0.2 --dns-port 53
```

#### Testar Requisição HTTP via R-UDP

```bash
# Requisição HTTP GET via R-UDP
python3 client/http_client.py GET /index.html \
    --protocol rudp \
    --server servidor.local \
    --dns-server 10.0.0.2 --dns-port 53
```

#### Testar Página 404

```bash
python3 client/http_client.py GET /pagina_inexistente.html \
    --protocol tcp \
    --server servidor.local
```

### Passo 3: Executar Benchmark Completo

```bash
# Executa 10 transferências de cada protocolo em cada cenário
bash scripts/run_all.sh 10
```

Para executar apenas o benchmark Python manualmente:

```bash
# Benchmark completo (todos os cenários, TCP e R-UDP)
PYTHONPATH=/app python3 benchmark/benchmark.py

# Ou executar cenário específico
PYTHONPATH=/app python3 benchmark/runner.py --protocol tcp --runs 10 --scenario A --file-size 100kb
PYTHONPATH=/app python3 benchmark/runner.py --protocol rudp --runs 10 --scenario A --file-size 100kb
```

### Passo 4: Gerar Relatório e Gráficos

```bash
# Relatório textual
PYTHONPATH=/app python3 analysis/analyze.py

# Gráficos comparativos
PYTHONPATH=/app python3 analysis/graphs.py
```

Os gráficos serão salvos em `analysis/plots/`.

### Passo 5: Capturar Tráfego com tcpdump

```bash
# Iniciar captura (em qualquer container)
bash scripts/capture.sh nome_da_captura eth0

# Ou manualmente
tcpdump -i eth0 -w captures/teste_dns_http.pcap -v
```

---

## 🔬 Cenários de Simulação de Rede

Os cenários são aplicados no container **cliente** usando `tc qdisc` e `netem`:

| Cenário | Perda | Delay  | Comando tc                              |
|---------|-------|--------|-----------------------------------------|
| A       | 0%    | 10ms   | `tc qdisc add dev eth0 root netem delay 10ms` |
| B       | 5%    | 50ms   | `tc qdisc add dev eth0 root netem delay 50ms loss 5%` |
| C       | 10%   | 100ms  | `tc qdisc add dev eth0 root netem delay 100ms loss 10%` |

Aplicar manualmente:

```bash
bash scripts/tc_scenario_a.sh   # Cenário A
bash scripts/tc_scenario_b.sh   # Cenário B
bash scripts/tc_scenario_c.sh   # Cenário C

# Limpar regras
tc qdisc del dev eth0 root
```

---

## 📦 Módulo DNS (Mini-DNS)

### Formato do Pacote DNS Simplificado

| Campo        | Tamanho | Descrição                                      |
|--------------|---------|-------------------------------------------------|
| ID           | 2 bytes | Identificador único da consulta                 |
| Flags        | 1 byte  | 0=consulta, 1=resposta, 0x80=erro               |
| Name Length  | 1 byte  | Tamanho do nome do domínio (max 128)            |
| Name         | 0-128 B | Nome do domínio (ex: "servidor.local")          |
| IP           | 4 bytes | Endereço IPv4 (0.0.0.0 = não encontrado)        |
| TTL          | 4 bytes | Time to live (segundos)                         |

### Arquivo de Zona (hosts.txt)

```txt
servidor.local     10.0.0.10
www.servidor.local 10.0.0.10
web.local          10.0.0.10
```

### Resolução de Nomes

O fluxo de resolução DNS segue a seguinte sequência:

1. Cliente cria pacote DNS com FLAG_QUERY e nome do domínio
2. Cliente envia pacote via UDP para o servidor DNS (10.0.0.2:53)
3. Servidor DNS consulta a tabela `hosts.txt`
4. Servidor DNS responde com FLAG_RESPONSE e IP correspondente
5. Se não encontrado: IP = 0.0.0.0 com flag de erro

---

## 🌐 Servidor HTTP/1.1

### Sobre TCP (Porta 80)

O servidor `http_server.py` escuta em TCP e processa requisições GET.

**Respostas implementadas:**
- `200 OK` — Arquivo encontrado e servido
- `404 Not Found` — Arquivo não existe
- `403 Forbidden` — Directory traversal detectado
- `405 Method Not Allowed` — Apenas GET é suportado
- `400 Bad Request` — Requisição mal formatada
- `500 Internal Server Error` — Erro interno do servidor

**Cabeçalhos de resposta:**
```
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 1234
X-Custom-Auth: <SHA-256(Matrícula+Nome)>
Connection: close
Server: MiniWebServer/1.0 (R-UDP/TCP)
Date: Thu, 26 Jun 2026 12:00:00 GMT
```

### Sobre R-UDP (Porta 81)

O servidor `rudp_http_server.py` escuta em UDP e utiliza o protocolo R-UDP com Stop-and-Wait para entrega confiável.

Para requisições grandes, o servidor fragmenta a resposta em múltiplos pacotes R-UDP (1024 bytes de payload cada) e os envia sequencialmente, aguardando ACK para cada pacote.

---

## 📊 Benchmark e Análise

### Métricas Coletadas

Para cada execução:

- **Tempo total** (DNS + transferência HTTP)
- **Throughput** (bytes/segundo)
- **Tempo de resolução DNS** (ms)
- **Retransmissões** (apenas R-UDP)
- **Status code** (200, 404, etc.)
- **Tamanho do corpo** (bytes)

### Configurações do Benchmark

```bash
# Argumentos do benchmark/runner.py
--protocol    tcp|rudp|all    Protocolo a testar
--runs        N               Número de execuções (default: 10)
--scenario    A|B|C           Cenário de rede
--file-size   100kb|1mb|10mb  Tamanho do arquivo
```

### Gráficos Gerados

| Gráfico                    | Descrição                                           |
|----------------------------|-----------------------------------------------------|
| `throughput_por_cenario.png` | Throughput médio ± desvio por cenário e protocolo  |
| `tempo_por_cenario.png`      | Tempo médio ± desvio por cenário e protocolo       |
| `retransmissoes_rudp.png`    | Retransmissões médias do R-UDP por cenário         |
| `boxplot_throughput.png`     | Distribuição do throughput por protocolo/cenário   |
| `degradacao_throughput.png`  | Curva de degradação (eixo Y duplo)                 |
| `dns_time_analysis.png`      | Tempo de resolução DNS por cenário                 |
| `tempo_total_com_dns.png`    | Tempo total (DNS + HTTP) por protocolo/cenário     |

---

## 🎯 Critérios de Avaliação Atendidos

| Critério                  | Pontos | Status | Como foi implementado                                  |
|---------------------------|--------|--------|--------------------------------------------------------|
| Integração e Reuso        | 1.5    | ✅     | Reuso do R-UDP, Docker, tc do Trabalho I               |
| Módulo DNS Local          | 2.5    | ✅     | Servidor DNS UDP + hosts.txt + cliente com timeout     |
| Miniservidor HTTP/1.1     | 2.5    | ✅     | GET, 200/404, Content-Type, X-Custom-Auth              |
| Validação & Gráficos      | 1.5    | ✅     | Capturas .pcap, 7 gráficos comparativos                |
| Relatório (SBC)           | 1.0    | ✅     | Análise textual com respostas às perguntas             |
| Vídeo Demonstrativo       | 1.0    | ❌     | (a ser produzido pelo aluno)                           |

---

## ❓ Perguntas Obrigatórias (Respostas)

### 1. Impacto da perda no DNS vs HTTP

O DNS usa UDP puro sem retransmissão. Em cenários com perda (5%, 10%), consultas DNS podem ser perdidas. O cliente implementa timeout (2s) na aplicação para detectar perdas e reenviar consultas. Já o R-UDP usa Stop-and-Wait (timeout 1s), e o TCP usa mecanismos nativos do kernel (Fast Retransmit, SACK).

### 2. Overhead HTTP vs protocolo customizado

O cabeçalho HTTP adiciona ~300 bytes (~3x o cabeçalho R-UDP de 93 bytes), mas o impacto é desprezível para arquivos grandes (>100kB). A diferença principal está no transporte, não no overhead HTTP.

### 3. Fluxo Wireshark

O fluxo segue estritamente a ordem: DNS Query → DNS Response → (TCP Handshake) → HTTP GET → HTTP Response → Encerramento.

---

## 🐳 Comandos Docker Úteis

```bash
# Ver logs dos containers
docker logs dns_redes -f
docker logs web_redes -f
docker logs cliente_redes -f

# Acessar container específico
docker exec -it cliente_redes bash
docker exec -it web_redes bash
docker exec -it dns_redes bash

# Parar todos os containers
docker compose -f Docker/docker-compose.yml down

# Reconstruir containers (após alterações)
docker compose -f Docker/docker-compose.yml up --build -d

# Verificar conectividade entre containers
docker exec cliente_redes ping 10.0.0.10
docker exec cliente_redes ping 10.0.0.2
```

---

## ⚠️ Observações Importantes

1. **Permissões NET_ADMIN**: Os containers precisam de `cap_add: NET_ADMIN` para usar `tc`.
2. **Porta DNS 53**: Pode exigir privilégios. Se necessário, use `--port 5353` no servidor DNS.
3. **R-UDP é lento**: Para arquivos grandes (1MB+), o R-UDP com Stop-and-Wait é extremamente lento em cenários com perda. Espere minutos, não segundos.
4. **Arquivos grandes**: O arquivo de 10MB pode levar horas para transferir via R-UDP com perda. Recomenda-se testar com 100kB e 1MB.
5. **Geração de gráficos**: Requer `pandas` e `matplotlib` (já incluídos no requirements.txt).

---

## 📚 Referências

- RFC 7230 — HTTP/1.1: Message Syntax and Routing
- RFC 1035 — Domain Names - Implementation and Specification
- Documentação do netem: https://man7.org/linux/man-pages/man8/tc-netem.8.html
- Projeto original (Trabalho I): Pasta `../Trabalho I/`
