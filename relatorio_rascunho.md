# Análise de Desempenho e Confiabilidade em Camadas de Transporte (TCP vs. R-UDP)

**Pedro Henrique de Carvalho Sousa**¹

¹Curso de Bacharelado em Sistemas de Informação – Universidade Federal do Piauí (UFPI)
Campus Senador Helvídio Nunes de Barros

**Resumo.** Este artigo apresenta a implementação e a análise comparativa de desempenho entre o protocolo TCP nativo e um protocolo confiável baseado em UDP (R-UDP), desenvolvido na camada de aplicação. Utilizando a estratégia Stop-and-Wait, o R-UDP implementa mecanismos de controle de erros, retransmissão por timeout, checksum (CRC32) e um cabeçalho customizado com autenticação SHA-256. Através da ferramenta de emulação de rede NetEm (via comando tc), foram simulados cenários de degradação com perdas de pacotes (0%, 5% e 10%) e latências (10ms, 50ms e 100ms). Os resultados, validados via análise de tráfego (Wireshark/tcpdump), demonstram o severo impacto da estratégia Stop-and-Wait no throughput em cenários de alta latência, contrastando com a resiliência do algoritmo de janela deslizante do TCP.

---

## 1. Introdução
*(Descreva brevemente a importância da camada de transporte, a diferença teórica entre TCP e UDP, e o objetivo do trabalho: criar confiabilidade sobre um protocolo não confiável).*

## 2. Metodologia e Implementação do R-UDP
A implementação do protocolo R-UDP foi desenvolvida em Python, baseando-se no modelo **Stop-and-Wait ARQ** (Automatic Repeat reQuest). Para garantir a integridade e identificação, foi projetado um cabeçalho de aplicação de **93 bytes** contendo:

*   **Identificação (78 bytes):** String delimitadora `X-Custom-Auth:` seguida do hash SHA-256 da string composta pela matrícula e nome do autor.
*   **Controle (11 bytes):** Números de sequência (`seq_num`) e confirmação (`ack_num`), uma flag indicadora (DATA, ACK, FIN) e o tamanho do payload.
*   **Integridade (4 bytes):** Checksum calculado via CRC-32 sobre o cabeçalho e payload.

A simulação das adversidades de rede foi isolada em containers Docker, utilizando a ferramenta `tc` e o módulo `netem` do kernel Linux, permitindo injetar atrasos e descartes de forma determinística na interface de rede virtual.

## 3. Resultados e Análise

*(Aqui você deve incluir os gráficos gerados no diretório `analysis/plots/` e comentá-los brevemente. Exemplo: "Como demonstrado no Gráfico 1 (throughput_por_cenario.png), observa-se que...")*

---

## 4. Respostas às Perguntas Obrigatórias

### 4.1. Como a curva de throughput do TCP se comportou em comparação ao seu R-UDP sob 10% de perda?
O TCP apresentou um throughput infinitamente superior ao R-UDP sob 10% de perda (Cenário C). Isso ocorre por uma diferença fundamental de design: o TCP utiliza algoritmos complexos de controle de congestionamento (como CUBIC ou Reno) e o mecanismo de **Janela Deslizante**, permitindo enviar múltiplos pacotes simultaneamente antes de exigir uma confirmação. Mesmo com 10% de perda reduzindo drasticamente o tamanho da janela do TCP, ele se recupera rapidamente via *Fast Retransmit*.

Em contrapartida, o R-UDP foi implementado com a abordagem **Stop-and-Wait**. Nesse modelo, a janela de transmissão é igual a 1. O throughput é duramente penalizado não apenas pela perda (que força a esperar 1 segundo inteiro de *timeout* para cada descarte), mas principalmente pelo *delay* associado de 100ms. Cada pacote enviado exige esperar 200ms de RTT (Round Trip Time) apenas para confirmar o recebimento, limitando fisicamente a vazão máxima teórica da aplicação, gerando um abismo de performance entre os dois.

### 4.2. Ao analisar o Wireshark/TCPDump, qual foi o overhead (em bytes) introduzido pelos cabeçalhos do seu protocolo R-UDP?
A análise de tráfego demonstra que a implementação do R-UDP gerou um overhead fixo na camada de aplicação de **93 bytes** por pacote enviado. 
Descendo a pilha de protocolos para a visão do Wireshark na rede local (Ethernet), o overhead total por fragmento de dados é calculado da seguinte forma:
*   Cabeçalho Ethernet: 14 bytes
*   Cabeçalho IPv4: 20 bytes
*   Cabeçalho UDP: 8 bytes
*   **Cabeçalho R-UDP (Aplicação): 93 bytes**

Isso totaliza **135 bytes** de cabeçalhos transitando na rede para cada "chunk" de 1024 bytes lidos do arquivo original, o que representa um overhead de aproximadamente 13% em relação à carga útil transferida. 

### 4.3. Houve discrepância entre o tempo medido pelo Python e o registrado no Wireshark/TCPDump? Justifique.
Sim, invariavelmente existe uma discrepância entre o tempo de cronômetro do código (`time.time()`) na aplicação e os *timestamps* registrados nos pacotes `.pcap` do Wireshark. 
O tempo medido em Python engloba toda a latência de processamento interno da máquina: as chamadas de sistema (syscalls) de leitura de arquivo (`open()`, `read()`), o processamento da CPU para gerar o pacote e calcular o hash SHA-256 e o CRC32, além do tempo que o Sistema Operacional leva para escalonar o processo, descer os dados pela pilha de rede (Sockets -> TCP/IP -> Driver) e, finalmente, colocar o sinal no meio físico.

O Wireshark, especialmente quando escutando via *kernel packet filter* (BPF), carimba o tempo no exato instante em que o pacote atinge a interface de rede lógica/física. Portanto, o tempo da aplicação será sempre ligeiramente maior, pois inclui o tempo de I/O em disco e a latência de processamento que ocorrem antes do pacote chegar à placa de rede.

---

## 5. Conclusões
*(Breve parágrafo concluindo que a criação de confiabilidade sobre UDP é possível, mas algoritmos ingênuos como Stop-and-Wait são inviáveis para alta performance em redes modernas, evidenciando o mérito da engenharia por trás do TCP).*
