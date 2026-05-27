import socket
import time
import os

# Em ambiente Docker Compose, o host é o nome do serviço ("servidor")
HOST = os.environ.get("TCP_SERVER_HOST", os.environ.get("SERVER_HOST", "servidor"))
PORT = int(os.environ.get("TCP_PORT", 5000))


def start_client(filepath="pdf_text.txt") -> dict:
    """
    Envia um arquivo via TCP.
    Retorna um dicionário com as métricas da transferência.
    """
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))

    start_time = time.time()

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(1024)
            if not chunk:
                break
            client.sendall(chunk)

    # Sinaliza fim do envio (EOF) para que o servidor saia do loop recv
    client.shutdown(socket.SHUT_WR)

    end_time = time.time()
    elapsed = max(end_time - start_time, 1e-6)

    total_size = os.path.getsize(filepath)
    throughput = total_size / elapsed

    metrics = {
        "protocol": "tcp",
        "time": elapsed,
        "throughput": throughput,
        "bytes": total_size,
        "retransmissions": 0,  # TCP lida internamente
    }

    print(f"\n[TCP CLIENT] Transferência concluída!")
    print(f"  Tempo:            {elapsed:.4f}s")
    print(f"  Throughput:       {throughput:.2f} bytes/s ({throughput/1024:.2f} KB/s)")
    print(f"  Retransmissões:   N/A (gerenciado pelo SO)")

    client.close()
    return metrics


if __name__ == "__main__":
    start_client()
