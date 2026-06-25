"""
Funções auxiliares para comunicação HTTP via R-UDP.
Utiliza o protocolo RUDP com Stop-and-Wait para transferência confiável.

Uso:
    from client.rudp_client import send_http_via_rudp, receive_http_via_rudp
"""

import os
import sys
import socket

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocol.packet import RUDP_Packet, FLAG_DATA, FLAG_ACK, FLAG_FIN

TIMEOUT = 1.0  # segundos de timeout por pacote


def send_http_via_rudp(server_ip: str, port: int, request_data: bytes) -> tuple[bytes, int]:
    """
    Envia uma requisição HTTP via R-UDP e recebe a resposta completa.
    
    Args:
        server_ip: IP do servidor
        port: Porta do servidor R-UDP
        request_data: Dados da requisição HTTP
        
    Returns:
        tuple[bytes, int]: (response_data, total_retransmissions)
    """
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.settimeout(TIMEOUT)
    server_addr = (server_ip, port)
    
    seq_num = 0
    total_retransmissions = 0
    response_data = b""
    
    # Passo 1: Envia requisição (pode ser grande, fragmenta em chunks)
    # Para requisições HTTP, normalmente cabem em um pacote só (<= 1024 bytes)
    # Mas vamos tratar o caso de requisições maiores
    max_http_payload = 1024  # Deve ser igual a MAX_PAYLOAD_SIZE do protocolo
    
    # Fragmenta a requisição em chunks R-UDP
    chunks = [request_data[i:i + max_http_payload] 
              for i in range(0, len(request_data), max_http_payload)]
    
    for chunk in chunks:
        packet = RUDP_Packet(seq_num, 0, FLAG_DATA, chunk)
        packet_bytes = packet.pack()
        
        ack_received = False
        while not ack_received:
            try:
                client.sendto(packet_bytes, server_addr)
                ack_data, _ = client.recvfrom(2048)
                ack_packet = RUDP_Packet.unpack(ack_data)
                
                if ack_packet.flags == FLAG_ACK and ack_packet.ack_num == seq_num:
                    ack_received = True
                    seq_num += 1
            except socket.timeout:
                total_retransmissions += 1
            except ValueError:
                pass
    
    # Passo 2: Recebe resposta do servidor (múltiplos pacotes)
    # O servidor envia chunks de dados + FIN
    expected_seq = 0
    receiving = True
    fin_received = False
    fin_retry = 0
    
    while receiving:
        try:
            data, addr = client.recvfrom(2048)
            
            try:
                packet = RUDP_Packet.unpack(data)
            except ValueError:
                # Pacote corrompido, ignora
                continue
            
            if packet.flags == FLAG_DATA:
                if packet.seq_num == expected_seq:
                    response_data += packet.payload
                    # Envia ACK
                    ack_packet = RUDP_Packet(0, packet.seq_num, FLAG_ACK)
                    client.sendto(ack_packet.pack(), addr)
                    expected_seq += 1
                else:
                    # Reenvia ACK do último pacote aceito
                    last_ack = max(0, expected_seq - 1)
                    ack_packet = RUDP_Packet(0, last_ack, FLAG_ACK)
                    client.sendto(ack_packet.pack(), addr)
                    
            elif packet.flags == FLAG_FIN:
                # Recebeu FIN - encerra
                ack_packet = RUDP_Packet(0, packet.seq_num, FLAG_ACK)
                client.sendto(ack_packet.pack(), addr)
                fin_received = True
                receiving = False
                
        except socket.timeout:
            if fin_received:
                receiving = False
            elif fin_retry == 0:
                # Reenvia um ACK para o último pacote na esperança de receber mais
                if expected_seq > 0:
                    ack_packet = RUDP_Packet(0, expected_seq - 1, FLAG_ACK)
                    client.sendto(ack_packet.pack(), server_addr)
                fin_retry += 1
            else:
                receiving = False
    
    client.close()
    return response_data, total_retransmissions





if __name__ == "__main__":
    # Teste simples
    print("Módulo cliente R-UDP carregado com sucesso.")
