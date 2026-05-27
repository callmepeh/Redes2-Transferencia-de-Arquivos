import socket
import time
import os
from protocol.packet import RUDP_Packet, FLAG_DATA, FLAG_ACK, FLAG_FIN

HOST = os.environ.get("RUDP_SERVER_HOST", os.environ.get("SERVER_HOST", "servidor_rudp"))
PORT = int(os.environ.get("RUDP_PORT", 5001))
TIMEOUT = 1.0  # segundos de timeout por pacote


def start_client(filepath="pdf_text.txt") -> dict:
    """
    Envia um arquivo via R-UDP (Stop-and-Wait).
    Retorna um dicionário com as métricas da transferência.
    """
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.settimeout(TIMEOUT)

    server_addr = (HOST, PORT)
    seq_num = 0
    total_retransmissions = 0

    start_time = time.time()

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(1024)
            if not chunk:
                break

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
                    # ACK de número errado → ignora e aguarda o correto

                except socket.timeout:
                    total_retransmissions += 1
                    print(f"[R-UDP CLIENT] TIMEOUT seq={seq_num}. "
                          f"Retransmissão #{total_retransmissions}")

                except ValueError as e:
                    # ACK corrompido — ignora e aguarda o próximo
                    print(f"[R-UDP CLIENT] ACK corrompido ignorado: {e}")

    # Handshake de encerramento: envia FIN e aguarda ACK
    fin_packet = RUDP_Packet(seq_num, 0, FLAG_FIN)
    fin_bytes = fin_packet.pack()
    ack_received = False
    while not ack_received:
        try:
            client.sendto(fin_bytes, server_addr)
            ack_data, _ = client.recvfrom(2048)
            ack_packet = RUDP_Packet.unpack(ack_data)
            if ack_packet.flags == FLAG_ACK and ack_packet.ack_num == seq_num:
                ack_received = True
        except socket.timeout:
            pass  # Reenvia FIN se não receber ACK

    end_time = time.time()
    elapsed = max(end_time - start_time, 1e-6)

    total_size = os.path.getsize(filepath)
    throughput = total_size / elapsed

    metrics = {
        "protocol": "rudp",
        "time": elapsed,
        "throughput": throughput,
        "bytes": total_size,
        "retransmissions": total_retransmissions,
    }

    print(f"\n[R-UDP CLIENT] Transferência concluída!")
    print(f"  Tempo:            {elapsed:.4f}s")
    print(f"  Throughput:       {throughput:.2f} bytes/s ({throughput/1024:.2f} KB/s)")
    print(f"  Retransmissões:   {total_retransmissions}")

    client.close()
    return metrics


if __name__ == "__main__":
    if not os.path.exists("pdf_text.txt"):
        with open("pdf_text.txt", "wb") as f:
            f.write(b"Arquivo de teste R-UDP - Pedro Henrique de Carvalho Sousa\n" * 100)

    start_client()