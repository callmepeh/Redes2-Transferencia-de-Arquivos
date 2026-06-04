import socket
import os
from protocol.packet import RUDP_Packet, FLAG_DATA, FLAG_ACK, FLAG_FIN

HOST = '0.0.0.0'
PORT = int(os.environ.get("RUDP_PORT", 5001))
OUTPUT_FILE = os.environ.get("RUDP_OUTPUT", "recebido_rudp.txt")


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((HOST, PORT))
    print(f"[R-UDP SERVER] Ouvindo em {PORT}...")

    while True:
        # Cada iteração é uma nova sessão de transferência
        expected_seq_num = 0
        file_handle = None

        print("[R-UDP SERVER] Aguardando nova transferência...")
        try:
            while True:
                data, addr = server.recvfrom(2048)

                try:
                    packet = RUDP_Packet.unpack(data)
                except ValueError as e:
                    # Checksum falhou — descarta sem ACK para forçar retransmissão
                    print(f"[R-UDP SERVER] Pacote descartado (checksum falhou): {e}")
                    continue

                if packet.flags == FLAG_FIN:
                    print(f"[R-UDP SERVER] FIN recebido. Encerrando sessão.")
                    ack_packet = RUDP_Packet(0, packet.seq_num, FLAG_ACK)
                    server.sendto(ack_packet.pack(), addr)
                    break

                if packet.flags == FLAG_DATA:
                    # Abre o arquivo apenas quando o primeiro pacote de dados chega
                    # Isso evita truncar o arquivo de uma sessão anterior
                    if file_handle is None:
                        file_handle = open(OUTPUT_FILE, "wb")

                    if packet.seq_num == expected_seq_num:
                        file_handle.write(packet.payload)
                        file_handle.flush()
                        print(f"[R-UDP SERVER] Pacote {packet.seq_num} OK → ACK enviado.")
                        ack_packet = RUDP_Packet(0, packet.seq_num, FLAG_ACK)
                        server.sendto(ack_packet.pack(), addr)
                        expected_seq_num += 1
                    else:
                        # Duplicata — reenvia ACK do último pacote aceito
                        last_ack = max(0, expected_seq_num - 1)
                        print(f"[R-UDP SERVER] Duplicata seq={packet.seq_num}. "
                              f"Reenviando ACK={last_ack}")
                        ack_packet = RUDP_Packet(0, last_ack, FLAG_ACK)
                        server.sendto(ack_packet.pack(), addr)

        except KeyboardInterrupt:
            print("\n[R-UDP SERVER] Encerrado pelo usuário.")
            break
        finally:
            if file_handle is not None:
                file_handle.close()

        print(f"[R-UDP SERVER] Transferência concluída! {expected_seq_num} pacotes recebidos.")


if __name__ == "__main__":
    start_server()
