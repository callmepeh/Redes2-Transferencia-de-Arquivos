import socket
import time
import os

# Em ambiente Docker Compose, o host é o nome do serviço ("servidor")
HOST = os.environ.get("SERVER_HOST", "servidor")
PORT = 5000

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

start = time.time()

with open("pdf_text.txt", "rb") as f:
    while True:
        chunk = f.read(1024)
        if not chunk:
            break
        client.sendall(chunk)

# Sinaliza fim do envio (EOF) para que o servidor saia do loop recv
client.shutdown(socket.SHUT_WR)

end = time.time()

print("Arquivo enviado com sucesso!")
print(f"Tempo de transferência: {end - start:.6f} segundos")

elapsed = end - start
if elapsed == 0:
    elapsed = 0.000001  # Evita divisão por zero se a transferência for instantânea

total_size = os.path.getsize("pdf_text.txt")
throughput = total_size / elapsed

print(f"Throughput: {throughput:.2f} bytes/s")  
client.close()  
