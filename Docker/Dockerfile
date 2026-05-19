FROM ubuntu:22.04

# Instala Python, Ferramentas de Rede (tc) e Captura (tcpdump)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    iproute2 \
    tcpdump \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Comando padrão (pode ser sobrescrito no docker-compose)
CMD ["python3", "server.py"]